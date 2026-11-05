"""Точка входа в приложение."""

import argparse
import configparser
import sys
from pathlib import Path

from .config import Config, config_text, load_config
from .graph import build_graph, levels_text
from .model import Package
from .nuget import NuGetRepository
from .order import order_text
from .test_repository import TestRepository
from .visualize import ascii_tree, save_diagram

Repository = NuGetRepository | TestRepository


def main(argv: list[str] | None = None) -> int:
    """Разобрать команду и показать результат или понятную ошибку."""
    args = _parser().parse_args(argv)
    try:
        config = load_config(args.config)
        _execute(args, config)
    except (ValueError, OSError, configparser.Error) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    return 0


def _parser() -> argparse.ArgumentParser:
    """Описать позиционный аргумент и режимы CLI."""
    parser = argparse.ArgumentParser(description="Граф зависимостей NuGet")
    parser.add_argument("config", type=Path, help="путь к файлу INI")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--show-config", action="store_true",
                       help="вывести параметры в формате ключ=значение")
    modes.add_argument("--direct", action="store_true",
                       help="вывести прямые зависимости из метаданных")
    modes.add_argument("--load-order", action="store_true",
                       help="вывести зависимости раньше потребителей")
    modes.add_argument("--levels", action="store_true",
                       help="вывести уровни BFS без создания файлов")
    return parser


def _execute(args: argparse.Namespace, config: Config) -> None:
    """Выбрать действие после полной проверки настроек."""
    if args.show_config:
        print(config_text(config))
        return
    package = Package(config.package, config.version)
    repository = _repository(config, package)
    if args.direct:
        _print_direct(repository, package)
        return
    graph = build_graph(package, repository.children, config.max_depth)
    if args.load_order:
        print(order_text(graph))
    elif args.levels:
        print(levels_text(graph))
    else:
        dot_file = save_diagram(graph, config.output)
        print(f"DOT: {dot_file}\nSVG: {config.output}")
        if config.ascii_tree:
            print(ascii_tree(graph))


def _repository(config: Config, package: Package) -> Repository:
    """Выбрать сетевой или локальный источник данных."""
    if config.test_mode:
        repository = TestRepository(Path(config.repository))
        repository.check_root(package)
        return repository
    return NuGetRepository(config.repository, config.target_framework)


def _print_direct(repository: Repository, package: Package) -> None:
    """Показать прямые зависимости с их исходными ограничениями."""
    dependencies = repository.declared_dependencies(package)
    print(f"Прямые зависимости {package}:")
    for dependency in dependencies:
        print(f"  {dependency}")
    if not dependencies:
        print("  нет")


if __name__ == "__main__":
    raise SystemExit(main())
