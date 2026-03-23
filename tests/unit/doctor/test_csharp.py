from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from synapse.doctor.checks.dotnet import DotNetCheck
from synapse.doctor.checks.csharp_ls import CSharpLSCheck


def test_dotnet_pass_when_list_runtimes_has_netcore_app() -> None:
    with patch("synapse.doctor.checks.dotnet.shutil") as mock_shutil, \
         patch("synapse.doctor.checks.dotnet.subprocess") as mock_sub:
        mock_shutil.which.return_value = "/usr/local/bin/dotnet"
        mock_sub.run.return_value.returncode = 0
        mock_sub.run.return_value.stdout = "Microsoft.NETCore.App 10.0.2 [/usr/local/share/dotnet/shared/Microsoft.NETCore.App/10.0.2]\n"
        mock_sub.TimeoutExpired = subprocess.TimeoutExpired
        result = DotNetCheck().run()
    assert result.status == "pass"
    assert "/usr/local/bin/dotnet" in result.detail


def test_dotnet_fail_when_not_on_path() -> None:
    with patch("synapse.doctor.checks.dotnet.shutil") as mock_shutil:
        mock_shutil.which.return_value = None
        result = DotNetCheck().run()
    assert result.status == "fail"
    assert result.fix is not None
    assert "dotnet.microsoft.com" in result.fix


def test_dotnet_fail_when_no_netcore_runtime() -> None:
    with patch("synapse.doctor.checks.dotnet.shutil") as mock_shutil, \
         patch("synapse.doctor.checks.dotnet.subprocess") as mock_sub:
        mock_shutil.which.return_value = "/usr/local/bin/dotnet"
        mock_sub.run.return_value.returncode = 0
        mock_sub.run.return_value.stdout = ""
        mock_sub.TimeoutExpired = subprocess.TimeoutExpired
        result = DotNetCheck().run()
    assert result.status == "fail"
    assert result.fix is not None


def test_dotnet_fail_when_list_runtimes_exits_nonzero() -> None:
    with patch("synapse.doctor.checks.dotnet.shutil") as mock_shutil, \
         patch("synapse.doctor.checks.dotnet.subprocess") as mock_sub:
        mock_shutil.which.return_value = "/usr/local/bin/dotnet"
        mock_sub.run.return_value.returncode = 1
        mock_sub.run.return_value.stdout = ""
        mock_sub.TimeoutExpired = subprocess.TimeoutExpired
        result = DotNetCheck().run()
    assert result.status == "fail"


def test_dotnet_fail_when_timeout() -> None:
    with patch("synapse.doctor.checks.dotnet.shutil") as mock_shutil, \
         patch("synapse.doctor.checks.dotnet.subprocess") as mock_sub:
        mock_shutil.which.return_value = "/usr/local/bin/dotnet"
        mock_sub.TimeoutExpired = subprocess.TimeoutExpired
        mock_sub.run.side_effect = subprocess.TimeoutExpired("dotnet", 10)
        result = DotNetCheck().run()
    assert result.status == "fail"


def test_dotnet_group_is_csharp() -> None:
    assert DotNetCheck().group == "csharp"


# --- CSharpLSCheck tests ---


def test_csharp_ls_pass_when_version_exits_zero() -> None:
    with patch("synapse.doctor.checks.csharp_ls.shutil") as mock_shutil, \
         patch("synapse.doctor.checks.csharp_ls.subprocess") as mock_sub:
        mock_shutil.which.side_effect = lambda name: {
            "dotnet": "/usr/local/bin/dotnet",
            "csharp-ls": "/usr/local/bin/csharp-ls",
        }.get(name)
        mock_sub.run.return_value.returncode = 0
        mock_sub.TimeoutExpired = subprocess.TimeoutExpired
        result = CSharpLSCheck().run()
    assert result.status == "pass"
    assert "/usr/local/bin/csharp-ls" in result.detail


def test_csharp_ls_fail_when_not_on_path() -> None:
    with patch("synapse.doctor.checks.csharp_ls.shutil") as mock_shutil, \
         patch("synapse.doctor.checks.csharp_ls.subprocess") as mock_sub:
        mock_shutil.which.side_effect = lambda name: {
            "dotnet": "/usr/local/bin/dotnet",
            "csharp-ls": None,
        }.get(name)
        mock_sub.TimeoutExpired = subprocess.TimeoutExpired
        result = CSharpLSCheck().run()
    assert result.status == "fail"
    assert result.fix is not None
    assert "dotnet tool install" in result.fix


def test_csharp_ls_warn_when_dotnet_absent() -> None:
    with patch("synapse.doctor.checks.csharp_ls.shutil") as mock_shutil:
        mock_shutil.which.side_effect = lambda name: {
            "dotnet": None,
        }.get(name)
        result = CSharpLSCheck().run()
    assert result.status == "warn"
    assert result.fix is None


def test_csharp_ls_fail_when_version_exits_nonzero() -> None:
    with patch("synapse.doctor.checks.csharp_ls.shutil") as mock_shutil, \
         patch("synapse.doctor.checks.csharp_ls.subprocess") as mock_sub:
        mock_shutil.which.side_effect = lambda name: {
            "dotnet": "/usr/local/bin/dotnet",
            "csharp-ls": "/usr/local/bin/csharp-ls",
        }.get(name)
        mock_sub.run.return_value.returncode = 1
        mock_sub.TimeoutExpired = subprocess.TimeoutExpired
        result = CSharpLSCheck().run()
    assert result.status == "fail"


def test_csharp_ls_fail_when_timeout() -> None:
    with patch("synapse.doctor.checks.csharp_ls.shutil") as mock_shutil, \
         patch("synapse.doctor.checks.csharp_ls.subprocess") as mock_sub:
        mock_shutil.which.side_effect = lambda name: {
            "dotnet": "/usr/local/bin/dotnet",
            "csharp-ls": "/usr/local/bin/csharp-ls",
        }.get(name)
        mock_sub.TimeoutExpired = subprocess.TimeoutExpired
        mock_sub.run.side_effect = subprocess.TimeoutExpired("csharp-ls", 10)
        result = CSharpLSCheck().run()
    assert result.status == "fail"


def test_csharp_ls_group_is_csharp() -> None:
    assert CSharpLSCheck().group == "csharp"
