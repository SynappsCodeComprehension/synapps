"""Unit tests for the cross-file string constant collection utility."""
from __future__ import annotations

import tree_sitter_python
import tree_sitter_typescript
from tree_sitter import Language, Parser

from synapse.indexer.http.constants_resolver import collect_cross_file_constants
from synapse.indexer.tree_sitter_util import ParsedFile

_py_lang = Language(tree_sitter_python.language())
_py_parser = Parser(_py_lang)

_ts_lang = Language(tree_sitter_typescript.language_typescript())
_ts_parser = Parser(_ts_lang)


def _py_parsed(source: str, path: str = "test.py") -> ParsedFile:
    tree = _py_parser.parse(bytes(source, "utf-8"))
    return ParsedFile(file_path=path, source=source, tree=tree)


def _ts_parsed(source: str, path: str = "test.ts") -> ParsedFile:
    tree = _ts_parser.parse(bytes(source, "utf-8"))
    return ParsedFile(file_path=path, source=source, tree=tree)


# ──────────────────────────────────────────────
# Python constant collection
# ──────────────────────────────────────────────


def test_python_collects_url_constant() -> None:
    source = 'API_URL = "/api/users"\n'
    pf = _py_parsed(source, "constants.py")
    result = collect_cross_file_constants({"constants.py": pf}, "python")
    assert result == {"constants.py": {"API_URL": "/api/users"}}


def test_python_collects_http_url_constant() -> None:
    source = 'BASE_URL = "http://example.com/api"\n'
    pf = _py_parsed(source, "constants.py")
    result = collect_cross_file_constants({"constants.py": pf}, "python")
    assert result == {"constants.py": {"BASE_URL": "http://example.com/api"}}


def test_python_skips_non_string_assignment() -> None:
    source = "COUNT = 42\n"
    pf = _py_parsed(source, "constants.py")
    result = collect_cross_file_constants({"constants.py": pf}, "python")
    assert result == {}


def test_python_skips_string_without_slash_or_http() -> None:
    source = 'LABEL = "hello"\n'
    pf = _py_parsed(source, "constants.py")
    result = collect_cross_file_constants({"constants.py": pf}, "python")
    assert result == {}


def test_python_skips_nested_assignment() -> None:
    source = """\
def foo():
    URL = "/api/path"
"""
    pf = _py_parsed(source, "constants.py")
    result = collect_cross_file_constants({"constants.py": pf}, "python")
    assert result == {}


def test_python_multi_file_collection() -> None:
    source_a = 'USERS_URL = "/api/users"\n'
    source_b = 'ITEMS_URL = "/api/items"\n'
    pf_a = _py_parsed(source_a, "a.py")
    pf_b = _py_parsed(source_b, "b.py")
    result = collect_cross_file_constants({"a.py": pf_a, "b.py": pf_b}, "python")
    assert "a.py" in result
    assert "b.py" in result
    assert result["a.py"] == {"USERS_URL": "/api/users"}
    assert result["b.py"] == {"ITEMS_URL": "/api/items"}


def test_python_empty_file() -> None:
    pf = _py_parsed("", "empty.py")
    result = collect_cross_file_constants({"empty.py": pf}, "python")
    assert result == {}


# ──────────────────────────────────────────────
# TypeScript constant collection
# ──────────────────────────────────────────────


def test_typescript_collects_const_url() -> None:
    source = "const API_URL = '/api/users';\n"
    pf = _ts_parsed(source, "constants.ts")
    result = collect_cross_file_constants({"constants.ts": pf}, "typescript")
    assert result == {"constants.ts": {"API_URL": "/api/users"}}


def test_typescript_collects_let_url() -> None:
    source = "let BASE_URL = '/api';\n"
    pf = _ts_parsed(source, "constants.ts")
    result = collect_cross_file_constants({"constants.ts": pf}, "typescript")
    assert result == {"constants.ts": {"BASE_URL": "/api"}}


def test_typescript_skips_non_url_string() -> None:
    source = "const LABEL = 'hello';\n"
    pf = _ts_parsed(source, "constants.ts")
    result = collect_cross_file_constants({"constants.ts": pf}, "typescript")
    assert result == {}


def test_typescript_empty_file() -> None:
    pf = _ts_parsed("", "empty.ts")
    result = collect_cross_file_constants({"empty.ts": pf}, "typescript")
    assert result == {}


# ──────────────────────────────────────────────
# Unknown language
# ──────────────────────────────────────────────


def test_unknown_language_returns_empty() -> None:
    source = 'API_URL = "/api/users"\n'
    pf = _py_parsed(source, "test.rb")
    result = collect_cross_file_constants({"test.rb": pf}, "ruby")
    assert result == {}
