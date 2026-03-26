"""Unit tests verifying index_project iterates all detected language plugins."""
import pytest
from unittest.mock import MagicMock, patch, call

from synapse.service import SynapseService


def _make_plugin(name: str) -> MagicMock:
    plugin = MagicMock()
    plugin.name = name
    plugin.file_extensions = frozenset({f".{name[:2]}"})
    plugin.create_lsp_adapter.return_value = MagicMock()
    return plugin


def _make_registry(plugins: list) -> MagicMock:
    registry = MagicMock()
    registry.detect.return_value = plugins
    registry.detect_with_files.return_value = [(p, []) for p in plugins]
    return registry


def test_index_project_calls_indexer_for_each_plugin() -> None:
    """When registry detects two plugins, Indexer is instantiated and called for each."""
    plugin_a = _make_plugin("csharp")
    plugin_b = _make_plugin("python")
    registry = _make_registry([plugin_a, plugin_b])
    conn = MagicMock()
    svc = SynapseService(conn, registry=registry)

    mock_indexer = MagicMock()
    with patch("synapse.service.indexing.Indexer", return_value=mock_indexer) as MockIndexer:
        svc.index_project("/some/path")

    assert MockIndexer.call_count == 2
    assert mock_indexer.index_project.call_count == 2


def test_index_project_single_plugin_works() -> None:
    """Single detected plugin still calls Indexer exactly once (backward compat)."""
    plugin = _make_plugin("csharp")
    registry = _make_registry([plugin])
    conn = MagicMock()
    svc = SynapseService(conn, registry=registry)

    mock_indexer = MagicMock()
    with patch("synapse.service.indexing.Indexer", return_value=mock_indexer) as MockIndexer:
        svc.index_project("/some/path")

    assert MockIndexer.call_count == 1
    assert mock_indexer.index_project.call_count == 1


def test_index_project_no_plugins_raises_value_error() -> None:
    """When no plugins are detected, index_project raises ValueError (existing behavior)."""
    registry = _make_registry([])
    conn = MagicMock()
    svc = SynapseService(conn, registry=registry)

    with pytest.raises(ValueError, match="No language plugin found"):
        svc.index_project("/some/path")


def test_index_project_on_progress_called_per_plugin() -> None:
    """on_progress callback is invoked for each detected plugin."""
    plugin_a = _make_plugin("csharp")
    plugin_b = _make_plugin("python")
    registry = _make_registry([plugin_a, plugin_b])
    conn = MagicMock()
    svc = SynapseService(conn, registry=registry)
    progress_calls: list[str] = []

    mock_indexer = MagicMock()
    with patch("synapse.service.indexing.Indexer", return_value=mock_indexer):
        svc.index_project("/some/path", on_progress=progress_calls.append)

    # Each plugin should have triggered at least one progress message
    assert len(progress_calls) >= 2
