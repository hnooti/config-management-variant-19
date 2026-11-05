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


@dataclass(frozen=True)
class VersionRange:
    """Границы допустимых версий и признаки их включения."""

    minimum: Version | None = None
    maximum: Version | None = None
    include_minimum: bool = False
    include_maximum: bool = False

    def contains(self, version: Version) -> bool:
        """Проверить границы и допуск предварительной версии."""
        if not version.stable and not self._allows_prerelease():
            return False
        if self.minimum is not None:
            if version < self.minimum:
                return False
            if version == self.minimum and not self.include_minimum:
                return False
        if self.maximum is not None:
            if version > self.maximum:
                return False
            if version == self.maximum and not self.include_maximum:
                return False
        return True

    def _allows_prerelease(self) -> bool:
        """Учитывать prerelease при явной prerelease-границе."""
        return any(v is not None and not v.stable for v in (
            self.minimum, self.maximum
        ))


def parse_range(raw: str) -> VersionRange:
    """Разобрать минимум, точное совпадение или интервал NuGet."""
    raw = raw.strip()
    if not raw:
        return VersionRange()
    if raw[0] not in "[(":
        return VersionRange(minimum=parse_version(raw), include_minimum=True)
    if raw[-1] not in "])":
        raise ValueError(f"некорректный диапазон NuGet: {raw!r}")
    inner = raw[1:-1]
    if "," not in inner:
        return _exact_range(raw, inner)
    lower, upper = (part.strip() for part in inner.split(",", 1))
    result = VersionRange(
        parse_version(lower) if lower else None,
        parse_version(upper) if upper else None,
        raw.startswith("["),
        raw.endswith("]"),
    )
    _validate_bounds(result, raw)
    return result


def _exact_range(raw: str, inner: str) -> VersionRange:
    """Прочитать форму [версия]."""
    if raw[0] != "[" or raw[-1] != "]":
        raise ValueError(f"некорректный диапазон NuGet: {raw!r}")
    exact = parse_version(inner)
    return VersionRange(exact, exact, True, True)


def _validate_bounds(bounds: VersionRange, raw: str) -> None:
    """Отклонить перепутанные границы или пустой диапазон."""
    low, high = bounds.minimum, bounds.maximum
    if low is None or high is None:
        return
    if low > high or (low == high and not bounds.contains(low)):
        raise ValueError(f"пустой диапазон NuGet: {raw!r}")
