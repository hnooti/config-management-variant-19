"""Чтение NuGet V3 по HTTP без менеджера пакетов и сторонних модулей."""

import json
import ssl
import sys
from functools import lru_cache
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from .config import is_http_url
from .model import Dependency, Package
from .nuspec import parse_nuspec
from .version import Version, parse_range, parse_version

HTTP_TIMEOUT = 15
MAX_RESPONSE = 16 * 1024 * 1024
NOT_FOUND = 404
BASE_TYPE = "PackageBaseAddress/3.0.0"
MACOS_CA_BUNDLE = Path("/etc/ssl/cert.pem")


class NuGetRepository:
    """Источник метаданных с кешем в памяти на время одного запуска."""

    def __init__(self, service_index: str, target_framework: str = ""):
        """Сохранить адрес индекса и выбор группы .nuspec."""
        self._service_index = service_index
        self._framework = target_framework
        self._base_url: str | None = None
        self._versions: dict[str, tuple[Version, ...]] = {}
        self._dependencies: dict[Package, tuple[Dependency, ...]] = {}

    def declared_dependencies(self, package: Package) -> tuple[Dependency, ...]:
        """Получить прямые зависимости для точной версии."""
        if package not in self._dependencies:
            name, version = package.name, package.version
            url = f"{self._base()}/{name}/{version}/{name}.nuspec"
            try:
                items = parse_nuspec(_fetch(url), self._framework)
            except ValueError as error:
                raise ValueError(f"{package}: {error}") from error
            self._dependencies[package] = items
        return self._dependencies[package]

    def children(self, package: Package) -> tuple[Package, ...]:
        """Для каждого ребра выбрать минимальную подходящую версию."""
        deps = self.declared_dependencies(package)
        resolved = (self._resolve(dep) for dep in deps)
        return tuple(dict.fromkeys(resolved))

    def _base(self) -> str:
        """Однократно найти ресурс PackageBaseAddress в индексе V3."""
        if self._base_url is None:
            self._base_url = _find_base(_json(self._service_index))
        return self._base_url

    def _package_versions(self, name: str) -> tuple[Version, ...]:
        """Прочитать и упорядочить версии из индекса пакета."""
        if name not in self._versions:
            data = _json(f"{self._base()}/{name}/index.json")
            raw = data.get("versions")
            if not isinstance(raw, list) or not all(
                isinstance(value, str) for value in raw
            ):
                raise ValueError(f"{name}: некорректный список версий")
            self._versions[name] = tuple(sorted(map(parse_version, raw)))
        return self._versions[name]

    def _resolve(self, dependency: Dependency) -> Package:
        """Выбрать минимальную доступную версию в заданном диапазоне."""
        try:
            allowed = parse_range(dependency.requirement)
        except ValueError as error:
            raise ValueError(f"{dependency}: {error}") from error
        for version in self._package_versions(dependency.name):
            if allowed.contains(version):
                return Package(dependency.name, version)
        raise ValueError(f"нет подходящей версии для {dependency}")


def _find_base(index: dict) -> str:
    """Найти корректный HTTP(S) адрес ресурса PackageBaseAddress."""
    resources = index.get("resources")
    if not isinstance(resources, list):
        raise ValueError("индекс NuGet V3 не содержит список resources")
    for resource in resources:
        if not isinstance(resource, dict) or resource.get("@type") != BASE_TYPE:
            continue
        url = resource.get("@id")
        if isinstance(url, str) and is_http_url(url):
            return url.rstrip("/")
    raise ValueError("индекс NuGet V3 не содержит PackageBaseAddress/3.0.0")


def _json(url: str) -> dict:
    """Прочитать объект JSON с адреса NuGet."""
    try:
        data = json.loads(_fetch(url))
    except (json.JSONDecodeError, UnicodeError) as error:
        raise ValueError(f"некорректный JSON: {url}") from error
    if not isinstance(data, dict):
        raise ValueError(f"ожидается JSON-объект: {url}")
    return data


@lru_cache(maxsize=1)
def _tls_context() -> ssl.SSLContext:
    """Использовать системное хранилище сертификатов и набор CA macOS."""
    context = ssl.create_default_context()
    if sys.platform == "darwin" and MACOS_CA_BUNDLE.is_file():
        context.load_verify_locations(cafile=str(MACOS_CA_BUNDLE))
    return context


def _fetch(url: str) -> bytes:
    """Выполнить GET с проверкой TLS, таймаутом и лимитом размера."""
    try:
        with urlopen(url, timeout=HTTP_TIMEOUT, context=_tls_context()) as rsp:
            data = rsp.read(MAX_RESPONSE + 1)
    except HTTPError as error:
        detail = "ресурс не найден" if error.code == NOT_FOUND else error.reason
        raise ValueError(f"HTTP {error.code}: {detail}: {url}") from error
    except (URLError, OSError) as error:
        raise ValueError(f"не удалось получить {url}: {error}") from error
    if len(data) > MAX_RESPONSE:
        raise ValueError(f"слишком большой ответ: {url}")
    return data
