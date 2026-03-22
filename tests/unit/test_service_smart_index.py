from __future__ import annotations

from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from synapse.indexer.sync import SyncResult
from synapse.service import SynapseService


@pytest.fixture
def conn():
    return MagicMock()


@pytest.fixture
def registry():
    reg = MagicMock()
    plugin = MagicMock()
    plugin.name = "csharp"
    plugin.file_extensions = {".cs"}
    lsp = MagicMock()
    plugin.create_lsp_adapter.return_value = lsp
    reg.detect.return_value = [plugin]
    return reg


@pytest.fixture
def svc(conn, registry):
    return SynapseService(conn, registry=registry)


@patch("synapse.service.is_git_repo", return_value=False)
def test_no_repo_node_runs_full_index(mock_git, svc, conn):
    conn.query.return_value = []  # no Repository rows
    with patch.object(svc, "index_project") as mock_idx:
        result = svc.smart_index("/project", "csharp")
    assert result == "full-index"
    mock_idx.assert_called_once()


@patch("synapse.service.set_last_indexed_commit")
@patch("synapse.service.rev_parse_head", return_value="abc123")
@patch("synapse.service.is_git_repo", return_value=True)
def test_full_index_on_git_project_stores_sha(mock_git, mock_rev, mock_set, svc, conn):
    conn.query.return_value = []  # no Repository rows
    with patch.object(svc, "index_project"):
        result = svc.smart_index("/project", "csharp")
    assert result == "full-index"
    mock_set.assert_called_once_with(conn, "/project", "abc123")


@patch("synapse.service._git_sync_project")
@patch("synapse.service.get_last_indexed_commit", return_value="stored_sha")
@patch("synapse.service.is_git_repo", return_value=True)
def test_git_repo_with_stored_sha_runs_git_sync(mock_git, mock_get_sha, mock_sync, svc, conn, registry):
    conn.query.return_value = [["some/path"]]  # has Repository
    mock_sync.return_value = SyncResult(updated=2, deleted=0, unchanged=0)
    result = svc.smart_index("/project", "csharp")
    assert result == "git-sync"
    mock_sync.assert_called_once()
    # Verify stored_sha was passed
    call_kwargs = mock_sync.call_args
    assert call_kwargs.kwargs.get("stored_sha") == "stored_sha" or call_kwargs[1].get("stored_sha") == "stored_sha"


@patch("synapse.service._git_sync_project")
@patch("synapse.service.get_last_indexed_commit", return_value=None)
@patch("synapse.service.is_git_repo", return_value=True)
def test_git_repo_no_stored_sha_uses_empty_tree(mock_git, mock_get_sha, mock_sync, svc, conn, registry):
    conn.query.return_value = [["some/path"]]  # has Repository
    mock_sync.return_value = SyncResult(updated=5, deleted=0, unchanged=0)
    result = svc.smart_index("/project", "csharp")
    assert result == "git-sync"
    call_kwargs = mock_sync.call_args
    # Should use the empty tree SHA
    effective_sha = call_kwargs.kwargs.get("stored_sha") or call_kwargs[1].get("stored_sha")
    assert effective_sha == "4b825dc642cb6eb9a060e54bf899d69f82cf7180"


@patch("synapse.service.get_last_indexed_commit", return_value=None)
@patch("synapse.service.is_git_repo", return_value=False)
def test_non_git_repo_runs_mtime_sync(mock_git, mock_get_sha, svc, conn):
    conn.query.return_value = [["some/path"]]  # has Repository
    with patch.object(svc, "sync_project") as mock_sync:
        result = svc.smart_index("/project", "csharp")
    assert result == "mtime-sync"
    mock_sync.assert_called_once_with("/project")


@patch("synapse.service._git_sync_project")
@patch("synapse.service.get_last_indexed_commit", return_value="sha1")
@patch("synapse.service.is_git_repo", return_value=True)
def test_git_sync_shuts_down_lsp(mock_git, mock_get_sha, mock_sync, svc, conn, registry):
    conn.query.return_value = [["some/path"]]
    mock_sync.return_value = SyncResult(updated=0, deleted=0, unchanged=0)
    svc.smart_index("/project", "csharp")
    plugin = registry.detect.return_value[0]
    lsp = plugin.create_lsp_adapter.return_value
    lsp.shutdown.assert_called_once()
