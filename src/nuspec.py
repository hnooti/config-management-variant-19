"""Извлечение зависимостей из XML-манифеста пакета NuGet."""

import xml.etree.ElementTree as et

from .config import PACKAGE_ID
from .model import Dependency


def parse_nuspec(
    content: bytes, target_framework: str
) -> tuple[Dependency, ...]:
    """Разобрать .nuspec с пространством имён или без него."""
    try:
        root = et.fromstring(content)
    except et.ParseError as error:
        raise ValueError(f"не удалось прочитать .nuspec: {error}") from error
    for element in root.iter():
        element.tag = element.tag.rsplit("}", 1)[-1]
    metadata = root.find("metadata")
    if metadata is None:
        raise ValueError(".nuspec не содержит элемента metadata")
    deps = metadata.find("dependencies")
    if deps is None:
        return ()
    unique = dict.fromkeys(
        _read_dependency(node) for node in _select_elements(
            deps, target_framework.lower()
        )
    )
    return tuple(unique)


def _select_elements(deps: et.Element, framework: str) -> list[et.Element]:
    """Взять все группы либо точную группу или её общий запасной вариант."""
    if not framework:
        return list(deps.iter("dependency"))
    groups = deps.findall("group")
    exact = [g for g in groups if _group_framework(g) == framework]
    if exact:
        return _group_dependencies(exact)
    neutral = [g for g in groups if not _group_framework(g)]
    direct = deps.findall("dependency")
    if neutral or direct or not groups:
        return direct + _group_dependencies(neutral)
    available = ", ".join(sorted({_group_framework(g) for g in groups}))
    raise ValueError(
        f"нет группы target_framework={framework}; доступны: {available}"
    )


def _group_framework(group: et.Element) -> str:
    """Получить имя группы без учёта регистра."""
    return group.get("targetFramework", "").strip().lower()


def _group_dependencies(groups: list[et.Element]) -> list[et.Element]:
    """Собрать элементы dependency из выбранных групп."""
    return [item for group in groups for item in group.findall("dependency")]


def _read_dependency(node: et.Element) -> Dependency:
    """Проверить идентификатор и сохранить текст ограничения."""
    name = node.get("id", "")
    if not PACKAGE_ID.fullmatch(name):
        raise ValueError(f".nuspec: некорректный ID зависимости {name!r}")
    return Dependency(name.lower(), node.get("version", "").strip())
