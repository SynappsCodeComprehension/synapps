from __future__ import annotations

import logging

from synapse.indexer.tree_sitter_util import ParsedFile, node_text

log = logging.getLogger(__name__)


def collect_cross_file_constants(
    parsed_files: dict[str, ParsedFile],
    language: str,
) -> dict[str, dict[str, str]]:
    """Scan parsed files and collect top-level string constants for URL resolution.

    Returns a mapping of file_path -> {constant_name: string_value}.
    Only collects constants whose values contain "/" or start with "http",
    filtering out non-URL strings to reduce noise.
    """
    result: dict[str, dict[str, str]] = {}
    collector = _COLLECTORS.get(language)
    if collector is None:
        return result
    for file_path, pf in parsed_files.items():
        constants = collector(pf.tree.root_node)
        if constants:
            result[file_path] = constants
    return result


def _is_url_like(value: str) -> bool:
    """Return True if the string looks like a URL path or base URL."""
    return "/" in value or value.startswith("http")


def _collect_python_constants(root_node) -> dict[str, str]:
    """Collect top-level name = "string" assignments from a Python module node."""
    constants: dict[str, str] = {}
    for child in root_node.children:
        if child.type != "expression_statement":
            continue
        for sub in child.children:
            if sub.type != "assignment":
                continue
            left = sub.child_by_field_name("left")
            right = sub.child_by_field_name("right")
            if left is None or right is None:
                continue
            if left.type != "identifier":
                continue
            val = _extract_python_string(right)
            if val is not None and _is_url_like(val):
                constants[node_text(left)] = val
    return constants


def _extract_python_string(node) -> str | None:
    """Extract the string value from a Python string node."""
    if node.type != "string":
        return None
    for child in node.children:
        if child.type == "string_content":
            return node_text(child)
    # Empty string literal
    return ""


def _collect_typescript_constants(root_node) -> dict[str, str]:
    """Collect top-level const/let/var string declarations from a TypeScript/JS program node."""
    constants: dict[str, str] = {}
    _ts_walk(root_node, constants, depth=0)
    return constants


def _ts_walk(node, constants: dict[str, str], depth: int) -> None:
    if node.type in ("lexical_declaration", "variable_declaration"):
        for child in node.children:
            if child.type != "variable_declarator":
                continue
            name_node = child.child_by_field_name("name")
            val_node = child.child_by_field_name("value")
            if name_node is None or val_node is None:
                continue
            if name_node.type != "identifier":
                continue
            val = _extract_typescript_string(val_node)
            if val is not None and _is_url_like(val):
                constants[node_text(name_node)] = val
        return

    if depth <= 1:
        for child in node.children:
            _ts_walk(child, constants, depth + 1)


def _extract_typescript_string(node) -> str | None:
    """Extract the string value from a TypeScript string node."""
    if node.type == "string":
        for child in node.children:
            if child.type == "string_fragment":
                return node_text(child)
        return ""
    raw = node_text(node)
    if len(raw) >= 2 and raw[0] in ('"', "'") and raw[-1] == raw[0]:
        return raw[1:-1]
    return None


def _collect_java_constants(root_node) -> dict[str, str]:
    """Collect static final String fields from a Java class body."""
    constants: dict[str, str] = {}
    _java_walk(root_node, constants)
    return constants


def _java_walk(node, constants: dict[str, str]) -> None:
    if node.type == "field_declaration":
        _java_collect_field(node, constants)
        return
    for child in node.children:
        _java_walk(child, constants)


def _java_collect_field(node, constants: dict[str, str]) -> None:
    """Extract static final String field with string_literal initializer."""
    modifiers: list[str] = []
    type_name: str | None = None
    for child in node.children:
        if child.type == "modifiers":
            for mod in child.children:
                modifiers.append(node_text(mod))
        elif child.type in ("type_identifier", "integral_type", "floating_point_type", "void_type"):
            type_name = node_text(child)
        elif child.type == "generic_type":
            type_name = node_text(child)

    if "static" not in modifiers or "final" not in modifiers:
        return
    if type_name not in ("String",):
        return

    for child in node.children:
        if child.type == "variable_declarator":
            name_node = child.child_by_field_name("name")
            val_node = child.child_by_field_name("value")
            if name_node is None or val_node is None:
                continue
            val = _extract_java_string(val_node)
            if val is not None and _is_url_like(val):
                constants[node_text(name_node)] = val


def _extract_java_string(node) -> str | None:
    """Extract the string value from a Java string_literal node."""
    if node.type != "string_literal":
        return None
    raw = node_text(node)
    if len(raw) >= 2 and raw[0] == '"' and raw[-1] == '"':
        return raw[1:-1]
    return None


def _collect_csharp_constants(root_node) -> dict[str, str]:
    """Collect const string and static readonly string fields from a C# file."""
    constants: dict[str, str] = {}
    _csharp_walk(root_node, constants)
    return constants


def _csharp_walk(node, constants: dict[str, str]) -> None:
    if node.type == "field_declaration":
        _csharp_collect_field(node, constants)
        return
    for child in node.children:
        _csharp_walk(child, constants)


def _csharp_collect_field(node, constants: dict[str, str]) -> None:
    """Extract const string or static readonly string field with string initializer."""
    modifiers: list[str] = []
    type_name: str | None = None
    for child in node.children:
        if child.type == "modifier":
            modifiers.append(node_text(child))
        elif child.type == "predefined_type":
            type_name = node_text(child)

    is_const = "const" in modifiers
    is_static_readonly = "static" in modifiers and "readonly" in modifiers
    if not (is_const or is_static_readonly):
        return
    if type_name not in ("string",):
        return

    for child in node.children:
        if child.type == "variable_declaration":
            for sub in child.children:
                if sub.type == "variable_declarator":
                    name_node = sub.child_by_field_name("name")
                    eq_node = sub.child_by_field_name("initializer")
                    if name_node is None or eq_node is None:
                        continue
                    # initializer is an "equals_value_clause" in C# tree-sitter grammar
                    for init_child in eq_node.children:
                        val = _extract_csharp_string(init_child)
                        if val is not None and _is_url_like(val):
                            constants[node_text(name_node)] = val


def _extract_csharp_string(node) -> str | None:
    """Extract the string value from a C# string_literal node."""
    if node.type != "string_literal":
        return None
    raw = node_text(node)
    if len(raw) >= 2 and raw[0] == '"' and raw[-1] == '"':
        return raw[1:-1]
    return None


_COLLECTORS = {
    "python": _collect_python_constants,
    "typescript": _collect_typescript_constants,
    "java": _collect_java_constants,
    "csharp": _collect_csharp_constants,
}
