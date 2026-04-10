from __future__ import annotations

from unittest.mock import MagicMock, patch

from synapps.service.context import ContextBuilder


def test_get_context_for_returns_none_for_missing_symbol():
    """get_context_for returns None when the symbol is not found in the graph."""
    conn = MagicMock()
    conn.query.return_value = []  # get_symbol returns None when rows is empty

    builder = ContextBuilder(conn)
    result = builder.get_context_for("Nonexistent.Symbol")

    assert result is None


def test_get_context_for_members_only_error_for_method():
    """members_only=True with a Method symbol returns an error string."""
    conn = MagicMock()
    # get_symbol returns rows[0][0]; simulate a Method node
    method_node = {"full_name": "Ns.Cls.method", "_labels": ["Method"], "kind": "method"}
    conn.query.return_value = [[method_node]]

    builder = ContextBuilder(conn)
    result = builder.get_context_for("Ns.Cls.method", members_only=True)

    assert isinstance(result, str)
    assert "members_only=True requires a type" in result


def test_context_builder_has_no_service_reference():
    """ContextBuilder no longer accepts a service parameter."""
    import inspect
    sig = inspect.signature(ContextBuilder.__init__)
    assert "service" not in sig.parameters
