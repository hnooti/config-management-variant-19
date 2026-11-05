"""Проверка допустимого порядка и отказа от сортировки цикла."""

import unittest

from src.order import load_order, order_text
from test_graph import example_graph, package


class OrderTests(unittest.TestCase):
    """Топологическая сортировка тестовых графов."""

    def test_dependencies_before_consumers(self):
        """Каждый потомок предшествует своему потребителю."""
        graph = example_graph("diamond", 5)
        order = load_order(graph)
        self.assertEqual(len(order), len(graph.depths))
        self.assertEqual(order[-1], graph.root)
        for node, children in graph.edges.items():
            for child in children:
                self.assertLess(order.index(child), order.index(node))

    def test_cycle_prevents_order(self):
        """При цикле не выдавать частичный порядок за полный."""
        with self.assertRaisesRegex(ValueError, "цикл"):
            load_order(example_graph("cycle", 5))

    def test_depth_limited_order(self):
        """При ограничении явно указать, что часть рёбер не запрошена."""
        graph = example_graph("diamond", 1)
        self.assertEqual(load_order(graph), tuple(map(package, "BCA")))
        self.assertIn("только для видимых рёбер", order_text(graph))
