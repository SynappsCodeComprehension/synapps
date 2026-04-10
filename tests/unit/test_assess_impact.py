from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest

from synapps.service import SynappsService
from conftest import _MockNode


@pytest.fixture(autouse=True)
def bypass_resolve(monkeypatch):
    """Make resolve_full_name return the name unchanged for all service tests."""
    monkeypatch.setattr("synapps.service.resolve_full_name", lambda conn, name: name)


def _service() -> SynappsService:
    conn = MagicMock()
    return SynappsService(conn=conn)


def _caller_entry(i: int) -> dict:
    """Build a caller entry with a MockNode and a single call site."""
    return {
        "caller": _MockNode(["Method"], {"full_name": f"Ns.Caller{i}", "file_path": f"/f{i}.py"}),
        "call_sites": [[10]],
    }


def _test_entry_with_line(i: int) -> dict:
    """Build a test entry with a line number (find_tests_for format)."""
    return {"full_name": f"test_func_{i}", "file_path": f"/tests/test_file_{i}.py", "line": 10 + i}


def _test_entry_no_line(i: int) -> dict:
    """Build a test entry without a line number (find_test_coverage format)."""
    return {"full_name": f"test_bar_{i}", "file_path": f"/tests/test_bar_{i}.py"}


def _empty_contract() -> dict:
    return {"method": "Ns.MyClass.DoThing", "interface": None, "contract_method": None, "sibling_implementations": []}


def _full_contract() -> dict:
    return {
        "method": "Ns.MyClass.DoThing",
        "interface": "Ns.IService",
        "contract_method": "Ns.IService.DoThing",
        "sibling_implementations": [{"class_name": "OtherImpl", "file_path": "/other.cs"}],
    }


def test_direct_callers_truncated() -> None:
    """Direct callers are capped at 15 and header shows (showing 15 of 20)."""
    svc = _service()
    callers = [_caller_entry(i) for i in range(20)]
    with patch.multiple(
        "synapps.service.context",
        find_callers_with_sites=lambda conn, fn: callers,
        find_test_coverage=lambda conn, fn: [],
        get_served_endpoint=lambda conn, fn: None,
        find_http_callers=lambda conn, fn: [],
    ):
        with patch("synapps.service.context.find_interface_contract", return_value=_empty_contract()):
            with patch("synapps.service.context.find_tests_for", return_value=[]):
                result = svc.assess_impact("Ns.MyClass.DoThing")
    assert "showing 15 of 20" in result
    # Count how many caller lines appear
    direct_section_lines = [line for line in result.split("\n") if "Ns.Caller" in line and "- `" in line]
    assert len(direct_section_lines) == 15


def test_direct_callers_no_truncation() -> None:
    """When count == limit or below, no (showing N of M) appears in the Direct Callers header."""
    svc = _service()
    callers = [_caller_entry(i) for i in range(10)]
    with patch.multiple(
        "synapps.service.context",
        find_callers_with_sites=lambda conn, fn: callers,
        find_test_coverage=lambda conn, fn: [],
        get_served_endpoint=lambda conn, fn: None,
        find_http_callers=lambda conn, fn: [],
    ):
        with patch("synapps.service.context.find_interface_contract", return_value=_empty_contract()):
            with patch("synapps.service.context.find_tests_for", return_value=[]):
                result = svc.assess_impact("Ns.MyClass.DoThing")
    # Header should be plain "## Direct Callers" without count
    assert "## Direct Callers\n" in result or "## Direct Callers " not in result.split("## Direct Callers")[1][:20]
    # No truncation count in Direct Callers section
    direct_section = result.split("## Direct Callers")[1].split("##")[0]
    assert "(showing" not in direct_section.split("\n")[0]


def test_transitive_callers_truncated() -> None:
    """Transitive callers are capped at 10 and direct callers don't appear in transitive section."""
    svc = _service()
    direct_callers = [_caller_entry(i) for i in range(3)]
    direct_full_names = {f"Ns.Caller{i}" for i in range(3)}

    # Transitive query returns 15 entries (excluding the 3 direct callers)
    transitive_nodes = [
        _MockNode(["Method"], {"full_name": f"Ns.Transitive{i}", "file_path": f"/t{i}.py"})
        for i in range(15)
    ]

    def mock_conn_query(cypher, *args, **kwargs):
        # Return transitive callers when queried
        return [{"transitive": node} for node in transitive_nodes]

    svc._conn.query.side_effect = mock_conn_query

    with patch.multiple(
        "synapps.service.context",
        find_callers_with_sites=lambda conn, fn: direct_callers,
        find_test_coverage=lambda conn, fn: [],
        get_served_endpoint=lambda conn, fn: None,
        find_http_callers=lambda conn, fn: [],
    ):
        with patch("synapps.service.context.find_interface_contract", return_value=_empty_contract()):
            with patch("synapps.service.context.find_tests_for", return_value=[]):
                result = svc.assess_impact("Ns.MyClass.DoThing")

    assert "showing 10 of 15" in result
    # Direct callers should NOT appear in the Transitive Callers section
    transitive_section = result.split("## Transitive Callers")[1].split("##")[0]
    for direct_name in direct_full_names:
        assert direct_name not in transitive_section


def test_test_coverage_truncated() -> None:
    """Test coverage is capped at 5 and header shows (showing 5 of 8)."""
    svc = _service()
    tests = [_test_entry_with_line(i) for i in range(8)]
    with patch.multiple(
        "synapps.service.context",
        find_callers_with_sites=lambda conn, fn: [],
        find_test_coverage=lambda conn, fn: [],
        get_served_endpoint=lambda conn, fn: None,
        find_http_callers=lambda conn, fn: [],
    ):
        with patch("synapps.service.context.find_interface_contract", return_value=_empty_contract()):
            with patch("synapps.service.context.find_tests_for", return_value=tests):
                result = svc.assess_impact("Ns.MyClass.DoThing")

    assert "showing 5 of 8" in result
    # Check test entries use file:line format
    test_section = result.split("## Test Coverage")[1].split("##")[0]
    # At least one entry should have a colon-line format
    assert any(":10" in line or ":11" in line for line in test_section.split("\n") if "test_func" in line)


def test_test_coverage_fallback_no_line() -> None:
    """When find_tests_for returns empty, falls back to find_test_coverage (no line in output)."""
    svc = _service()
    coverage_entries = [_test_entry_no_line(i) for i in range(2)]
    with patch.multiple(
        "synapps.service.context",
        find_callers_with_sites=lambda conn, fn: [],
        find_test_coverage=lambda conn, fn: coverage_entries,
        get_served_endpoint=lambda conn, fn: None,
        find_http_callers=lambda conn, fn: [],
    ):
        with patch("synapps.service.context.find_interface_contract", return_value=_empty_contract()):
            with patch("synapps.service.context.find_tests_for", return_value=[]):
                result = svc.assess_impact("Ns.MyClass.DoThing")

    test_section = result.split("## Test Coverage")[1].split("##")[0]
    # Should have test_bar entries
    assert "test_bar_0" in test_section
    # Should NOT have colon-line since find_test_coverage has no line number
    for line in test_section.split("\n"):
        if "test_bar" in line:
            # Line format should be `test_bar_0 — /tests/test_bar_0.py` (no :line)
            assert ":1" not in line


def test_interface_contract_present() -> None:
    """Interface contract section shows interface name and contract method."""
    svc = _service()
    with patch.multiple(
        "synapps.service.context",
        find_callers_with_sites=lambda conn, fn: [],
        find_test_coverage=lambda conn, fn: [],
        get_served_endpoint=lambda conn, fn: None,
        find_http_callers=lambda conn, fn: [],
    ):
        with patch("synapps.service.context.find_interface_contract", return_value=_full_contract()):
            with patch("synapps.service.context.find_tests_for", return_value=[]):
                result = svc.assess_impact("Ns.MyClass.DoThing")

    assert "## Interface Contract" in result
    assert "Ns.IService" in result
    assert "Ns.IService.DoThing" in result


def test_interface_contract_absent() -> None:
    """When no interface contract exists, section shows 'No interface contract found'."""
    svc = _service()
    with patch.multiple(
        "synapps.service.context",
        find_callers_with_sites=lambda conn, fn: [],
        find_test_coverage=lambda conn, fn: [],
        get_served_endpoint=lambda conn, fn: None,
        find_http_callers=lambda conn, fn: [],
    ):
        with patch("synapps.service.context.find_interface_contract", return_value=_empty_contract()):
            with patch("synapps.service.context.find_tests_for", return_value=[]):
                result = svc.assess_impact("Ns.MyClass.DoThing")

    assert "No interface contract found" in result


def test_http_section_present() -> None:
    """HTTP endpoint is shown and HTTP callers are capped at 5 with (showing 5 of 7)."""
    svc = _service()
    http_callers = [
        {"full_name": f"Ns.HttpCaller{i}", "file_path": f"/h{i}.py", "route": "/api/foo"}
        for i in range(7)
    ]
    with patch.multiple(
        "synapps.service.context",
        find_callers_with_sites=lambda conn, fn: [],
        find_test_coverage=lambda conn, fn: [],
        get_served_endpoint=lambda conn, fn: {"http_method": "GET", "route": "/api/foo"},
        find_http_callers=lambda conn, fn: http_callers,
    ):
        with patch("synapps.service.context.find_interface_contract", return_value=_empty_contract()):
            with patch("synapps.service.context.find_tests_for", return_value=[]):
                result = svc.assess_impact("Ns.MyClass.DoThing")

    assert "GET /api/foo" in result
    assert "showing 5 of 7" in result


def test_http_section_absent() -> None:
    """When no HTTP endpoint exists, section shows 'No HTTP endpoint found'."""
    svc = _service()
    with patch.multiple(
        "synapps.service.context",
        find_callers_with_sites=lambda conn, fn: [],
        find_test_coverage=lambda conn, fn: [],
        get_served_endpoint=lambda conn, fn: None,
        find_http_callers=lambda conn, fn: [],
    ):
        with patch("synapps.service.context.find_interface_contract", return_value=_empty_contract()):
            with patch("synapps.service.context.find_tests_for", return_value=[]):
                result = svc.assess_impact("Ns.MyClass.DoThing")

    assert "No HTTP endpoint found" in result


def test_empty_sections() -> None:
    """All five section headers always appear, even when all data is empty."""
    svc = _service()
    with patch.multiple(
        "synapps.service.context",
        find_callers_with_sites=lambda conn, fn: [],
        find_test_coverage=lambda conn, fn: [],
        get_served_endpoint=lambda conn, fn: None,
        find_http_callers=lambda conn, fn: [],
    ):
        with patch("synapps.service.context.find_interface_contract", return_value=_empty_contract()):
            with patch("synapps.service.context.find_tests_for", return_value=[]):
                result = svc.assess_impact("Ns.MyClass.DoThing")

    assert "## Direct Callers" in result
    assert "## Transitive Callers" in result
    assert "## Test Coverage" in result
    assert "## Interface Contract" in result
    assert "## HTTP Endpoint" in result

    assert "No direct callers found" in result
    assert "No transitive callers found" in result
    assert "No test coverage found" in result
    assert "No interface contract found" in result
    assert "No HTTP endpoint found" in result


def test_excludes_source_and_callees() -> None:
    """assess_impact output must not contain source code or callees sections."""
    svc = _service()
    with patch.multiple(
        "synapps.service.context",
        find_callers_with_sites=lambda conn, fn: [],
        find_test_coverage=lambda conn, fn: [],
        get_served_endpoint=lambda conn, fn: None,
        find_http_callers=lambda conn, fn: [],
        get_symbol_source_info=MagicMock(return_value=None),
        find_callees=MagicMock(return_value=[]),
    ) as mocks:
        with patch("synapps.service.context.find_interface_contract", return_value=_empty_contract()):
            with patch("synapps.service.context.find_tests_for", return_value=[]):
                result = svc.assess_impact("Ns.MyClass.DoThing")

    assert "## Source" not in result
    assert "## Callees" not in result
    assert "## Direct Callees" not in result
    # Verify the graph functions for source/callees were NOT called
    mocks["get_symbol_source_info"].assert_not_called()
    mocks["find_callees"].assert_not_called()


def test_service_delegates_to_context() -> None:
    """SynappsService.assess_impact delegates to ContextBuilder.assess_impact."""
    svc = _service()
    svc._context.assess_impact = MagicMock(return_value="mocked result")

    result = svc.assess_impact("Ns.MyClass.DoThing")

    svc._context.assess_impact.assert_called_once_with("Ns.MyClass.DoThing")
    assert result == "mocked result"
