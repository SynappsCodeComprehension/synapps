import time
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from synapse.watcher.watcher import FileWatcher


def wait_for_call(mock: MagicMock, *, timeout: float = 2.0, interval: float = 0.05) -> None:
    """Poll a mock until it has been called, or raise after timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if mock.called:
            return
        time.sleep(interval)
    raise AssertionError(f"Mock {mock} was not called within {timeout}s")


@pytest.mark.timeout(5)
def test_watcher_calls_on_change_for_cs_file() -> None:
    on_change = MagicMock()
    on_delete = MagicMock()

    with tempfile.TemporaryDirectory() as tmpdir:
        watcher = FileWatcher(
            root_path=tmpdir,
            on_change=on_change,
            on_delete=on_delete,
            debounce_seconds=0.05,
        )
        watcher.start()
        try:
            test_file = Path(tmpdir) / "Test.cs"
            test_file.write_text("// hello")
            wait_for_call(on_change)
            args = on_change.call_args[0]
            assert args[0].endswith(".cs")
        finally:
            watcher.stop()


@pytest.mark.timeout(5)
def test_watcher_ignores_non_cs_files() -> None:
    on_change = MagicMock()
    on_delete = MagicMock()

    with tempfile.TemporaryDirectory() as tmpdir:
        watcher = FileWatcher(
            root_path=tmpdir,
            on_change=on_change,
            on_delete=on_delete,
            debounce_seconds=0.05,
        )
        watcher.start()
        try:
            (Path(tmpdir) / "notes.txt").write_text("ignore me")
            time.sleep(0.3)
            on_change.assert_not_called()
        finally:
            watcher.stop()


@pytest.mark.timeout(5)
def test_watcher_calls_on_change_for_py_file() -> None:
    on_change = MagicMock()
    on_delete = MagicMock()

    with tempfile.TemporaryDirectory() as tmpdir:
        watcher = FileWatcher(
            root_path=tmpdir,
            on_change=on_change,
            on_delete=on_delete,
            debounce_seconds=0.05,
            watched_extensions=frozenset({".py"}),
        )
        watcher.start()
        try:
            test_file = Path(tmpdir) / "example.py"
            test_file.write_text("# hello")
            wait_for_call(on_change)
            args = on_change.call_args[0]
            assert args[0].endswith(".py")
        finally:
            watcher.stop()


@pytest.mark.timeout(5)
def test_watcher_ignores_non_py_files_when_watching_python() -> None:
    on_change = MagicMock()
    on_delete = MagicMock()

    with tempfile.TemporaryDirectory() as tmpdir:
        watcher = FileWatcher(
            root_path=tmpdir,
            on_change=on_change,
            on_delete=on_delete,
            debounce_seconds=0.05,
            watched_extensions=frozenset({".py"}),
        )
        watcher.start()
        try:
            (Path(tmpdir) / "Test.cs").write_text("// should be ignored")
            (Path(tmpdir) / "notes.txt").write_text("also ignored")
            time.sleep(0.3)
            on_change.assert_not_called()
        finally:
            watcher.stop()


@pytest.mark.timeout(5)
def test_watcher_ignores_gitignored_cs_file() -> None:
    on_change = MagicMock()
    on_delete = MagicMock()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Set up a .gitignore that ignores the obj/ directory
        (Path(tmpdir) / ".gitignore").write_text("obj/\n")
        obj_dir = Path(tmpdir) / "obj"
        obj_dir.mkdir()

        watcher = FileWatcher(
            root_path=tmpdir,
            on_change=on_change,
            on_delete=on_delete,
            debounce_seconds=0.05,
        )
        watcher.start()
        try:
            (obj_dir / "Generated.cs").write_text("// generated")
            time.sleep(0.3)
            on_change.assert_not_called()
        finally:
            watcher.stop()


@pytest.mark.timeout(5)
def test_watcher_allows_non_gitignored_cs_file() -> None:
    on_change = MagicMock()
    on_delete = MagicMock()

    with tempfile.TemporaryDirectory() as tmpdir:
        # .gitignore ignores obj/ but not src/
        (Path(tmpdir) / ".gitignore").write_text("obj/\n")
        src_dir = Path(tmpdir) / "src"
        src_dir.mkdir()

        watcher = FileWatcher(
            root_path=tmpdir,
            on_change=on_change,
            on_delete=on_delete,
            debounce_seconds=0.05,
        )
        watcher.start()
        try:
            (src_dir / "App.cs").write_text("// real code")
            wait_for_call(on_change)
            assert on_change.call_args[0][0].endswith(".cs")
        finally:
            watcher.stop()


@pytest.mark.timeout(5)
def test_watcher_ignores_synignored_file() -> None:
    on_change = MagicMock()
    on_delete = MagicMock()

    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / ".synignore").write_text("generated/\n")
        gen_dir = Path(tmpdir) / "generated"
        gen_dir.mkdir()

        watcher = FileWatcher(
            root_path=tmpdir,
            on_change=on_change,
            on_delete=on_delete,
            debounce_seconds=0.05,
        )
        watcher.start()
        try:
            (gen_dir / "Output.cs").write_text("// generated")
            time.sleep(0.3)
            on_change.assert_not_called()
        finally:
            watcher.stop()


@pytest.mark.timeout(5)
def test_watcher_stop_joins_observer_thread() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        watcher = FileWatcher(
            root_path=tmpdir,
            on_change=MagicMock(),
            on_delete=MagicMock(),
            debounce_seconds=0.05,
        )
        watcher.start()
        watcher.stop()
        assert not watcher.is_running()


_TS_EXTENSIONS = frozenset({".ts", ".tsx", ".js", ".jsx", ".mts", ".cts", ".mjs", ".cjs"})


@pytest.mark.timeout(5)
def test_watcher_calls_on_change_for_ts_file() -> None:
    on_change = MagicMock()
    on_delete = MagicMock()

    with tempfile.TemporaryDirectory() as tmpdir:
        watcher = FileWatcher(
            root_path=tmpdir,
            on_change=on_change,
            on_delete=on_delete,
            debounce_seconds=0.05,
            watched_extensions=_TS_EXTENSIONS,
        )
        watcher.start()
        try:
            test_file = Path(tmpdir) / "animals.ts"
            test_file.write_text("export class Dog {}")
            wait_for_call(on_change)
            args = on_change.call_args[0]
            assert args[0].endswith(".ts")
        finally:
            watcher.stop()


@pytest.mark.timeout(5)
def test_watcher_calls_on_change_for_js_file() -> None:
    on_change = MagicMock()
    on_delete = MagicMock()

    with tempfile.TemporaryDirectory() as tmpdir:
        watcher = FileWatcher(
            root_path=tmpdir,
            on_change=on_change,
            on_delete=on_delete,
            debounce_seconds=0.05,
            watched_extensions=_TS_EXTENSIONS,
        )
        watcher.start()
        try:
            test_file = Path(tmpdir) / "utils.js"
            test_file.write_text("function formatName(name) { return name; }")
            wait_for_call(on_change)
            args = on_change.call_args[0]
            assert args[0].endswith(".js")
        finally:
            watcher.stop()


@pytest.mark.timeout(5)
def test_watcher_ignores_non_ts_files_when_watching_typescript() -> None:
    on_change = MagicMock()
    on_delete = MagicMock()

    with tempfile.TemporaryDirectory() as tmpdir:
        watcher = FileWatcher(
            root_path=tmpdir,
            on_change=on_change,
            on_delete=on_delete,
            debounce_seconds=0.05,
            watched_extensions=_TS_EXTENSIONS,
        )
        watcher.start()
        try:
            (Path(tmpdir) / "example.py").write_text("# should be ignored")
            (Path(tmpdir) / "notes.txt").write_text("also ignored")
            time.sleep(0.3)
            on_change.assert_not_called()
        finally:
            watcher.stop()
