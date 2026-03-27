from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from synapse.util.file_system import ProjectFileFilter


class TestProjectFileFilter:
    """Tests for the unified ProjectFileFilter that combines _ALWAYS_SKIP, .gitignore, and .synignore."""

    def test_ignores_always_skip_directory(self, tmp_path: Path) -> None:
        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        f = ProjectFileFilter(str(tmp_path))
        assert f.is_dir_ignored(str(node_modules))

    def test_allows_normal_directory(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        f = ProjectFileFilter(str(tmp_path))
        assert not f.is_dir_ignored(str(src))

    def test_ignores_file_inside_always_skip_directory(self, tmp_path: Path) -> None:
        obj_dir = tmp_path / "obj"
        obj_dir.mkdir()
        cs_file = obj_dir / "Generated.cs"
        cs_file.write_text("// generated")
        f = ProjectFileFilter(str(tmp_path))
        assert f.is_file_ignored(str(cs_file))

    def test_allows_file_outside_always_skip_directory(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        cs_file = src / "App.cs"
        cs_file.write_text("// real code")
        f = ProjectFileFilter(str(tmp_path))
        assert not f.is_file_ignored(str(cs_file))

    def test_ignores_gitignored_file(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("*.log\n")
        log_file = tmp_path / "debug.log"
        log_file.write_text("log data")
        f = ProjectFileFilter(str(tmp_path))
        assert f.is_file_ignored(str(log_file))

    def test_ignores_gitignored_directory(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("output/\n")
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        f = ProjectFileFilter(str(tmp_path))
        assert f.is_dir_ignored(str(output_dir))

    def test_ignores_file_inside_gitignored_directory(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("output/\n")
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        result_file = output_dir / "result.cs"
        result_file.write_text("// output")
        f = ProjectFileFilter(str(tmp_path))
        assert f.is_file_ignored(str(result_file))

    def test_ignores_synignored_file(self, tmp_path: Path) -> None:
        (tmp_path / ".synignore").write_text("generated/\n")
        gen_dir = tmp_path / "generated"
        gen_dir.mkdir()
        gen_file = gen_dir / "Output.cs"
        gen_file.write_text("// generated")
        f = ProjectFileFilter(str(tmp_path))
        assert f.is_file_ignored(str(gen_file))

    def test_ignores_synignored_directory(self, tmp_path: Path) -> None:
        (tmp_path / ".synignore").write_text("generated/\n")
        gen_dir = tmp_path / "generated"
        gen_dir.mkdir()
        f = ProjectFileFilter(str(tmp_path))
        assert f.is_dir_ignored(str(gen_dir))

    def test_allows_file_not_matching_any_rule(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("*.log\n")
        (tmp_path / ".synignore").write_text("generated/\n")
        src = tmp_path / "src"
        src.mkdir()
        cs_file = src / "App.cs"
        cs_file.write_text("// real code")
        f = ProjectFileFilter(str(tmp_path))
        assert not f.is_file_ignored(str(cs_file))

    def test_works_without_gitignore_or_synignore(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        cs_file = src / "App.cs"
        cs_file.write_text("// real code")
        f = ProjectFileFilter(str(tmp_path))
        assert not f.is_file_ignored(str(cs_file))

    def test_always_skip_takes_precedence_over_deeply_nested_path(self, tmp_path: Path) -> None:
        deep = tmp_path / "a" / "b" / "node_modules" / "pkg"
        deep.mkdir(parents=True)
        js_file = deep / "index.js"
        js_file.write_text("module.exports = {}")
        f = ProjectFileFilter(str(tmp_path))
        assert f.is_file_ignored(str(js_file))

    def test_ignores_dot_git_directory(self, tmp_path: Path) -> None:
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        f = ProjectFileFilter(str(tmp_path))
        assert f.is_dir_ignored(str(git_dir))

    def test_ignores_file_inside_dot_git(self, tmp_path: Path) -> None:
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        config = git_dir / "config"
        config.write_text("[core]")
        f = ProjectFileFilter(str(tmp_path))
        assert f.is_file_ignored(str(config))
