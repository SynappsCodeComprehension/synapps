from __future__ import annotations

import logging

from tree_sitter import Tree

from synapps.indexer.tree_sitter_util import node_text

log = logging.getLogger(__name__)

_DECL_TYPES = frozenset({
    "class_declaration",
    "interface_declaration",
    "record_declaration",
    "struct_declaration",
})


class CSharpBaseTypeExtractor:
    def __init__(self) -> None:
        pass

    def extract(self, file_path: str, tree: Tree) -> list[tuple[str, str, bool, int, int]]:
        """Return (type_name, base_name, is_first, line, col) 5-tuples for all base type entries found."""
        results: list[tuple[str, str, bool, int, int]] = []
        self._walk(tree.root_node, results)
        return results

    def _walk(self, node, results: list[tuple[str, str, bool, int, int]]) -> None:
        if node.type in _DECL_TYPES:
            self._handle_decl(node, results)
        for child in node.children:
            self._walk(child, results)

    def _handle_decl(self, node, results: list[tuple[str, str, bool, int, int]]) -> None:
        type_name: str | None = None
        base_list_node = None

        for child in node.children:
            if child.type == "identifier" and type_name is None:
                type_name = node_text(child)
            elif child.type == "base_list":
                base_list_node = child

        if type_name is None or base_list_node is None:
            return

        base_entries = [
            c for c in base_list_node.children
            if c.type not in (":", ",")
        ]

        for idx, entry in enumerate(base_entries):
            base_info = _extract_base_name(entry)
            if base_info:
                base_name, line, col = base_info
                results.append((type_name, base_name, idx == 0, line, col))


def _extract_base_name(node) -> tuple[str, int, int] | None:
    if node.type == "identifier":
        return (node_text(node), node.start_point[0], node.start_point[1])
    if node.type == "generic_name":
        # First child is the unqualified identifier before the type argument list
        for child in node.children:
            if child.type == "identifier":
                return (node_text(child), child.start_point[0], child.start_point[1])
    if node.type == "qualified_name":
        # Recurse left-to-right, keeping the last result; tree is left-recursive so
        # the rightmost leaf is always the simple type name we need for name lookup.
        # Example: "A.B.C" → qualified_name(qualified_name(A,B), C) → returns "C"
        last: tuple[str, int, int] | None = None
        for child in node.children:
            if child.type == ".":
                continue
            candidate = _extract_base_name(child)
            if candidate:
                last = candidate
        return last
    return None
