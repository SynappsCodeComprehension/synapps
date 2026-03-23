from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from synapse.doctor.checks.python3 import PythonCheck


def test_python_pass_when_version_exits_zero() -> None:
    with patch("synapse.doctor.checks.python3.shutil") as mock_shutil:
        with patch("synapse.doctor.checks.python3.subprocess") as mock_sub:
            mock_shutil.which.return_value = "/usr/bin/python3"
            mock_sub.run.return_value = MagicMock(returncode=0)
            mock_sub.TimeoutExpired = subprocess.TimeoutExpired
            result = PythonCheck().run()
    assert result.status == "pass"
    assert "/usr/bin/python3" in result.detail


def test_python_fail_when_not_on_path() -> None:
    with patch("synapse.doctor.checks.python3.shutil") as mock_shutil:
        mock_shutil.which.return_value = None
        result = PythonCheck().run()
    assert result.status == "fail"
    assert result.fix is not None
    assert "python.org" in result.fix


def test_python_fail_when_version_exits_nonzero() -> None:
    with patch("synapse.doctor.checks.python3.shutil") as mock_shutil:
        with patch("synapse.doctor.checks.python3.subprocess") as mock_sub:
            mock_shutil.which.return_value = "/usr/bin/python3"
            mock_sub.run.return_value = MagicMock(returncode=1)
            mock_sub.TimeoutExpired = subprocess.TimeoutExpired
            result = PythonCheck().run()
    assert result.status == "fail"


def test_python_fail_when_timeout() -> None:
    with patch("synapse.doctor.checks.python3.shutil") as mock_shutil:
        with patch("synapse.doctor.checks.python3.subprocess") as mock_sub:
            mock_shutil.which.return_value = "/usr/bin/python3"
            mock_sub.run.side_effect = subprocess.TimeoutExpired(cmd="python3", timeout=10)
            mock_sub.TimeoutExpired = subprocess.TimeoutExpired
            result = PythonCheck().run()
    assert result.status == "fail"


def test_python_group_is_python() -> None:
    assert PythonCheck().group == "python"


def test_python_pass_fix_is_none() -> None:
    with patch("synapse.doctor.checks.python3.shutil") as mock_shutil:
        with patch("synapse.doctor.checks.python3.subprocess") as mock_sub:
            mock_shutil.which.return_value = "/usr/bin/python3"
            mock_sub.run.return_value = MagicMock(returncode=0)
            mock_sub.TimeoutExpired = subprocess.TimeoutExpired
            result = PythonCheck().run()
    assert result.fix is None
