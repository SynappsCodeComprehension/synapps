from __future__ import annotations

import re
from contextlib import ExitStack
from unittest.mock import MagicMock, create_autospec, patch

from typer.testing import CliRunner

from synapps.cli.app import app
from synapps.doctor.base import CheckResult
from synapps.service import SynappsService

# Module-level compiled regexes for normalization
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_ABS_PATH_RE = re.compile(r"/(?:[^\s/]+/)+([^\s/]+\.(?:py|cs|ts|java))")

runner = CliRunner(env={"COLUMNS": "80"})

_ALL_CHECKS = [
    ("DockerDaemonCheck", "Docker daemon", "core"),
    ("MemgraphBoltCheck", "Memgraph", "core"),
    ("DotNetCheck", ".NET SDK", "csharp"),
    ("CSharpLSCheck", "Roslyn Language Server", "csharp"),
    ("NodeCheck", "Node.js", "typescript"),
    ("TypeScriptLSCheck", "npm", "typescript"),
    ("PythonCheck", "Python 3", "python"),
    ("PylspCheck", "pyright", "python"),
    ("JavaCheck", "Java", "java"),
    ("JdtlsCheck", "Eclipse JDT LS", "java"),
]


def normalize_cli_output(output: str) -> str:
    """Strip ANSI codes and replace absolute file paths for snapshot stability."""
    output = _ANSI_RE.sub("", output)
    output = _ABS_PATH_RE.sub(r"<PATH>/\1", output)
    return output


def _svc() -> SynappsService:
    """Return a create_autospec SynappsService with sensible defaults."""
    svc = create_autospec(SynappsService)
    svc.get_symbol.return_value = {"full_name": "A.Method", "_labels": ["Method"]}
    svc.find_callers.return_value = []
    svc.find_callees.return_value = []
    svc.search_symbols.return_value = []
    svc.get_hierarchy.return_value = {"parents": [], "children": [], "implements": []}
    return svc


def test_callers_golden(snapshot) -> None:
    svc = _svc()
    svc.find_callers.return_value = [
        {"full_name": "Namespace.ClassA.Invoke", "file_path": "/src/project/ClassA.cs", "line": 42, "signature": "Invoke(string arg) : void"},
        {"full_name": "Namespace.ClassB.Process", "file_path": "/src/project/ClassB.cs", "line": 108, "signature": "Process() : bool"},
        {"full_name": "Namespace.ClassC.Handle", "file_path": "/src/project/ClassC.cs", "line": 55},
    ]
    with patch("synapps.cli.app._get_service", return_value=svc):
        result = runner.invoke(app, ["callers", "A.Method"])
    assert normalize_cli_output(result.output) == snapshot


def test_callees_golden(snapshot) -> None:
    svc = _svc()
    svc.find_callees.return_value = [
        {"full_name": "Namespace.Helper.Log", "name": "Log", "file_path": "/src/project/Helper.cs", "line": 20, "signature": "Log(string msg) : void"},
        {"full_name": "Namespace.Db.Save", "name": "Save", "file_path": "/src/project/Db.cs", "line": 77, "signature": "Save() : Task"},
    ]
    with patch("synapps.cli.app._get_service", return_value=svc):
        result = runner.invoke(app, ["callees", "A.Method"])
    assert normalize_cli_output(result.output) == snapshot


def test_hierarchy_golden(snapshot) -> None:
    svc = _svc()
    svc.get_hierarchy.return_value = {
        "parents": [{"full_name": "Namespace.BaseService"}],
        "children": [{"full_name": "Namespace.DerivedA"}, {"full_name": "Namespace.DerivedB"}],
        "implements": [{"full_name": "Namespace.IService"}],
    }
    with patch("synapps.cli.app._get_service", return_value=svc):
        result = runner.invoke(app, ["hierarchy", "Namespace.MyService"])
    assert normalize_cli_output(result.output) == snapshot


def test_hierarchy_empty_golden(snapshot) -> None:
    svc = _svc()
    with patch("synapps.cli.app._get_service", return_value=svc):
        result = runner.invoke(app, ["hierarchy", "Namespace.Leaf"])
    assert normalize_cli_output(result.output) == snapshot


def test_search_golden(snapshot) -> None:
    svc = _svc()
    svc.search_symbols.return_value = [
        {"full_name": "Namespace.MyClass", "name": "MyClass", "kind": "Class", "file_path": "/src/project/MyClass.cs", "line": 10, "language": "csharp"},
        {"full_name": "Namespace.MyClass.MyMethod", "name": "MyMethod", "kind": "Method", "file_path": "/src/project/MyClass.cs", "line": 25, "language": "csharp", "signature": "MyMethod(int x) : string"},
        {"full_name": "Other.MyClassHelper", "name": "MyClassHelper", "kind": "Class", "file_path": "/src/other/Helper.cs", "line": 5, "language": "csharp"},
    ]
    with patch("synapps.cli.app._get_service", return_value=svc):
        result = runner.invoke(app, ["search", "MyClass"])
    assert normalize_cli_output(result.output) == snapshot


def test_doctor_all_pass_golden(snapshot) -> None:
    patches = [patch(f"synapps.cli.app.{cls}") for cls, _, _ in _ALL_CHECKS]
    with ExitStack() as stack:
        mocks = [stack.enter_context(p) for p in patches]
        for mock, (_, name, group) in zip(mocks, _ALL_CHECKS):
            mock.return_value.run.return_value = CheckResult(
                name=name, status="pass", detail="ok", fix=None, group=group
            )
        result = runner.invoke(app, ["doctor"])
    assert normalize_cli_output(result.output) == snapshot


def test_doctor_with_failure_golden(snapshot) -> None:
    patches = [patch(f"synapps.cli.app.{cls}") for cls, _, _ in _ALL_CHECKS]
    with ExitStack() as stack:
        mocks = [stack.enter_context(p) for p in patches]
        for mock, (_, name, group) in zip(mocks, _ALL_CHECKS):
            mock.return_value.run.return_value = CheckResult(
                name=name, status="pass", detail="ok", fix=None, group=group
            )
        # Override Docker check to fail
        mocks[0].return_value.run.return_value = CheckResult(
            name="Docker daemon", status="fail", detail="not running",
            fix="Install Docker Desktop and start it", group="core"
        )
        result = runner.invoke(app, ["doctor"])
    assert normalize_cli_output(result.output) == snapshot


def test_normalize_strips_ansi_and_paths() -> None:
    raw = "\x1b[32mOK\x1b[0m /Users/alex/Dev/project/src/main.py:42"
    result = normalize_cli_output(raw)
    assert "\x1b[" not in result
    assert "/Users/" not in result
    assert "<PATH>/main.py" in result
    assert "OK" in result
