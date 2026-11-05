"""Разбор и нормализация точного номера версии NuGet."""

import re
from dataclasses import dataclass

VERSION_PATTERN = re.compile(
    r"(?P<numbers>[0-9]+(?:\.[0-9]+){0,3})"
    r"(?:-(?P<pre>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)
BASE_COMPONENTS = 3
MAX_COMPONENTS = 4


@dataclass(frozen=True, order=True)
class Version:
    """Числовые компоненты, признак релиза и идентификаторы prerelease."""

    numbers: tuple[int, ...]
    stable: bool
    prerelease: tuple[tuple[int, int | str], ...]

    def __str__(self) -> str:
        """Вернуть нормализованный ключ для HTTP-запросов NuGet."""
        numbers = self.numbers
        if not numbers[-1]:
            numbers = numbers[:BASE_COMPONENTS]
        main = ".".join(map(str, numbers))
        suffix = ".".join(str(value) for _, value in self.prerelease)
        return main if self.stable else f"{main}-{suffix}"


def parse_version(raw: str) -> Version:
    """Разобрать точную версию, игнорируя метаданные сборки."""
    match = VERSION_PATTERN.fullmatch(raw.strip())
    if match is None:
        raise ValueError(f"некорректная версия NuGet: {raw!r}")
    numbers = tuple(int(part) for part in match["numbers"].split("."))
    padded = numbers + (0,) * (MAX_COMPONENTS - len(numbers))
    suffix = match["pre"]
    tags = tuple(_prerelease_key(part) for part in suffix.split(".")) if (
        suffix
    ) else ()
    return Version(padded, not suffix, tags)


def _prerelease_key(part: str) -> tuple[int, int | str]:
    """Поставить числовые идентификаторы перед текстовыми."""
    return (0, int(part)) if part.isdecimal() else (1, part.lower())
