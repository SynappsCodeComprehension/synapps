from __future__ import annotations

import logging

from synapse.indexer.tree_sitter_util import find_enclosing_scope, node_text

log = logging.getLogger(__name__)

_JAVA_CALLS_QUERY = """
(method_invocation name: (identifier) @callee) @call
(object_creation_expression type: (type_identifier) @callee) @new_call
"""

# tree-sitter node types that introduce a method/constructor scope
_METHOD_SCOPE_TYPES = {"method_declaration", "constructor_declaration", "lambda_expression"}
# tree-sitter node types that represent class/interface body (calls here are field initializers)
_CLASS_SCOPE_TYPES = {"class_body", "interface_body", "enum_body"}


class JavaCallExtractor:
    """
    Parses a Java source file with tree-sitter and returns call sites as
    (caller_full_name, callee_simple_name, line_1indexed, col_0indexed) tuples.

    Detects method_invocation (including chained calls) and
    object_creation_expression (new Foo()) per D-17.

    Scope classification uses tree-sitter parent traversal to skip
    class-body field initializer calls (same approach as Python/TypeScript).
    """

    def __init__(self) -> None:
        import tree_sitter_java as ts_java
        from tree_sitter import Language, Parser, Query, QueryCursor

        self._language = Language(ts_java.language())
        self._parser = Parser(self._language)
        self._query = Query(self._language, _JAVA_CALLS_QUERY)
        self._QueryCursor = QueryCursor
        self._sites_seen: int = 0

    def extract(
        self,
        file_path: str,
        source: str,
        symbol_map: dict[tuple[str, int], str],
        *,
        module_name_resolver=None,
        class_lines=None,
    ) -> list[tuple[str, str, int, int]]:
        """
        :param file_path: absolute path (used as key prefix in symbol_map).
        :param source: full UTF-8 source text.
        :param symbol_map: maps (file_path, 0-indexed line) -> method full_name.
        :returns: list of (caller_full_name, callee_simple_name,
                  1-indexed call line, 0-indexed call column).
        """
        if not source.strip():
            return []

        self._sites_seen = 0

        try:
            tree = self._parser.parse(bytes(source, "utf-8"))
        except Exception:
            log.warning("tree-sitter failed to parse %s", file_path)
            return []

        method_lines = sorted(
            (line, full_name)
            for (fp, line), full_name in symbol_map.items()
            if fp == file_path
        )

        results: list[tuple[str, str, int, int]] = []
        seen: set[tuple[str, str, int, int]] = set()

        cursor = self._QueryCursor(self._query)
        for _pattern_idx, captures in cursor.matches(tree.root_node):
            nodes = captures.get("callee", [])
            for node in nodes:
                scope_type = self._get_call_scope(node)

                # Skip calls in class body that are outside any method
                # (field initializers, static initializer blocks without methods)
                if scope_type == "class":
                    continue

                call_line_0 = node.start_point[0]
                call_col_0 = node.start_point[1]
                callee_name = node_text(node)

                caller = find_enclosing_scope(call_line_0, method_lines)
                if caller is None:
                    continue

                self._sites_seen += 1

                entry = (caller, callee_name, call_line_0 + 1, call_col_0)
                if entry not in seen:
                    seen.add(entry)
                    results.append(entry)

        return results

    @staticmethod
    def _get_call_scope(node) -> str:
        """
        Walk the parent chain to determine what scope this call node lives in.

        Returns 'method' if inside a method/constructor/lambda,
        'class' if directly inside a class body (field initializer),
        'file' if at file top level (shouldn't happen in valid Java).
        """
        parent = node.parent
        while parent is not None:
            if parent.type in _METHOD_SCOPE_TYPES:
                return "method"
            if parent.type in _CLASS_SCOPE_TYPES:
                return "class"
            parent = parent.parent
        return "file"
