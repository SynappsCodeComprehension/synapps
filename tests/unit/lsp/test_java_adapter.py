from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from synapse.lsp.interface import IndexSymbol, SymbolKind
from synapse.lsp.java import JavaLSPAdapter, _LSP_KIND_MAP


# ---------------------------------------------------------------------------
# _LSP_KIND_MAP coverage
# ---------------------------------------------------------------------------

class TestLSPKindMap:
    def test_class_mapping(self) -> None:
        assert _LSP_KIND_MAP[5] == SymbolKind.CLASS

    def test_method_mapping(self) -> None:
        assert _LSP_KIND_MAP[6] == SymbolKind.METHOD

    def test_constructor_mapping(self) -> None:
        assert _LSP_KIND_MAP[9] == SymbolKind.METHOD

    def test_interface_mapping(self) -> None:
        assert _LSP_KIND_MAP[11] == SymbolKind.INTERFACE

    def test_enum_mapping(self) -> None:
        assert _LSP_KIND_MAP[10] == SymbolKind.ENUM

    def test_field_mapping(self) -> None:
        assert _LSP_KIND_MAP[8] == SymbolKind.FIELD

    def test_constant_mapping(self) -> None:
        """D-23: static final fields (kind 14) map to FIELD."""
        assert _LSP_KIND_MAP[14] == SymbolKind.FIELD

    def test_namespace_mapping(self) -> None:
        assert _LSP_KIND_MAP[3] == SymbolKind.NAMESPACE

    def test_property_mapping(self) -> None:
        assert _LSP_KIND_MAP[7] == SymbolKind.PROPERTY

    def test_function_mapping(self) -> None:
        assert _LSP_KIND_MAP[12] == SymbolKind.METHOD


# ---------------------------------------------------------------------------
# _convert tests
# ---------------------------------------------------------------------------

def _make_adapter() -> JavaLSPAdapter:
    """Create adapter with a mock language server (no real LSP needed for _convert)."""
    return JavaLSPAdapter(MagicMock())


def _make_raw(
    name: str,
    kind: int,
    parent: dict | None = None,
    detail: str = "",
    start_line: int = 0,
    end_line: int = 0,
) -> dict:
    raw: dict = {
        "name": name,
        "kind": kind,
        "detail": detail,
        "location": {
            "range": {
                "start": {"line": start_line, "character": 0},
                "end": {"line": end_line, "character": 0},
            }
        },
    }
    if parent is not None:
        raw["parent"] = parent
    return raw


class TestConvert:
    def test_convert_class_symbol(self) -> None:
        parent = {"name": "com.graphhopper.routing", "kind": 3}
        raw = _make_raw("Router", 5, parent=parent, start_line=10, end_line=100)
        sym = _make_adapter()._convert(raw, "/proj/Router.java", parent_full_name=None)

        assert sym.full_name == "com.graphhopper.routing.Router"
        assert sym.kind == SymbolKind.CLASS
        assert sym.name == "Router"
        assert sym.line == 10
        assert sym.end_line == 100

    def test_convert_method_symbol(self) -> None:
        grandparent = {"name": "com.graphhopper.routing", "kind": 3}
        parent = {"name": "Router", "kind": 5, "parent": grandparent}
        raw = _make_raw("route", 6, parent=parent, detail="public GHResponse route(GHRequest req)")
        sym = _make_adapter()._convert(raw, "/proj/Router.java", parent_full_name="com.graphhopper.routing.Router")

        assert sym.full_name == "com.graphhopper.routing.Router.route"
        assert sym.kind == SymbolKind.METHOD
        assert sym.signature == "public GHResponse route(GHRequest req)"

    def test_convert_constructor(self) -> None:
        parent = {"name": "Router", "kind": 5}
        raw = _make_raw("Router", 9, parent=parent)
        sym = _make_adapter()._convert(raw, "/proj/Router.java", parent_full_name="Router")

        assert sym.kind == SymbolKind.METHOD

    def test_convert_interface(self) -> None:
        parent = {"name": "com.graphhopper.routing", "kind": 3}
        raw = _make_raw("RoutingAlgorithm", 11, parent=parent)
        sym = _make_adapter()._convert(raw, "/proj/RoutingAlgorithm.java", parent_full_name=None)

        assert sym.kind == SymbolKind.INTERFACE
        assert sym.full_name == "com.graphhopper.routing.RoutingAlgorithm"

    def test_convert_constant(self) -> None:
        """D-23: kind 14 (constant) maps to FIELD."""
        parent = {"name": "Router", "kind": 5}
        raw = _make_raw("MAX_RETRIES", 14, parent=parent, detail="public static final int")
        sym = _make_adapter()._convert(raw, "/proj/Router.java", parent_full_name="Router")

        assert sym.kind == SymbolKind.FIELD
        assert sym.is_static is True

    def test_convert_abstract_method(self) -> None:
        parent = {"name": "Animal", "kind": 5}
        raw = _make_raw("speak", 6, parent=parent, detail="public abstract void speak()")
        sym = _make_adapter()._convert(raw, "/proj/Animal.java", parent_full_name="Animal")

        assert sym.is_abstract is True

    def test_convert_static_method(self) -> None:
        parent = {"name": "Util", "kind": 5}
        raw = _make_raw("helper", 6, parent=parent, detail="public static void helper()")
        sym = _make_adapter()._convert(raw, "/proj/Util.java", parent_full_name="Util")

        assert sym.is_static is True

    def test_convert_unmapped_kind_defaults_to_class(self) -> None:
        raw = _make_raw("Unknown", 999)
        sym = _make_adapter()._convert(raw, "/proj/Foo.java", parent_full_name=None)

        assert sym.kind == SymbolKind.CLASS

    def test_convert_fallback_when_no_container(self) -> None:
        """D-05: If build_full_name returns just the name, use parent_full_name fallback."""
        raw = _make_raw("speak", 6)  # No parent in raw dict
        sym = _make_adapter()._convert(raw, "/proj/Animal.java", parent_full_name="com.test.Animal")

        assert sym.full_name == "com.test.Animal.speak"


# ---------------------------------------------------------------------------
# get_workspace_files tests
# ---------------------------------------------------------------------------

class TestGetWorkspaceFiles:
    def test_excludes_build_dirs(self, tmp_path: Path) -> None:
        """D-03: target, build, .gradle and other build dirs are excluded."""
        # Create included files
        src_dir = tmp_path / "src" / "main" / "java"
        src_dir.mkdir(parents=True)
        (src_dir / "Main.java").touch()

        # Create excluded files
        for excluded in ["target", "build", ".gradle", ".idea", "bin", ".settings", ".mvn"]:
            d = tmp_path / excluded / "sub"
            d.mkdir(parents=True)
            (d / "Excluded.java").touch()

        adapter = _make_adapter()
        files = adapter.get_workspace_files(str(tmp_path))

        assert len(files) == 1
        assert files[0].endswith("Main.java")

    def test_returns_only_java_files(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "Main.java").touch()
        (src / "readme.md").touch()
        (src / "pom.xml").touch()

        adapter = _make_adapter()
        files = adapter.get_workspace_files(str(tmp_path))

        assert len(files) == 1
        assert files[0].endswith("Main.java")

    def test_returns_absolute_paths(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "App.java").touch()

        adapter = _make_adapter()
        files = adapter.get_workspace_files(str(tmp_path))

        assert len(files) == 1
        assert os.path.isabs(files[0])


# ---------------------------------------------------------------------------
# get_document_symbols integration
# ---------------------------------------------------------------------------

class TestGetDocumentSymbols:
    def test_returns_symbols_from_root(self) -> None:
        class_raw = _make_raw("Router", 5, start_line=5, end_line=50)
        class_raw["children"] = []

        mock_result = MagicMock()
        mock_result.root_symbols = [class_raw]
        mock_ls = MagicMock()
        mock_ls.request_document_symbols.return_value = mock_result

        adapter = JavaLSPAdapter(mock_ls)
        symbols = adapter.get_document_symbols("/proj/Router.java")

        assert len(symbols) == 1
        assert symbols[0].name == "Router"

    def test_returns_empty_on_none(self) -> None:
        mock_ls = MagicMock()
        mock_ls.request_document_symbols.return_value = None

        adapter = JavaLSPAdapter(mock_ls)
        symbols = adapter.get_document_symbols("/proj/Missing.java")

        assert symbols == []

    def test_traverse_sets_parent_full_name(self) -> None:
        method_raw = _make_raw("route", 6, detail="void route()")
        method_raw["children"] = []
        parent = {"name": "com.test", "kind": 3}
        class_raw = _make_raw("Router", 5, parent=parent)
        class_raw["children"] = [method_raw]

        mock_result = MagicMock()
        mock_result.root_symbols = [class_raw]
        mock_ls = MagicMock()
        mock_ls.request_document_symbols.return_value = mock_result

        adapter = JavaLSPAdapter(mock_ls)
        symbols = adapter.get_document_symbols("/proj/Router.java")

        method = next(s for s in symbols if s.name == "route")
        assert method.parent_full_name == "com.test.Router"

    def test_returns_empty_on_exception(self) -> None:
        mock_ls = MagicMock()
        mock_ls.request_document_symbols.side_effect = RuntimeError("LSP failed")

        adapter = JavaLSPAdapter(mock_ls)
        symbols = adapter.get_document_symbols("/proj/Broken.java")

        assert symbols == []


# ---------------------------------------------------------------------------
# Stub methods
# ---------------------------------------------------------------------------

class TestStubs:
    def test_find_method_calls_returns_empty(self) -> None:
        adapter = _make_adapter()
        sym = IndexSymbol(
            name="route", full_name="com.test.Router.route",
            kind=SymbolKind.METHOD, file_path="/proj/Router.java", line=10,
        )
        assert adapter.find_method_calls(sym) == []

    def test_find_overridden_method_returns_none(self) -> None:
        adapter = _make_adapter()
        sym = IndexSymbol(
            name="speak", full_name="com.test.Dog.speak",
            kind=SymbolKind.METHOD, file_path="/proj/Dog.java", line=5,
        )
        assert adapter.find_overridden_method(sym) is None
