from __future__ import annotations

import logging

from tree_sitter import Tree

from synapps.indexer.tree_sitter_util import node_text

log = logging.getLogger(__name__)


class PythonBaseTypeExtractor:
    def __init__(self) -> None:
        pass

    def extract(self, file_path: str, tree: Tree) -> list[tuple[str, str, bool, int, int]]:
        """Return (class_name, base_name, is_first, line, col) 5-tuples for all class definitions found."""
        results: list[tuple[str, str, bool, int, int]] = []
        self._walk(tree.root_node, results)
        return results

    def _walk(self, node, results: list[tuple[str, str, bool, int, int]]) -> None:
        if node.type == "class_definition":
            self._handle_class_def(node, results)
        for child in node.children:
            self._walk(child, results)

    def _handle_class_def(self, node, results: list[tuple[str, str, bool, int, int]]) -> None:
        class_name: str | None = None
        superclasses_node = None

        for child in node.children:
            if child.type == "identifier" and class_name is None:
                class_name = node_text(child)
            elif child.type == "argument_list":
                superclasses_node = child

        if class_name is None or superclasses_node is None:
            return

        base_entries = [
            c for c in superclasses_node.children
            if c.type not in ("(", ")", ",")
        ]

        for idx, entry in enumerate(base_entries):
            base_info = _extract_identifier(entry)
            if base_info:
                base_name, line, col = base_info
                results.append((class_name, base_name, idx == 0, line, col))


def _extract_identifier(node) -> tuple[str, int, int] | None:
    if node.type == "identifier":
        return (node_text(node), node.start_point[0], node.start_point[1])
    if node.type == "attribute":
        # Dotted name like `mod.Base` — extract rightmost identifier node
        last_node = None
        for child in node.children:
            if child.type == "identifier":
                last_node = child
        if last_node is not None:
            return (node_text(last_node), last_node.start_point[0], last_node.start_point[1])
    return None
