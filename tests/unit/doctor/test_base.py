from __future__ import annotations

import dataclasses
from typing import get_args

import pytest

from synapse.doctor.base import CheckResult, CheckStatus, DoctorCheck


def test_checkresult_has_required_fields() -> None:
    result = CheckResult(name="x", status="pass", detail="ok", fix=None, group="infra")
    assert result.name == "x"
    assert result.status == "pass"
    assert result.detail == "ok"
    assert result.fix is None
    assert result.group == "infra"


def test_checkresult_is_frozen() -> None:
    result = CheckResult(name="x", status="pass", detail="ok", fix=None, group="infra")
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.name = "y"  # type: ignore[misc]


def test_checkresult_fix_can_be_string() -> None:
    result = CheckResult(name="x", status="pass", detail="ok", fix="install foo", group="infra")
    assert result.fix == "install foo"


def test_checkstatus_valid_values() -> None:
    assert frozenset(get_args(CheckStatus)) == {"pass", "warn", "fail"}


def test_doctor_check_is_runtime_checkable() -> None:
    class _PassCheck:
        def run(self) -> CheckResult:
            return CheckResult(name="t", status="pass", detail="ok", fix=None, group="x")

    assert isinstance(_PassCheck(), DoctorCheck) is True


def test_incomplete_object_fails_protocol_check() -> None:
    class NoRunMethod:
        pass

    assert isinstance(NoRunMethod(), DoctorCheck) is False
