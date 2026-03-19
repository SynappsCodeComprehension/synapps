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
def test_watcher_stop_joins_observer_thread() -> None:
    watcher = FileWatcher(
        root_path=tempfile.gettempdir(),
        on_change=MagicMock(),
        on_delete=MagicMock(),
        debounce_seconds=0.05,
    )
    watcher.start()
    watcher.stop()
    assert not watcher.is_running()
