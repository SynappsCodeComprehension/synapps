from __future__ import annotations

import os

import pytest

from synapse.util.file_system import SynignoreFilter, load_synignore


class TestLoadSynignore:
    def test_returns_none_when_no_file(self, tmp_path):
        assert load_synignore(str(tmp_path)) is None

    def test_returns_none_for_empty_file(self, tmp_path):
        (tmp_path / ".synignore").write_text("")
        assert load_synignore(str(tmp_path)) is None

    def test_returns_none_for_comments_only(self, tmp_path):
        (tmp_path / ".synignore").write_text("# just a comment\n# another comment\n")
        assert load_synignore(str(tmp_path)) is None

    def test_returns_filter_for_valid_patterns(self, tmp_path):
        (tmp_path / ".synignore").write_text("worktrees/\n")
        result = load_synignore(str(tmp_path))
        assert isinstance(result, SynignoreFilter)

    def test_ignores_blank_lines(self, tmp_path):
        (tmp_path / ".synignore").write_text("\n\nworktrees/\n\n")
        result = load_synignore(str(tmp_path))
        assert result is not None

    def test_handles_unreadable_file(self, tmp_path):
        synignore_path = tmp_path / ".synignore"
        synignore_path.write_text("test")
        synignore_path.chmod(0o000)
        try:
            assert load_synignore(str(tmp_path)) is None
        finally:
            synignore_path.chmod(0o644)


class TestSynignoreFilter:
    def _make_filter(self, tmp_path, patterns: str) -> SynignoreFilter:
        (tmp_path / ".synignore").write_text(patterns)
        result = load_synignore(str(tmp_path))
        assert result is not None
        return result

    def test_ignores_matching_directory(self, tmp_path):
        (tmp_path / "worktrees").mkdir()
        f = self._make_filter(tmp_path, "worktrees/\n")
        assert f.is_dir_ignored(str(tmp_path / "worktrees"))

    def test_does_not_ignore_non_matching_directory(self, tmp_path):
        (tmp_path / "src").mkdir()
        f = self._make_filter(tmp_path, "worktrees/\n")
        assert not f.is_dir_ignored(str(tmp_path / "src"))

    def test_ignores_matching_file(self, tmp_path):
        (tmp_path / "secret.log").write_text("data")
        f = self._make_filter(tmp_path, "*.log\n")
        assert f.is_file_ignored(str(tmp_path / "secret.log"))

    def test_does_not_ignore_non_matching_file(self, tmp_path):
        (tmp_path / "main.py").write_text("x = 1")
        f = self._make_filter(tmp_path, "*.log\n")
        assert not f.is_file_ignored(str(tmp_path / "main.py"))

    def test_glob_pattern_matches_nested(self, tmp_path):
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)
        (nested / "test.py").write_text("x")
        f = self._make_filter(tmp_path, "a/b/\n")
        assert f.is_dir_ignored(str(nested))
        assert f.is_file_ignored(str(nested / "test.py"))

    def test_wildcard_directory_pattern(self, tmp_path):
        (tmp_path / "foo-worktree").mkdir()
        (tmp_path / "bar-worktree").mkdir()
        f = self._make_filter(tmp_path, "*-worktree/\n")
        assert f.is_dir_ignored(str(tmp_path / "foo-worktree"))
        assert f.is_dir_ignored(str(tmp_path / "bar-worktree"))

    def test_doublestar_pattern(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        (deep / "data.csv").write_text("1,2,3")
        f = self._make_filter(tmp_path, "**/*.csv\n")
        assert f.is_file_ignored(str(deep / "data.csv"))

    def test_multiple_patterns(self, tmp_path):
        (tmp_path / "worktrees").mkdir()
        (tmp_path / "generated").mkdir()
        (tmp_path / "src").mkdir()
        f = self._make_filter(tmp_path, "worktrees/\ngenerated/\n")
        assert f.is_dir_ignored(str(tmp_path / "worktrees"))
        assert f.is_dir_ignored(str(tmp_path / "generated"))
        assert not f.is_dir_ignored(str(tmp_path / "src"))

    def test_is_ignored_detects_directory(self, tmp_path):
        (tmp_path / "worktrees").mkdir()
        f = self._make_filter(tmp_path, "worktrees/\n")
        assert f.is_ignored(str(tmp_path / "worktrees"))

    def test_is_ignored_detects_file(self, tmp_path):
        (tmp_path / "data.log").write_text("x")
        f = self._make_filter(tmp_path, "*.log\n")
        assert f.is_ignored(str(tmp_path / "data.log"))


class TestSynignoreInDetectWithFiles:
    def test_synignore_excludes_directory_from_detection(self, tmp_path):
        """detect_with_files should skip directories listed in .synignore."""
        from synapse.plugin import default_registry

        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("x = 1")
        ignored = tmp_path / "worktrees"
        ignored.mkdir()
        (ignored / "stale.py").write_text("y = 2")
        (tmp_path / ".synignore").write_text("worktrees/\n")

        registry = default_registry()
        results = registry.detect_with_files(str(tmp_path))
        all_files = [f for _, files in results for f in files]
        assert any("main.py" in f for f in all_files)
        assert not any("stale.py" in f for f in all_files)

    def test_synignore_excludes_file_pattern(self, tmp_path):
        """detect_with_files should skip files matching .synignore patterns."""
        from synapse.plugin import default_registry

        (tmp_path / "app.py").write_text("x = 1")
        (tmp_path / "generated.py").write_text("y = 2")
        (tmp_path / ".synignore").write_text("generated.py\n")

        registry = default_registry()
        results = registry.detect_with_files(str(tmp_path))
        all_files = [f for _, files in results for f in files]
        assert any("app.py" in f for f in all_files)
        assert not any("generated.py" in f for f in all_files)

    def test_no_synignore_file_behaves_normally(self, tmp_path):
        """Without .synignore, all files should be discovered."""
        from synapse.plugin import default_registry

        (tmp_path / "app.py").write_text("x = 1")
        registry = default_registry()
        results = registry.detect_with_files(str(tmp_path))
        all_files = [f for _, files in results for f in files]
        assert any("app.py" in f for f in all_files)
