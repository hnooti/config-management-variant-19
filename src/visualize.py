"""Представление графа в DOT, SVG и ASCII."""

import json
import subprocess
from collections.abc import Iterator
from pathlib import Path

from .graph import Graph
from .model import Package

DOT_TIMEOUT = 30
DOT_HEADER = """digraph dependencies {
  graph [rankdir=LR, bgcolor="white", pad=0.25, nodesep=0.35];
  node [shape=box, style="rounded,filled", fillcolor="#f1f5f9",
        color="#64748b", fontname="Helvetica", margin="0.18,0.10"];
  edge [color="#64748b", arrowsize=0.7];"""


def to_dot(graph: Graph) -> str:
    """Сформировать описание Graphviz с отдельным ID каждой вершины."""
    ids = {node: f"n{index}" for index, node in enumerate(graph.depths)}
    lines = [DOT_HEADER]
    lines.extend(_dot_node(graph, node, name) for node, name in ids.items())
    for parent, children in graph.edges.items():
        lines.extend(f"  {ids[parent]} -> {ids[child]};" for child in children)
    lines.append("}")
    return "\n".join(lines) + "\n"


def _dot_node(graph: Graph, node: Package, name: str) -> str:
    """Выделить корень цветом, а границу глубины пунктиром."""
    label = json.dumps(f"{node.name}\n{node.version}")
    attrs = [f"label={label}"]
    if node == graph.root:
        attrs.append('fillcolor="#dbeafe"')
    if node not in graph.edges:
        attrs.append('style="rounded,filled,dashed"')
    return f"  {name} [{', '.join(attrs)}];"


def save_diagram(graph: Graph, output: Path) -> Path:
    """Записать SVG и соседний DOT после успешного вызова Graphviz."""
    dot_file = output.with_suffix(".dot")
    if dot_file.is_dir():
        raise ValueError(f"не удалось сохранить DOT: указан каталог {dot_file}")
    source = to_dot(graph)
    svg = _render_svg(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(svg)
    dot_file.write_text(source, encoding="utf-8")
    return dot_file


def _render_svg(source: str) -> bytes:
    """Преобразовать DOT в SVG с помощью команды dot."""
    try:
        result = subprocess.run(
            ["dot", "-Tsvg"], input=source.encode("utf-8"),
            capture_output=True, check=True, timeout=DOT_TIMEOUT,
        )
    except FileNotFoundError as error:
        message = "установите Graphviz: команда dot не найдена"
        raise ValueError(message) from error
    except subprocess.CalledProcessError as error:
        details = error.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"Graphviz: {details}") from error
    except subprocess.TimeoutExpired as error:
        raise ValueError("Graphviz не завершил построение SVG") from error
    return result.stdout


def ascii_tree(graph: Graph) -> str:
    """Показать рёбра деревом, обозначив циклы и повторные вершины."""
    rows: list[str] = []
    shown: set[Package] = set()
    active: set[Package] = set()

    stack = [(graph.root, "", "", False)]
    while stack:
        node, line, prefix, leave = stack.pop()
        if leave:
            active.remove(node)
            continue
        marker = _tree_marker(graph, node, active, shown)
        rows.append(f"{line}{node}{marker}")
        if marker:
            continue
        shown.add(node)
        active.add(node)
        stack.append((node, "", "", True))
        children = list(_branches(graph.edges[node], prefix))
        stack.extend(reversed(children))
    return "\n".join(rows)


def _branches(
    children: tuple[Package, ...], prefix: str
) -> Iterator[tuple[Package, str, str, bool]]:
    """Подготовить строки для прямых потомков вершины дерева."""
    for index, child in enumerate(children, 1):
        last = index == len(children)
        branch = "`-- " if last else "|-- "
        indent = "    " if last else "|   "
        yield child, prefix + branch, prefix + indent, False


def _tree_marker(
    graph: Graph, node: Package, active: set[Package], shown: set[Package]
) -> str:
    """Различить цикл, граничную вершину и повтор уже показанной ветви."""
    if node in active:
        return " [cycle]"
    if node not in graph.edges:
        return " [depth limit]"
    if node in shown:
        return " [seen]"
    return ""
