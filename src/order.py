"""Расчёт порядка, в котором зависимости предшествуют потребителям."""

from collections import deque

from .graph import Graph
from .model import Package


def load_order(graph: Graph) -> tuple[Package, ...]:
    """Применить алгоритм Кана, начиная с пакетов без зависимостей."""
    pending = {node: len(graph.edges.get(node, ())) for node in graph.depths}
    consumers = _consumers(graph)
    ready = deque(node for node, count in pending.items() if not count)
    result: list[Package] = []
    while ready:
        node = ready.popleft()
        result.append(node)
        for consumer in consumers[node]:
            pending[consumer] -= 1
            if not pending[consumer]:
                ready.append(consumer)
    if len(result) != len(pending):
        blocked = ", ".join(str(node) for node in pending if pending[node])
        raise ValueError(f"цикл; порядок загрузки невозможен: {blocked}")
    return tuple(result)


def _consumers(graph: Graph) -> dict[Package, list[Package]]:
    """Построить обратное соответствие «зависимость → потребители»."""
    reverse: dict[Package, list[Package]] = {node: [] for node in graph.depths}
    for parent, children in graph.edges.items():
        for child in children:
            reverse[child].append(parent)
    return reverse


def order_text(graph: Graph) -> str:
    """Отформатировать порядок с предупреждением об обрезанном графе."""
    order = load_order(graph)
    lines = ["Порядок загрузки (зависимости раньше потребителей):"]
    if graph.boundary():
        lines.append("Граф ограничен глубиной; порядок только для видимых рёбер.")
    lines.extend(f"{index}. {node}" for index, node in enumerate(order, 1))
    return "\n".join(lines)
