from unittest.mock import MagicMock, patch
import os

import pytest

from synapse.service import SynapseService
from synapse.indexer.sync import SyncResult


@pytest.fixture(autouse=True)
def bypass_resolve(monkeypatch):
    monkeypatch.setattr("synapse.service.resolve_full_name", lambda conn, name: name)


def test_sync_project_uses_plugin_detection(tmp_path):
    """sync_project uses registry.detect_with_files() and creates LSP + Indexer per plugin."""
    (tmp_path / "a.cs").write_text("class A {}")

    conn = MagicMock()
    mock_plugin = MagicMock()
    mock_plugin.name = "csharp"
    mock_plugin.file_extensions = frozenset({".cs"})
    mock_lsp = MagicMock()
    mock_lsp.get_workspace_files.return_value = [str(tmp_path / "a.cs")]
    mock_plugin.create_lsp_adapter.return_value = mock_lsp

    registry = MagicMock()
    plugin_files = [(mock_plugin, [str(tmp_path / "a.cs")])]
    registry.detect_with_files.return_value = plugin_files

    fake_result = SyncResult(updated=1, deleted=0, unchanged=0)

    with patch("synapse.service.indexing._sync_project", return_value=fake_result) as mock_sync:
        with patch("synapse.service.indexing.Indexer") as mock_indexer_cls:
            svc = SynapseService(conn, registry=registry)
            result = svc.sync_project(str(tmp_path))

    registry.detect_with_files.assert_called_once_with(str(tmp_path))
    mock_plugin.create_lsp_adapter.assert_called_once_with(str(tmp_path))
    mock_lsp.shutdown.assert_called_once()
    assert result.updated == 1


def test_sync_project_uses_predetected_files(tmp_path):
    """sync_project uses pre-detected files when plugin_files is provided."""
    cs_file = tmp_path / "a.cs"
    cs_file.write_text("class A {}")

    conn = MagicMock()
    mock_plugin = MagicMock()
    mock_plugin.name = "csharp"
    mock_plugin.file_extensions = frozenset({".cs"})
    mock_lsp = MagicMock()
    mock_plugin.create_lsp_adapter.return_value = mock_lsp

    registry = MagicMock()
    plugin_files = [(mock_plugin, [str(cs_file)])]

    fake_result = SyncResult(updated=1, deleted=0, unchanged=0)

    with patch("synapse.service.indexing._sync_project", return_value=fake_result) as mock_sync:
        with patch("synapse.service.indexing.Indexer"):
            svc = SynapseService(conn, registry=registry)
            result = svc.sync_project(str(tmp_path), plugin_files=plugin_files)

    # detect_with_files should NOT be called when plugin_files is provided
    registry.detect_with_files.assert_not_called()
    # lsp.get_workspace_files should NOT be called when files are pre-detected
    mock_lsp.get_workspace_files.assert_not_called()
    mock_lsp.shutdown.assert_called_once()
    assert result.updated == 1


def test_sync_project_no_plugins_raises(tmp_path):
    conn = MagicMock()
    registry = MagicMock()
    registry.detect_with_files.return_value = []
    svc = SynapseService(conn, registry=registry)

    with pytest.raises(ValueError, match="No language plugin"):
        svc.sync_project(str(tmp_path))
