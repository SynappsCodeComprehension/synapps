"""
CLI command integration tests against the Java fixture (SynapseJavaTest).

Requires Memgraph on localhost:7687 and Eclipse JDT LS (Java JDK 11+).
Run with: pytest tests/integration/test_cli_commands_java.py -v -m integration
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from synapse.cli.app import app
from synapse.service import SynapseService
from tests.integration.conftest import JAVA_FIXTURE_PATH

runner = CliRunner()


def _invoke(service: SynapseService, args: list[str]):
    """Patch _get_service so CLI commands use the Java test-scoped fixture service."""
    with patch("synapse.cli.app._get_service", return_value=service):
        return runner.invoke(app, args)


# ---------------------------------------------------------------------------
# Project-level commands
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.timeout(10)
def test_status(java_service: SynapseService) -> None:
    """status command returns exit code 0 for the Java fixture."""
    result = _invoke(java_service, ["status"])
    assert result.exit_code == 0


@pytest.mark.integration
@pytest.mark.timeout(10)
def test_query(java_service: SynapseService) -> None:
    """query command executes Cypher against Java-indexed graph."""
    result = _invoke(java_service, [
        "query",
        "MATCH (n:Class {language: 'java'}) RETURN n.name LIMIT 5",
    ])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Symbol query commands
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.timeout(10)
def test_symbol(java_service: SynapseService) -> None:
    """symbol command returns info for a Java interface."""
    result = _invoke(java_service, ["symbol", "com.synapsetest.IAnimal"])
    assert result.exit_code == 0
    assert "IAnimal" in result.output


@pytest.mark.integration
@pytest.mark.timeout(10)
def test_source(java_service: SynapseService) -> None:
    """source command returns exit code 0 for a Java class."""
    result = _invoke(java_service, ["source", "com.synapsetest.Dog"])
    assert result.exit_code == 0


@pytest.mark.integration
@pytest.mark.timeout(10)
def test_search(java_service: SynapseService) -> None:
    """search command returns matching symbols from Java fixture."""
    result = _invoke(java_service, ["search", "Animal"])
    assert result.exit_code == 0
    assert "Animal" in result.output


@pytest.mark.integration
@pytest.mark.timeout(10)
def test_search_language_filter(java_service: SynapseService) -> None:
    """search with --language java filters to only Java symbols."""
    result = _invoke(java_service, ["search", "Animal", "--language", "java"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Relationship commands
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.timeout(10)
def test_hierarchy(java_service: SynapseService) -> None:
    """hierarchy command returns parent chain for Dog (Animal ancestor)."""
    result = _invoke(java_service, ["hierarchy", "com.synapsetest.Dog"])
    assert result.exit_code == 0
    assert "Animal" in result.output


@pytest.mark.integration
@pytest.mark.timeout(10)
def test_implementations(java_service: SynapseService) -> None:
    """implementations command works for Java interfaces."""
    result = _invoke(java_service, [
        "implementations",
        "com.synapsetest.IAnimal",
    ])
    assert result.exit_code == 0
    assert "Animal" in result.output


@pytest.mark.integration
@pytest.mark.timeout(10)
def test_callers(java_service: SynapseService) -> None:
    """callers command returns exit code 0 (may have no results without JDT LS)."""
    result = _invoke(java_service, ["callers", "com.synapsetest.IAnimal.speak"])
    assert result.exit_code == 0


@pytest.mark.integration
@pytest.mark.timeout(10)
def test_callees(java_service: SynapseService) -> None:
    """callees command returns exit code 0 for a Java method."""
    result = _invoke(java_service, [
        "callees",
        "com.synapsetest.AnimalService.greet",
    ])
    assert result.exit_code == 0


@pytest.mark.integration
@pytest.mark.timeout(10)
def test_usages(java_service: SynapseService) -> None:
    """usages command returns exit code 0 for a Java interface."""
    result = _invoke(java_service, ["usages", "com.synapsetest.IAnimal"])
    assert result.exit_code == 0


@pytest.mark.integration
@pytest.mark.timeout(10)
def test_dependencies(java_service: SynapseService) -> None:
    """dependencies command returns exit code 0 for a Java class."""
    result = _invoke(java_service, [
        "dependencies",
        "com.synapsetest.AnimalService",
    ])
    assert result.exit_code == 0


@pytest.mark.integration
@pytest.mark.timeout(10)
def test_type_refs(java_service: SynapseService) -> None:
    """type-refs command returns exit code 0 (may be empty) for a Java interface."""
    result = _invoke(java_service, ["type-refs", "com.synapsetest.IAnimal"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Call chain / entry point / impact commands
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.timeout(10)
def test_context(java_service: SynapseService) -> None:
    """context command returns context text for a Java class."""
    result = _invoke(java_service, ["context", "com.synapsetest.Dog"])
    assert result.exit_code == 0
    assert "Dog" in result.output


@pytest.mark.integration
@pytest.mark.timeout(10)
def test_trace(java_service: SynapseService) -> None:
    """trace command returns exit code 0 (may find no paths without call edges)."""
    result = _invoke(java_service, [
        "trace",
        "com.synapsetest.AnimalService.greet",
        "com.synapsetest.IAnimal.speak",
    ])
    assert result.exit_code == 0


@pytest.mark.integration
@pytest.mark.timeout(10)
def test_impact(java_service: SynapseService) -> None:
    """impact command returns exit code 0 and prints analysis output."""
    result = _invoke(java_service, [
        "impact",
        "com.synapsetest.AnimalService.greet",
    ])
    assert result.exit_code == 0
    assert "direct" in result.output.lower() or "impact" in result.output.lower()


@pytest.mark.integration
@pytest.mark.timeout(10)
def test_contract(java_service: SynapseService) -> None:
    """contract command returns exit code 0 for a Java method."""
    result = _invoke(java_service, [
        "contract",
        "com.synapsetest.AnimalService.greet",
    ])
    assert result.exit_code == 0


@pytest.mark.integration
@pytest.mark.timeout(10)
def test_entry_points(java_service: SynapseService) -> None:
    """entry-points command returns exit code 0 for a Java method."""
    result = _invoke(java_service, [
        "entry-points",
        "com.synapsetest.AnimalService.greet",
    ])
    assert result.exit_code == 0


@pytest.mark.integration
@pytest.mark.timeout(10)
def test_call_depth(java_service: SynapseService) -> None:
    """call-depth command returns exit code 0 for a Java method."""
    result = _invoke(java_service, [
        "call-depth",
        "com.synapsetest.AnimalService.greet",
    ])
    assert result.exit_code == 0


@pytest.mark.integration
@pytest.mark.timeout(10)
def test_type_impact(java_service: SynapseService) -> None:
    """type-impact command returns exit code 0 and names the Java interface."""
    result = _invoke(java_service, [
        "type-impact",
        "com.synapsetest.IAnimal",
    ])
    assert result.exit_code == 0
    assert "IAnimal" in result.output


# ---------------------------------------------------------------------------
# Audit / summarize commands
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.timeout(10)
def test_audit(java_service: SynapseService) -> None:
    """audit command returns exit code 0 (empty violations for Java is OK)."""
    result = _invoke(java_service, ["audit", "layering_violations"])
    assert result.exit_code == 0
    assert "layering_violations" in result.output


# ---------------------------------------------------------------------------
# Summary subcommands
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.timeout(10)
def test_summary_set_get_list(java_service: SynapseService) -> None:
    """summary set/get/list subcommands round-trip correctly for Java symbols."""
    set_result = _invoke(java_service, [
        "summary", "set", "com.synapsetest.Cat", "A cat class in Java.",
    ])
    assert set_result.exit_code == 0

    get_result = _invoke(java_service, [
        "summary", "get", "com.synapsetest.Cat",
    ])
    assert get_result.exit_code == 0
    assert "A cat class in Java." in get_result.output

    list_result = _invoke(java_service, ["summary", "list"])
    assert list_result.exit_code == 0
    assert "Cat" in list_result.output
