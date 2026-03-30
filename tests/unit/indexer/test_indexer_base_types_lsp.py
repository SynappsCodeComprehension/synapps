"""Unit tests for LSP-backed base type resolution in _index_base_types().

These tests verify that _index_base_types() uses LSP request_definition() +
symbol_map lookup rather than the name-heuristic approach.
"""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, call

import pytest
import tree_sitter_c_sharp
from tree_sitter import Language, Parser

from synapps.indexer.indexer import Indexer
from synapps.lsp.interface import IndexSymbol, LSPAdapter, SymbolKind

_lang = Language(tree_sitter_c_sharp.language())
_parser = Parser(_lang)


def _parse(source: str):
    return _parser.parse(bytes(source, "utf-8"))


def _mock_ls(definitions: list[dict] | None = None, raises: Exception | None = None):
    """Create a mock LSPResolverBackend.

    definitions: list of Location dicts to return from request_definition
    raises: if set, request_definition raises this exception
    """
    ls = MagicMock()

    @contextmanager
    def _open_file(rel_path):
        yield

    ls.open_file = _open_file

    if raises is not None:
        ls.request_definition.side_effect = raises
    else:
        ls.request_definition.return_value = definitions if definitions is not None else []

    return ls


def _mock_ls_open_fails():
    """Create a mock LSPResolverBackend whose open_file context manager raises."""
    ls = MagicMock()

    @contextmanager
    def _open_file_raises(rel_path):
        raise Exception("open_file failed")
        yield  # noqa: unreachable — required for contextmanager protocol

    ls.open_file = _open_file_raises
    return ls


def _make_indexer(language: str = "csharp"):
    """Create an Indexer with mock connection and mock LSP adapter."""
    from synapps.indexer.csharp.csharp_base_type_extractor import CSharpBaseTypeExtractor

    mock_conn = MagicMock()

    mock_lsp = MagicMock(spec=LSPAdapter)
    mock_lsp.file_extensions = frozenset({".cs"})

    plugin = MagicMock()
    plugin.name = language
    plugin.file_extensions = frozenset({".cs"})
    plugin.create_import_extractor.return_value = None
    plugin.create_base_type_extractor.return_value = CSharpBaseTypeExtractor()
    plugin.create_attribute_extractor = MagicMock(return_value=None)
    plugin.create_call_extractor = MagicMock(return_value=None)
    plugin.create_type_ref_extractor = MagicMock(return_value=None)
    plugin.create_assignment_extractor = MagicMock(return_value=None)
    plugin.create_http_extractor = MagicMock(return_value=None)

    indexer = Indexer(mock_conn, mock_lsp, plugin)
    return indexer, mock_conn


def _location(abs_path: str, line: int, col: int = 0) -> dict:
    """Build a Location dict as returned by LSP request_definition."""
    return {
        "absolutePath": abs_path,
        "range": {"start": {"line": line, "character": col}, "end": {"line": line, "character": col + 10}},
    }


def _collect_edges(mock_conn) -> dict[str, list[tuple[str, str]]]:
    """Extract edge upsert calls grouped by edge type from conn.execute calls."""
    edges: dict[str, list[tuple[str, str]]] = {"INHERITS": [], "IMPLEMENTS": [], "INTERFACE_INHERITS": []}
    for c in mock_conn.execute.call_args_list:
        cypher, params = c[0]
        if "INHERITS" in cypher and "cls" in params and "base" in params:
            edges["INHERITS"].append((params["cls"], params["base"]))
        if "IMPLEMENTS" in cypher and "cls" in params and "iface" in params:
            edges["IMPLEMENTS"].append((params["cls"], params["iface"]))
        if "INTERFACE_INHERITS" in cypher:
            # interface_inherits uses child/parent parameter names
            child = params.get("child") or params.get("cls") or params.get("sub")
            parent = params.get("parent") or params.get("base") or params.get("iface")
            if child and parent:
                edges["INTERFACE_INHERITS"].append((child, parent))
    return edges


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLspHitCreatesInherits:
    """LSP returns a definition in symbol_map -> INHERITS edge written."""

    def test_lsp_hit_creates_inherits(self):
        indexer, mock_conn = _make_indexer()

        source = "class Dog : Animal {}"
        tree = _parse(source)

        abs_path = "/proj/Animal.cs"
        symbol_map = {(abs_path, 0): "Animals.Animal"}
        kind_map = {
            "Animals.Dog": SymbolKind.CLASS,
            "Animals.Animal": SymbolKind.CLASS,
        }
        name_to_full_names = {"Dog": ["Animals.Dog"]}
        ls = _mock_ls(definitions=[_location(abs_path, 0)])

        indexer._index_base_types("/proj/Dog.cs", tree, symbol_map, kind_map, ls, "/proj", name_to_full_names)

        edges = _collect_edges(mock_conn)
        assert ("Animals.Dog", "Animals.Animal") in edges["INHERITS"]


class TestLspHitCreatesImplements:
    """Class implements interface (base_kind == INTERFACE) -> IMPLEMENTS edge."""

    def test_lsp_hit_creates_implements(self):
        indexer, mock_conn = _make_indexer(language="python")

        source = "class Cache : ICache {}"
        tree = _parse(source)

        abs_path = "/proj/ICache.cs"
        symbol_map = {(abs_path, 0): "Services.ICache"}
        kind_map = {
            "Services.Cache": SymbolKind.CLASS,
            "Services.ICache": SymbolKind.INTERFACE,
        }
        name_to_full_names = {"Cache": ["Services.Cache"]}
        ls = _mock_ls(definitions=[_location(abs_path, 0)])

        indexer._index_base_types("/proj/Cache.cs", tree, symbol_map, kind_map, ls, "/proj", name_to_full_names)

        edges = _collect_edges(mock_conn)
        assert ("Services.Cache", "Services.ICache") in edges["IMPLEMENTS"]


class TestLspHitCreatesInterfaceInherits:
    """Interface extends interface -> INTERFACE_INHERITS edge."""

    def test_lsp_hit_creates_interface_inherits(self):
        indexer, mock_conn = _make_indexer(language="python")

        source = "class IExtended : IBase {}"
        tree = _parse(source)

        abs_path = "/proj/IBase.cs"
        symbol_map = {(abs_path, 0): "NS.IBase"}
        kind_map = {
            "NS.IExtended": SymbolKind.INTERFACE,
            "NS.IBase": SymbolKind.INTERFACE,
        }
        name_to_full_names = {"IExtended": ["NS.IExtended"]}
        ls = _mock_ls(definitions=[_location(abs_path, 0)])

        indexer._index_base_types("/proj/IExtended.cs", tree, symbol_map, kind_map, ls, "/proj", name_to_full_names)

        edges = _collect_edges(mock_conn)
        assert ("NS.IExtended", "NS.IBase") in edges["INTERFACE_INHERITS"]


class TestLspCsharpFirstBaseDualWrite:
    """C# first base writes both INHERITS and IMPLEMENTS (existing logic)."""

    def test_lsp_csharp_first_base_dual_write(self):
        indexer, mock_conn = _make_indexer(language="csharp")

        source = "class Dog : Animal {}"
        tree = _parse(source)

        abs_path = "/proj/Animal.cs"
        symbol_map = {(abs_path, 0): "NS.Animal"}
        kind_map = {
            "NS.Dog": SymbolKind.CLASS,
            "NS.Animal": SymbolKind.CLASS,
        }
        name_to_full_names = {"Dog": ["NS.Dog"]}
        ls = _mock_ls(definitions=[_location(abs_path, 0)])

        indexer._index_base_types("/proj/Dog.cs", tree, symbol_map, kind_map, ls, "/proj", name_to_full_names)

        edges = _collect_edges(mock_conn)
        # For C# first base: both INHERITS and IMPLEMENTS are written (typed MATCH guards
        # ensure only the semantically correct one persists in the graph)
        assert ("NS.Dog", "NS.Animal") in edges["INHERITS"]
        assert ("NS.Dog", "NS.Animal") in edges["IMPLEMENTS"]


class TestLspNoDefinitionsSkips:
    """LSP returns [] -> no edges written, no error raised."""

    def test_lsp_no_definitions_skips(self):
        indexer, mock_conn = _make_indexer()

        source = "class Dog : Animal {}"
        tree = _parse(source)

        ls = _mock_ls(definitions=[])
        symbol_map: dict = {}
        kind_map = {"NS.Dog": SymbolKind.CLASS}
        name_to_full_names = {"Dog": ["NS.Dog"]}

        # Should not raise
        indexer._index_base_types("/proj/Dog.cs", tree, symbol_map, kind_map, ls, "/proj", name_to_full_names)

        mock_conn.execute.assert_not_called()


class TestLspExternalTypeSkipped:
    """LSP returns definition at location NOT in symbol_map -> no edges."""

    def test_lsp_external_type_skipped(self):
        indexer, mock_conn = _make_indexer()

        source = "class Dog : Animal {}"
        tree = _parse(source)

        # Definition points to a location not in symbol_map
        ls = _mock_ls(definitions=[_location("/external/lib/Animal.cs", 42)])
        symbol_map: dict = {}  # empty — external type not indexed
        kind_map = {"NS.Dog": SymbolKind.CLASS}
        name_to_full_names = {"Dog": ["NS.Dog"]}

        indexer._index_base_types("/proj/Dog.cs", tree, symbol_map, kind_map, ls, "/proj", name_to_full_names)

        mock_conn.execute.assert_not_called()


class TestLspExceptionSkips:
    """LSP raises Exception on request_definition -> no edges, no crash."""

    def test_lsp_exception_skips(self):
        indexer, mock_conn = _make_indexer()

        source = "class Dog : Animal {}"
        tree = _parse(source)

        ls = _mock_ls(raises=RuntimeError("LSP crashed"))
        symbol_map: dict = {}
        kind_map = {"NS.Dog": SymbolKind.CLASS}
        name_to_full_names = {"Dog": ["NS.Dog"]}

        # Must not raise
        indexer._index_base_types("/proj/Dog.cs", tree, symbol_map, kind_map, ls, "/proj", name_to_full_names)

        mock_conn.execute.assert_not_called()


class TestLspOpenFileFailure:
    """open_file raises Exception -> entire file skipped gracefully."""

    def test_lsp_open_file_failure(self):
        indexer, mock_conn = _make_indexer()

        source = "class Dog : Animal {}"
        tree = _parse(source)

        ls = _mock_ls_open_fails()
        symbol_map = {("/proj/Animal.cs", 0): "NS.Animal"}
        kind_map = {"NS.Dog": SymbolKind.CLASS, "NS.Animal": SymbolKind.CLASS}
        name_to_full_names = {"Dog": ["NS.Dog"]}

        # Must not raise
        indexer._index_base_types("/proj/Dog.cs", tree, symbol_map, kind_map, ls, "/proj", name_to_full_names)

        mock_conn.execute.assert_not_called()


class TestMultipleBaseTypes:
    """Class with 3 bases -> 3 LSP calls, correct edges for each."""

    def test_multiple_base_types(self):
        indexer, mock_conn = _make_indexer(language="python")

        # Python-style inheritance (3 bases)
        source = "class MyClass(Base, IFoo, IBar): pass"

        import tree_sitter_python
        from tree_sitter import Language as TSLanguage, Parser as TSParser
        py_lang = TSLanguage(tree_sitter_python.language())
        py_parser = TSParser(py_lang)
        py_tree = py_parser.parse(bytes(source, "utf-8"))

        from synapps.plugin.python import PythonPlugin
        mock_conn2 = MagicMock()
        mock_lsp2 = MagicMock(spec=LSPAdapter)
        mock_lsp2.file_extensions = frozenset({".py"})
        plugin2 = PythonPlugin()
        indexer2 = Indexer(mock_conn2, mock_lsp2, plugin2)

        base_abs = "/proj/Base.py"
        ifoo_abs = "/proj/IFoo.py"
        ibar_abs = "/proj/IBar.py"

        symbol_map = {
            (base_abs, 5): "mymod.Base",
            (ifoo_abs, 3): "mymod.IFoo",
            (ibar_abs, 7): "mymod.IBar",
        }
        kind_map = {
            "mymod.MyClass": SymbolKind.CLASS,
            "mymod.Base": SymbolKind.CLASS,
            "mymod.IFoo": SymbolKind.INTERFACE,
            "mymod.IBar": SymbolKind.INTERFACE,
        }
        name_to_full_names = {"MyClass": ["mymod.MyClass"]}

        def _request_def(rel_path, line, col):
            # Return different definitions based on what's being queried
            # We can't easily distinguish which base is being queried via position alone
            # so just return the first matching entry — use call count to rotate
            call_count = _request_def.count
            _request_def.count += 1
            if call_count == 0:
                return [_location(base_abs, 5)]
            elif call_count == 1:
                return [_location(ifoo_abs, 3)]
            else:
                return [_location(ibar_abs, 7)]
        _request_def.count = 0

        ls = MagicMock()

        @contextmanager
        def _open_file(rel_path):
            yield

        ls.open_file = _open_file
        ls.request_definition.side_effect = _request_def

        indexer2._index_base_types("/proj/MyClass.py", py_tree, symbol_map, kind_map, ls, "/proj", name_to_full_names)

        assert ls.request_definition.call_count == 3
        edges = _collect_edges(mock_conn2)
        assert ("mymod.MyClass", "mymod.Base") in edges["INHERITS"]
        assert ("mymod.MyClass", "mymod.IFoo") in edges["IMPLEMENTS"]
        assert ("mymod.MyClass", "mymod.IBar") in edges["IMPLEMENTS"]


class TestDeclaringTypeResolvedViaNameToFullNames:
    """type_simple is looked up in name_to_full_names (the declaring type)."""

    def test_declaring_type_resolved_via_name_to_full_names(self):
        indexer, mock_conn = _make_indexer()

        source = "class Dog : Animal {}"
        tree = _parse(source)

        abs_path = "/proj/Animal.cs"
        symbol_map = {(abs_path, 0): "NS.Animal"}
        kind_map = {
            "NS.Dog": SymbolKind.CLASS,
            "NS.Animal": SymbolKind.CLASS,
        }
        # Two possible full names for "Dog" — both should get edges
        name_to_full_names = {"Dog": ["NS.Dog", "NS2.Dog"]}
        ls = _mock_ls(definitions=[_location(abs_path, 0)])

        indexer._index_base_types("/proj/Dog.cs", tree, symbol_map, kind_map, ls, "/proj", name_to_full_names)

        edges = _collect_edges(mock_conn)
        assert ("NS.Dog", "NS.Animal") in edges["INHERITS"]
        assert ("NS2.Dog", "NS.Animal") in edges["INHERITS"]
