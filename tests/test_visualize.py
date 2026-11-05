"""Проверка отображения рёбер, циклов и границы глубины."""

import unittest

from src.visualize import ascii_tree, to_dot
from test_graph import example_graph


class VisualizeTests(unittest.TestCase):
    """Текстовые представления графа без запуска внешних программ."""

    def test_shared_child_is_not_a_cycle(self):
        """Показать оба ребра к D, не раскрывая его второй раз."""
        graph = example_graph("diamond", 5)
        result = ascii_tree(graph)
        self.assertEqual(result.count("D@1.0.0"), 2)
        self.assertIn("D@1.0.0 [seen]", result)
        self.assertNotIn("[cycle]", result)
        dot = to_dot(graph)
        self.assertIn("n1 -> n3;", dot)
        self.assertIn("n2 -> n3;", dot)

    def test_cycle_and_depth_limit(self):
        """Пометить цикл и отсечение в соответствующих графах."""
        cycle = example_graph("cycle", 5)
        limited = example_graph("diamond", 1)
        self.assertIn("A@1.0.0 [cycle]", ascii_tree(cycle))
        self.assertIn("n2 -> n0;", to_dot(cycle))
        self.assertIn("B@1.0.0 [depth limit]", ascii_tree(limited))
        self.assertEqual(to_dot(limited).count("dashed"), 2)
