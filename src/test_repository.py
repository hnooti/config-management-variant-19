"""Чтение локального JSON-репозитория с синтетическими пакетами."""

import json
from pathlib import Path

from .config import TEST_ID
from .model import Dependency, Package


class TestRepository:
    """Граф, где все имена состоят из заглавных латинских букв."""

    def __init__(self, path: Path):
        """Загрузить список смежности и проверить все ссылки."""
        with path.open(encoding="utf-8-sig") as stream:
            data = json.load(stream)
        self._nodes = _validate_graph(data)

    def children(self, package: Package) -> tuple[Package, ...]:
        """Вернуть потомков с условной версией из конфигурации."""
        return tuple(
            Package(name, package.version) for name in self._neighbors(package)
        )

    def declared_dependencies(self, package: Package) -> tuple[Dependency, ...]:
        """Показать тестовых соседей в том же формате, что NuGet."""
        return tuple(
            Dependency(name, f"[{package.version}]")
            for name in self._neighbors(package)
        )

    def _neighbors(self, package: Package) -> tuple[str, ...]:
        """Получить соседей или сообщить об отсутствующем пакете."""
        try:
            return self._nodes[package.name]
        except KeyError as error:
            raise ValueError(f"в тестовом графе нет {package.name}") from error

    def check_root(self, package: Package) -> None:
        """Проверить стартовую вершину даже при нулевой глубине."""
        self._neighbors(package)


def _validate_graph(data: object) -> dict[str, tuple[str, ...]]:
    """Проверить структуру графа и наличие каждой целевой вершины."""
    if not isinstance(data, dict) or not data:
        raise ValueError("repository: ожидается непустой JSON-объект")
    nodes = {name: _validate_neighbors(name, links)
             for name, links in data.items()}
    for name, links in nodes.items():
        for link in links:
            if link not in nodes:
                raise ValueError(
                    f"repository: {name} ссылается на {link} без записи"
                )
    return nodes


def _validate_neighbors(name: str, links: object) -> tuple[str, ...]:
    """Проверить имя вершины и убрать повторные рёбра."""
    if not TEST_ID.fullmatch(name):
        raise ValueError(f"repository: имя {name!r} должно состоять из A-Z")
    if not isinstance(links, list) or not all(
        isinstance(link, str) and TEST_ID.fullmatch(link) for link in links
    ):
        raise ValueError(f"repository: {name}: ожидается список имён из A-Z")
    return tuple(dict.fromkeys(links))
