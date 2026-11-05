"""Точка входа в приложение."""

import argparse
import configparser
import sys
from pathlib import Path

from .config import config_text, load_config
from .model import Package
from .nuget import NuGetRepository


def main(argv: list[str] | None = None) -> int:
    """Показать прямые зависимости NuGet для указанной версии."""
    parser = argparse.ArgumentParser(description="Граф зависимостей NuGet")
    parser.add_argument("config", type=Path, help="путь к файлу INI")
    parser.add_argument("--show-config", action="store_true",
                        help="вывести параметры в формате ключ=значение")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        if args.show_config:
            print(config_text(config))
            return 0
        if config.test_mode:
            raise ValueError("для этого этапа укажите URL NuGet V3")
        package = Package(config.package, config.version)
        repo = NuGetRepository(config.repository, config.target_framework)
        dependencies = repo.declared_dependencies(package)
        print(f"Прямые зависимости {package}:")
        for dependency in dependencies:
            print(f"  {dependency}")
        if not dependencies:
            print("  нет")
    except (ValueError, OSError, configparser.Error) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
