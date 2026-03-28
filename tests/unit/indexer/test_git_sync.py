from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest

from synapps.indexer.git import GitDiff
from synapps.indexer.sync import git_sync_project, SyncResult


@pytest.fixture
def conn():
    return MagicMock()


@pytest.fixture
def indexer():
    m = MagicMock()
    m.reindex_file = MagicMock()
    m.delete_file = MagicMock()
    return m


@patch("synapps.indexer.sync.rev_parse_head", return_value="abc123")
@patch("synapps.indexer.sync.compute_git_diff")
def test_no_changes_returns_zero_sync_result(mock_diff, mock_rev, conn, indexer):
    mock_diff.return_value = GitDiff()
    result = git_sync_project(conn, indexer, "/project", "old_sha")
    assert result == SyncResult(updated=0, deleted=0, unchanged=0)
    indexer.reindex_file.assert_not_called()
    indexer.delete_file.assert_not_called()


@patch("synapps.indexer.sync.set_last_indexed_commit")
@patch("synapps.indexer.sync.rev_parse_head", return_value="new_sha")
@patch("synapps.indexer.sync.compute_git_diff")
def test_modified_file_reindexed(mock_diff, mock_rev, mock_set, conn, indexer):
    mock_diff.return_value = GitDiff(to_reindex={"/project/a.cs"})
    result = git_sync_project(conn, indexer, "/project", "old_sha")
    indexer.reindex_file.assert_called_once_with("/project/a.cs", "/project")
    assert result.updated == 1
    assert result.deleted == 0


@patch("synapps.indexer.sync.set_last_indexed_commit")
@patch("synapps.indexer.sync.rev_parse_head", return_value="new_sha")
@patch("synapps.indexer.sync.compute_git_diff")
def test_deleted_file_removed(mock_diff, mock_rev, mock_set, conn, indexer):
    mock_diff.return_value = GitDiff(to_delete={"/project/old.cs"})
    result = git_sync_project(conn, indexer, "/project", "old_sha")
    indexer.delete_file.assert_called_once_with("/project/old.cs")
    assert result.deleted == 1
    assert result.updated == 0


@patch("synapps.indexer.sync.set_last_indexed_commit")
@patch("synapps.indexer.sync.rename_file_node")
@patch("synapps.indexer.sync.rev_parse_head", return_value="new_sha")
@patch("synapps.indexer.sync.compute_git_diff")
def test_renamed_file_calls_rename_and_reindex(mock_diff, mock_rev, mock_rename, mock_set, conn, indexer):
    mock_diff.return_value = GitDiff(
        renames=[("/project/old.cs", "/project/new.cs")],
        to_reindex={"/project/new.cs"},
    )
    result = git_sync_project(conn, indexer, "/project", "old_sha")
    mock_rename.assert_called_once_with(conn, "/project/old.cs", "/project/new.cs")
    indexer.reindex_file.assert_called_once_with("/project/new.cs", "/project")
    assert result.updated == 2  # 1 rename + 1 reindex


@patch("synapps.indexer.sync.set_last_indexed_commit")
@patch("synapps.indexer.sync.rev_parse_head", return_value="head_sha")
@patch("synapps.indexer.sync.compute_git_diff")
def test_stores_commit_sha_after_sync(mock_diff, mock_rev, mock_set, conn, indexer):
    mock_diff.return_value = GitDiff(to_reindex={"/project/a.cs"})
    git_sync_project(conn, indexer, "/project", "old_sha")
    mock_set.assert_called_once_with(conn, "/project", "head_sha")


@patch("synapps.indexer.sync.set_last_indexed_commit")
@patch("synapps.indexer.sync.rev_parse_head", return_value="new_sha")
@patch("synapps.indexer.sync.compute_git_diff")
def test_reindex_failure_skipped_others_processed(mock_diff, mock_rev, mock_set, conn, indexer):
    mock_diff.return_value = GitDiff(to_reindex={"/project/a.cs", "/project/b.cs"})
    indexer.reindex_file.side_effect = [Exception("boom"), None]
    result = git_sync_project(conn, indexer, "/project", "old_sha")
    assert indexer.reindex_file.call_count == 2
    assert result.updated == 1  # one succeeded


@patch("synapps.indexer.sync.set_last_indexed_commit")
@patch("synapps.indexer.sync.rev_parse_head", return_value=None)
@patch("synapps.indexer.sync.compute_git_diff")
def test_no_head_sha_skips_commit_store(mock_diff, mock_rev, mock_set, conn, indexer):
    mock_diff.return_value = GitDiff(to_reindex={"/project/a.cs"})
    git_sync_project(conn, indexer, "/project", "old_sha")
    mock_set.assert_not_called()


@patch("synapps.indexer.sync.set_last_indexed_commit")
@patch("synapps.indexer.sync.rev_parse_head", return_value="new_sha")
@patch("synapps.indexer.sync.compute_git_diff")
def test_file_extensions_filter_only_processes_matching_files(mock_diff, mock_rev, mock_set, conn, indexer):
    """With file_extensions, git_sync_project ignores files from other languages."""
    mock_diff.return_value = GitDiff(
        to_reindex={"/project/a.cs", "/project/b.ts", "/project/c.tsx"},
        to_delete={"/project/old.cs", "/project/old.py"},
        renames=[("/project/x.cs", "/project/y.cs"), ("/project/m.ts", "/project/n.ts")],
    )
    result = git_sync_project(
        conn, indexer, "/project", "old_sha",
        file_extensions=frozenset({".cs"}),
    )
    # Only .cs files should be processed
    reindex_paths = {c.args[0] for c in indexer.reindex_file.call_args_list}
    assert reindex_paths == {"/project/a.cs"}
    indexer.delete_file.assert_called_once_with("/project/old.cs")
    assert result.updated == 2  # 1 reindex + 1 rename
    assert result.deleted == 1


@patch("synapps.indexer.sync.rev_parse_head", return_value="abc123")
@patch("synapps.indexer.sync.compute_git_diff")
def test_file_extensions_filter_all_filtered_returns_zero(mock_diff, mock_rev, conn, indexer):
    """When all changed files are from other languages, result is zero."""
    mock_diff.return_value = GitDiff(
        to_reindex={"/project/a.ts", "/project/b.py"},
        to_delete={"/project/old.js"},
    )
    result = git_sync_project(
        conn, indexer, "/project", "old_sha",
        file_extensions=frozenset({".cs"}),
    )
    assert result == SyncResult(updated=0, deleted=0, unchanged=0)
    indexer.reindex_file.assert_not_called()
    indexer.delete_file.assert_not_called()
