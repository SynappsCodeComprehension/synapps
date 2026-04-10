from __future__ import annotations

import inspect
from unittest.mock import MagicMock, patch

import pytest

from synapps.service import SynappsService
from conftest import _MockNode


def _node(labels: list[str], props: dict) -> _MockNode:
    return _MockNode(labels, props)


@pytest.fixture(autouse=True)
def bypass_resolve(monkeypatch):
    monkeypatch.setattr("synapps.service.resolve_full_name", lambda conn, name: name)


def _service() -> SynappsService:
    conn = MagicMock()
    return SynappsService(conn=conn)


def test_get_context_for_no_scope_parameter():
    """get_context_for must not have a scope parameter on SynappsService."""
    sig = inspect.signature(SynappsService.get_context_for)
    assert "scope" not in sig.parameters
    assert "members_only" in sig.parameters


def test_get_context_for_members_only_returns_signatures(tmp_path):
    """members_only=True on a Class returns member signatures without source bodies or callees."""
    source_file = tmp_path / "MyClass.cs"
    source_file.write_text(
        "namespace Ns {\n"
        "    class MyClass {\n"
        "        public MyClass() {}\n"
        "        public void DoWork() {}\n"
        "    }\n"
        "}\n"
    )

    svc = _service()
    symbol = _node(["Class"], {"full_name": "Ns.MyClass", "name": "MyClass", "kind": "class"})
    ctor_node = _node(["Method"], {"full_name": "Ns.MyClass.MyClass", "name": "MyClass",
                                   "line": 3, "end_line": 3})

    with patch.multiple(
        "synapps.service.context",
        get_symbol=MagicMock(return_value=symbol),
        get_constructor=MagicMock(return_value=ctor_node),
        get_symbol_source_info=MagicMock(return_value={
            "file_path": str(source_file), "line": 3, "end_line": 3,
        }),
        get_members_overview=MagicMock(return_value=[
            {"full_name": "Ns.MyClass.MyClass", "name": "MyClass", "signature": "MyClass()"},
            {"full_name": "Ns.MyClass.DoWork", "name": "DoWork", "signature": "void DoWork()"},
        ]),
        get_implemented_interfaces=MagicMock(return_value=[]),
        get_summary=MagicMock(return_value=None),
    ):
        result = svc.get_context_for("Ns.MyClass", members_only=True)

    assert result is not None
    assert isinstance(result, str)
    assert "## Members" in result
    assert "DoWork" in result
    assert "## Called Methods" not in result
    assert "## Parameter & Return Types" not in result
    assert "## Containing Type:" not in result


def test_get_context_for_members_only_on_interface():
    """members_only=True works on Interface nodes without error."""
    svc = _service()
    symbol = _node(["Interface"], {"full_name": "Ns.IFoo", "name": "IFoo", "kind": "interface"})

    with patch.multiple(
        "synapps.service.context",
        get_symbol=MagicMock(return_value=symbol),
        get_constructor=MagicMock(return_value=None),
        get_members_overview=MagicMock(return_value=[
            {"full_name": "Ns.IFoo.DoWork", "name": "DoWork", "signature": "void DoWork()"},
        ]),
        get_implemented_interfaces=MagicMock(return_value=[]),
        get_summary=MagicMock(return_value=None),
    ):
        result = svc.get_context_for("Ns.IFoo", members_only=True)

    assert result is not None
    assert isinstance(result, str)
    assert "## Members" in result
    assert "DoWork" in result


def test_get_context_for_members_only_on_method_returns_error():
    """members_only=True on a Method returns an error message (not an exception)."""
    svc = _service()
    symbol = _node(["Method"], {"full_name": "Ns.Foo.Bar", "name": "Bar", "kind": "method"})

    with patch("synapps.service.context.get_symbol", return_value=symbol):
        result = svc.get_context_for("Ns.Foo.Bar", members_only=True)

    assert result is not None
    assert isinstance(result, str)
    assert "members_only=True requires a type" in result
    assert "method" in result


def test_get_context_for_default_excludes_callers(tmp_path):
    """Default get_context_for does not include a Direct Callers section."""
    source_file = tmp_path / "Foo.cs"
    source_file.write_text("class Foo { void Bar() {} }\n")

    svc = _service()
    symbol = _node(["Method"], {"full_name": "Ns.Foo.Bar", "name": "Bar", "kind": "method"})

    with patch.multiple(
        "synapps.service.context",
        get_symbol=MagicMock(return_value=symbol),
        get_symbol_source_info=MagicMock(return_value={
            "file_path": str(source_file), "line": 1, "end_line": 0,
        }),
        get_containing_type=MagicMock(return_value=None),
        get_implemented_interfaces=MagicMock(return_value=[]),
        find_callees=MagicMock(return_value=[
            {"full_name": "Ns.Other.Call", "signature": "void Call()"},
        ]),
        query_find_dependencies=MagicMock(return_value=[]),
        get_summary=MagicMock(return_value=None),
    ):
        result = svc.get_context_for("Ns.Foo.Bar")

    assert result is not None
    assert "## Direct Callers" not in result
    assert "## Callers" not in result


def test_get_context_for_default_excludes_tests(tmp_path):
    """Default get_context_for does not include a Test Coverage section."""
    source_file = tmp_path / "Foo.cs"
    source_file.write_text("class Foo { void Bar() {} }\n")

    svc = _service()
    symbol = _node(["Method"], {"full_name": "Ns.Foo.Bar", "name": "Bar", "kind": "method"})

    with patch.multiple(
        "synapps.service.context",
        get_symbol=MagicMock(return_value=symbol),
        get_symbol_source_info=MagicMock(return_value={
            "file_path": str(source_file), "line": 1, "end_line": 0,
        }),
        get_containing_type=MagicMock(return_value=None),
        get_implemented_interfaces=MagicMock(return_value=[]),
        find_callees=MagicMock(return_value=[]),
        query_find_dependencies=MagicMock(return_value=[]),
        get_summary=MagicMock(return_value=None),
    ):
        result = svc.get_context_for("Ns.Foo.Bar")

    assert result is not None
    assert "## Test Coverage" not in result


def test_get_context_for_default_includes_callees(tmp_path):
    """Default get_context_for includes a Called Methods section when callees exist."""
    source_file = tmp_path / "Foo.cs"
    source_file.write_text("class Foo { void Bar() { Other(); } }\n")

    svc = _service()
    symbol = _node(["Method"], {"full_name": "Ns.Foo.Bar", "name": "Bar", "kind": "method"})

    with patch.multiple(
        "synapps.service.context",
        get_symbol=MagicMock(return_value=symbol),
        get_symbol_source_info=MagicMock(return_value={
            "file_path": str(source_file), "line": 1, "end_line": 0,
        }),
        get_containing_type=MagicMock(return_value=None),
        get_implemented_interfaces=MagicMock(return_value=[]),
        find_callees=MagicMock(return_value=[
            {"full_name": "Ns.Other.Call", "signature": "void Call()"},
        ]),
        query_find_dependencies=MagicMock(return_value=[]),
        get_summary=MagicMock(return_value=None),
    ):
        result = svc.get_context_for("Ns.Foo.Bar")

    assert result is not None
    assert "## Called Methods" in result
    assert "Ns.Other.Call" in result
