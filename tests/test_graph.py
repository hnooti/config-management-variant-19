"""Проверка BFS на ветвлении, общем потомке, цикле и ограничении."""

import tempfile
import unittest
from pathlib import Path

from src.graph import build_graph
from src.model import Package
from src.test_repository import TestRepository
from src.version import parse_version

VERSION = parse_version("1")


def package(name: str) -> Package:
    """Создать вершину тестовой версии."""
    return Package(name, VERSION)


def example_graph(fixture: str, limit: int):
    """Загрузить пример из репозитория и построить его граф."""
    repository = TestRepository(Path(f"examples/{fixture}.json"))
    return build_graph(package("A"), repository.children, limit)


class GraphTests(unittest.TestCase):
    """Сценарии обхода тестовых зависимостей."""

    def test_shared_dependency(self):
        """Сохранить обе связи к D, запросив D только один раз."""
        source = TestRepository(Path("examples/diamond.json"))
        queried = []

        def children(node):
            """Запомнить вызов и вернуть рёбра."""
            queried.append(node.name)
            return source.children(node)

        graph = build_graph(package("A"), children, 5)
        self.assertEqual(queried, ["A", "B", "C", "D", "E"])
        self.assertEqual(list(graph.depths.values()), [0, 1, 1, 2, 2])
        self.assertIn(package("D"), graph.edges[package("B")])
        self.assertIn(package("D"), graph.edges[package("C")])

    def test_cycle_edge_is_retained(self):
        """Завершить обход и сохранить замыкающее цикл ребро."""
        graph = example_graph("cycle", 5)
        self.assertEqual(set(graph.depths), set(map(package, "ABCD")))
        self.assertEqual(graph.edges[package("C")], (package("A"),))

    def test_depth_is_maximum_distance(self):
        """Сохранить граничные вершины без запроса их зависимостей."""
        graph = example_graph("diamond", 1)
        self.assertEqual(list(graph.depths), list(map(package, "ABC")))
        self.assertEqual(list(graph.edges), [package("A")])
        self.assertEqual(graph.boundary(), (package("B"), package("C")))
        root_only = example_graph("diamond", 0)
        self.assertEqual(list(root_only.depths), [package("A")])
        self.assertFalse(root_only.edges)

    def test_dangling_reference(self):
        """Выдать ошибку для неполного списка смежности."""
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "invalid.json"
            file.write_text('{"A":["Z"]}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "A ссылается на Z"):
                TestRepository(file)
