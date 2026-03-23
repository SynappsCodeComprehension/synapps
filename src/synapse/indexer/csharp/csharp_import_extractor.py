from __future__ import annotations

import logging

from tree_sitter import Tree

from synapse.indexer.tree_sitter_util import node_text

log = logging.getLogger(__name__)


class CSharpImportExtractor:
    def __init__(self) -> None:
        pass

    def extract(self, file_path: str, tree: Tree) -> list[str]:
        """Return deduplicated package names imported by this file."""
        results: list[str] = []
        seen: set[str] = set()
        self._walk(tree.root_node, results, seen)
        return results

    def _walk(self, node, results: list[str], seen: set[str]) -> None:
        if node.type == "using_directive":
            self._handle_using_directive(node, results, seen)
            return  # using directives don't nest
        for child in node.children:
            self._walk(child, results, seen)

    def _handle_using_directive(self, node, results: list[str], seen: set[str]) -> None:
        child_types = {c.type for c in node.children}
        # Skip: using static ...
        if "static" in child_types:
            return
        # Skip: using Alias = ...  (alias directives have '=' as a child token)
        if "=" in child_types:
            return
        for child in node.children:
            if child.type in ("identifier", "qualified_name"):
                name = node_text(child)
                if name and name not in seen:
                    seen.add(name)
                    results.append(name)
                break
