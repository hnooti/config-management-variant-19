"""Чтение и проверка пользовательских настроек из INI."""

import configparser
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from .version import Version, parse_version

SECTION = "graph"
PACKAGE_ID = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*")
TEST_ID = re.compile(r"[A-Z]+")
FRAMEWORK = re.compile(r"[A-Za-z0-9.][A-Za-z0-9.,=+_-]*")
MAX_DEPTH = 500
REQUIRED = frozenset({
    "package", "repository", "test_mode", "version", "output",
    "ascii_tree", "max_depth",
})


@dataclass(frozen=True)
class Config:
    """Проверенные настройки. Пути разрешены относительно INI."""

    package: str
    repository: str
    test_mode: bool
    version: Version
    output: Path
    ascii_tree: bool
    max_depth: int
    target_framework: str


def load_config(path: Path) -> Config:
    """Прочитать UTF-8 INI и проверить все обязательные поля."""
    parser = configparser.ConfigParser(interpolation=None)
    with path.open(encoding="utf-8-sig") as stream:
        parser.read_file(stream)
    values = _get_section(parser)
    test_mode = _read_bool(values, "test_mode")
    config = Config(
        package=_read_package(values["package"], test_mode),
        repository=_read_repository(values["repository"], test_mode, path),
        test_mode=test_mode,
        version=parse_version(values["version"]),
        output=_read_output(values["output"], path),
        ascii_tree=_read_bool(values, "ascii_tree"),
        max_depth=_read_depth(values["max_depth"]),
        target_framework=_read_framework(values.get("target_framework", "")),
    )
    _check_output_paths(config, path)
    return config


def _get_section(
    parser: configparser.ConfigParser,
) -> configparser.SectionProxy:
    """Отклонить отсутствующие и неизвестные настройки."""
    if parser.sections() != [SECTION] or parser.defaults():
        raise ValueError("INI должен содержать одну секцию [graph]")
    values = parser[SECTION]
    missing = REQUIRED - values.keys()
    if missing:
        raise ValueError("отсутствуют параметры: " + ", ".join(sorted(missing)))
    extra = values.keys() - REQUIRED - {"target_framework"}
    if extra:
        raise ValueError("неизвестные параметры: " + ", ".join(sorted(extra)))
    return values


def _read_bool(values: configparser.SectionProxy, key: str) -> bool:
    """Разобрать стандартное логическое значение INI."""
    try:
        return values.getboolean(key)
    except ValueError as error:
        raise ValueError(f"{key}: ожидается true или false") from error


def _read_package(raw: str, test_mode: bool) -> str:
    """Проверить имя NuGet или идентификатор тестовой вершины."""
    pattern = TEST_ID if test_mode else PACKAGE_ID
    if not pattern.fullmatch(raw):
        hint = ("только заглавные буквы A-Z" if test_mode
                else "ожидается NuGet ID")
        raise ValueError(f"package: {hint}")
    return raw if test_mode else raw.lower()


def is_http_url(raw: str) -> bool:
    """Проверить абсолютный HTTP(S) URL без учётных данных."""
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme in {"http", "https"} and bool(parsed.hostname)
        and parsed.username is None and port != 0 and not parsed.fragment
        and not any(c.isspace() or ord(c) < 32 for c in raw)
    )


def _read_repository(raw: str, test_mode: bool, config_path: Path) -> str:
    """Проверить URL сервиса NuGet или существующий файл графа."""
    if test_mode:
        if not raw:
            raise ValueError("repository: укажите путь к JSON")
        source = (config_path.parent / raw).resolve()
        if not source.is_file():
            raise ValueError(f"repository: файл не найден: {source}")
        return str(source)
    if not is_http_url(raw):
        raise ValueError("repository: ожидается HTTP(S) URL индекса NuGet V3")
    return raw


def _read_output(raw: str, config_path: Path) -> Path:
    """Разрешить путь для SVG и отклонить каталог в качестве файла."""
    if Path(raw).suffix.lower() != ".svg":
        raise ValueError("output: ожидается имя файла с расширением .svg")
    target = (config_path.parent / raw).resolve()
    if target.is_dir():
        raise ValueError(f"output: указан каталог: {target}")
    return target


def _check_output_paths(config: Config, config_path: Path) -> None:
    """Не позволить выходным файлам заменить входные."""
    inputs = {config_path.resolve()}
    if config.test_mode:
        inputs.add(Path(config.repository).resolve())
    if any(p.resolve() in inputs for p in (
        config.output, config.output.with_suffix(".dot")
    )):
        raise ValueError("output: выходной файл совпадает с входным")


def _read_depth(raw: str) -> int:
    """Проверить число уровней, оставив запас стека для рекурсии."""
    try:
        depth = int(raw)
    except ValueError as error:
        raise ValueError("max_depth: ожидается целое число") from error
    if not 0 <= depth <= MAX_DEPTH:
        raise ValueError(f"max_depth: допустимы значения от 0 до {MAX_DEPTH}")
    return depth


def _read_framework(raw: str) -> str:
    """Проверить имя группы; пустое значение означает все группы."""
    if raw and not FRAMEWORK.fullmatch(raw):
        raise ValueError("target_framework: ожидается имя группы из .nuspec")
    return raw


def config_text(config: Config) -> str:
    """Вернуть настройки в формате ключ=значение."""
    values = vars(config)
    return "\n".join(f"{key}={_format_value(value)}" for key, value in (
        values.items()
    ))


def _format_value(value: object) -> str:
    """Отформатировать значения без Python-представления путей и bool."""
    return str(value).lower() if isinstance(value, bool) else str(value)
