"""Построение графа зависимостей рекурсивным обходом в ширину."""

from collections.abc import Callable
from dataclasses import dataclass

from .model import Package

GetChildren = Callable[[Package], tuple[Package, ...]]


@dataclass(frozen=True)
class Graph:
    """Вершины с минимальными расстояниями и рёбра «пакет → зависимость»."""

    root: Package
    depths: dict[Package, int]
    edges: dict[Package, tuple[Package, ...]]

    def boundary(self) -> tuple[Package, ...]:
        """Вернуть вершины, чьи зависимости не были запрошены."""
        return tuple(node for node in self.depths if node not in self.edges)


def build_graph(root: Package, get_children: GetChildren, limit: int) -> Graph:
    """Обойти достижимые пакеты, не раскрывая вершины на границе."""
    graph = Graph(root, {root: 0}, {})
    _walk_level(graph, [root], get_children, limit)
    return graph


def _walk_level(
    graph: Graph, frontier: list[Package], get_children: GetChildren, limit: int
) -> None:
    """Полностью обработать текущий уровень перед рекурсивным вызовом."""
    if not frontier:
        return
    depth = graph.depths[frontier[0]]
    if depth >= limit:
        return
    next_level: list[Package] = []
    for package in frontier:
        children = tuple(dict.fromkeys(get_children(package)))
        graph.edges[package] = children
        for child in children:
            if child not in graph.depths:
                graph.depths[child] = depth + 1
                next_level.append(child)
    _walk_level(graph, next_level, get_children, limit)


def levels_text(graph: Graph) -> str:
    """Показать вершины и их минимальные расстояния от корня."""
    rows = [f"Глубина {depth}: {node}"
            for node, depth in graph.depths.items()]
    if graph.boundary():
        rows.append("На предельной глубине зависимости не запрашивались.")
    return "\n".join(rows)
