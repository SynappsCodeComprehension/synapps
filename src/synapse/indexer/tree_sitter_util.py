"""Shared tree-sitter utilities used by all language extractors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import tree_sitter


@dataclass(frozen=True)
class ParsedFile:
    """A source file with its tree-sitter parse tree. Created once, shared across all extractors."""
    file_path: str
    source: str
    tree: tree_sitter.Tree


def node_text(node) -> str:
    """Decode a tree-sitter node's text to a Python str."""
    raw = node.text
    return raw.decode("utf-8") if isinstance(raw, bytes) else raw


def find_enclosing_scope(
    line_0: int, sorted_lines: list[tuple[int, str]]
) -> str | None:
    """Return the full_name of the innermost scope whose start line <= line_0.

    Works for both method and class scope lookups. ``sorted_lines`` must be
    sorted ascending by line number.
    """
    best: str | None = None
    for scope_line, full_name in sorted_lines:
        if scope_line <= line_0:
            best = full_name
        else:
            break
    return best
