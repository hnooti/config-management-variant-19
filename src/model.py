"""Модель вершины графа и объявленной зависимости NuGet."""

from dataclasses import dataclass

from .version import Version


@dataclass(frozen=True)
class Package:
    """Имя пакета и точная нормализованная версия."""

    name: str
    version: Version

    def __str__(self) -> str:
        """Показать имя и версию одной строкой."""
        return f"{self.name}@{self.version}"


@dataclass(frozen=True)
class Dependency:
    """Ограничение на версию, прочитанное из метаданных."""

    name: str
    requirement: str

    def __str__(self) -> str:
        """Показать идентификатор и исходное ограничение."""
        return f"{self.name}: {self.requirement or '(любая версия)'}"
