"""Точка входа в приложение."""

import argparse
import configparser
import sys
from pathlib import Path

from .config import config_text, load_config


def main(argv: list[str] | None = None) -> int:
    """Проверить INI и показать текущие настройки."""
    parser = argparse.ArgumentParser(description="Граф зависимостей NuGet")
    parser.add_argument("config", type=Path, help="путь к файлу INI")
    args = parser.parse_args(argv)
    try:
        print(config_text(load_config(args.config)))
    except (ValueError, OSError, configparser.Error) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
