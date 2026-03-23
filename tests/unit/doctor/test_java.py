from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from synapse.doctor.checks.java import JavaCheck
from synapse.doctor.checks.jdtls import JdtlsCheck


# ---------------------------------------------------------------------------
# JavaCheck tests (LANG-07)
# ---------------------------------------------------------------------------


def test_java_pass_when_version_exits_zero() -> None:
    with patch("synapse.doctor.checks.java.shutil") as mock_shutil, \
         patch("synapse.doctor.checks.java.subprocess") as mock_sub:
        mock_shutil.which.return_value = "/usr/bin/java"
        mock_sub.run.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")
        mock_sub.TimeoutExpired = subprocess.TimeoutExpired
        result = JavaCheck().run()
    assert result.status == "pass"
    assert "/usr/bin/java" in result.detail


def test_java_fail_when_not_on_path() -> None:
    with patch("synapse.doctor.checks.java.shutil") as mock_shutil:
        mock_shutil.which.return_value = None
        result = JavaCheck().run()
    assert result.status == "fail"
    assert result.fix is not None
    assert "adoptium.net" in result.fix


def test_java_fail_when_version_exits_nonzero() -> None:
    with patch("synapse.doctor.checks.java.shutil") as mock_shutil, \
         patch("synapse.doctor.checks.java.subprocess") as mock_sub:
        mock_shutil.which.return_value = "/usr/bin/java"
        mock_sub.run.return_value = MagicMock(returncode=1, stdout=b"", stderr=b"")
        mock_sub.TimeoutExpired = subprocess.TimeoutExpired
        result = JavaCheck().run()
    assert result.status == "fail"


def test_java_fail_when_timeout() -> None:
    with patch("synapse.doctor.checks.java.shutil") as mock_shutil, \
         patch("synapse.doctor.checks.java.subprocess") as mock_sub:
        mock_shutil.which.return_value = "/usr/bin/java"
        mock_sub.run.side_effect = subprocess.TimeoutExpired(cmd="java", timeout=10)
        mock_sub.TimeoutExpired = subprocess.TimeoutExpired
        result = JavaCheck().run()
    assert result.status == "fail"


def test_java_group_is_java() -> None:
    assert JavaCheck().group == "java"


def test_java_pass_fix_is_none() -> None:
    with patch("synapse.doctor.checks.java.shutil") as mock_shutil, \
         patch("synapse.doctor.checks.java.subprocess") as mock_sub:
        mock_shutil.which.return_value = "/usr/bin/java"
        mock_sub.run.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")
        mock_sub.TimeoutExpired = subprocess.TimeoutExpired
        result = JavaCheck().run()
    assert result.fix is None


# ---------------------------------------------------------------------------
# JdtlsCheck tests (LANG-08)
# ---------------------------------------------------------------------------


def test_jdtls_pass_when_launcher_jar_exists() -> None:
    with patch("synapse.doctor.checks.jdtls.shutil") as mock_shutil, \
         patch("synapse.doctor.checks.jdtls.glob") as mock_glob:
        mock_shutil.which.return_value = "/usr/bin/java"
        mock_glob.glob.return_value = [
            "/home/user/.solidlsp/language_servers/static/EclipseJDTLS/jdtls/plugins/org.eclipse.equinox.launcher_1.7.100.jar"
        ]
        result = JdtlsCheck().run()
    assert result.status == "pass"
    assert "org.eclipse.equinox.launcher" in result.detail


def test_jdtls_fail_when_launcher_jar_missing() -> None:
    with patch("synapse.doctor.checks.jdtls.shutil") as mock_shutil, \
         patch("synapse.doctor.checks.jdtls.glob") as mock_glob:
        mock_shutil.which.return_value = "/usr/bin/java"
        mock_glob.glob.return_value = []
        result = JdtlsCheck().run()
    assert result.status == "fail"
    assert result.fix is not None
    assert "eclipse-jdtls" in result.fix or "github.com/eclipse" in result.fix


def test_jdtls_warn_when_java_absent() -> None:
    with patch("synapse.doctor.checks.jdtls.shutil") as mock_shutil:
        mock_shutil.which.return_value = None
        result = JdtlsCheck().run()
    assert result.status == "warn"
    assert result.fix is None


def test_jdtls_group_is_java() -> None:
    assert JdtlsCheck().group == "java"


def test_jdtls_pass_fix_is_none() -> None:
    with patch("synapse.doctor.checks.jdtls.shutil") as mock_shutil, \
         patch("synapse.doctor.checks.jdtls.glob") as mock_glob:
        mock_shutil.which.return_value = "/usr/bin/java"
        mock_glob.glob.return_value = [
            "/home/user/.solidlsp/language_servers/static/EclipseJDTLS/jdtls/plugins/org.eclipse.equinox.launcher_1.7.100.jar"
        ]
        result = JdtlsCheck().run()
    assert result.fix is None
