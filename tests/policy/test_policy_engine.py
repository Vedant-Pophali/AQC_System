import tempfile
from pathlib import Path

from src.policy.policy_engine import (
    load_known_deviations,
    resolve_module_status,
    compute_ci
)


def _fake_report(status, module="qctools_qc", error_code=None):
    r = {
        "module": module,
        "status": status
    }
    if error_code:
        r["error_code"] = error_code
    return r


def test_strict_qctools_error_fails():
    report = _fake_report(
        status="ERROR",
        error_code="QCTOOLS_UNAVAILABLE"
    )

    status, _ = resolve_module_status(
        report,
        profile="strict",
        deviations=[]
    )

    assert status == "ERROR"


def test_ott_qctools_error_with_deviation_softens():
    report = _fake_report(
        status="ERROR",
        error_code="QCTOOLS_UNAVAILABLE"
    )

    deviations = [{
        "id": "DEV-001",
        "module": "qctools_qc"
    }]

    status, notes = resolve_module_status(
        report,
        profile="ott",
        deviations=deviations
    )

    assert status == "NOT_APPLICABLE"
    assert notes


def test_ott_qctools_error_without_deviation_fails():
    report = _fake_report(
        status="ERROR",
        error_code="QCTOOLS_UNAVAILABLE"
    )

    status, _ = resolve_module_status(
        report,
        profile="ott",
        deviations=[]
    )

    assert status == "ERROR"


def test_rejected_is_never_softened():
    report = _fake_report(status="REJECTED")

    status, _ = resolve_module_status(
        report,
        profile="ott",
        deviations=[{"id": "DEV-001", "module": "qctools_qc"}]
    )

    assert status == "REJECTED"


def test_ci_computation():
    statuses = {
        "artifact_qc": "PASSED",
        "qctools_qc": "NOT_APPLICABLE"
    }

    overall, exit_code = compute_ci(statuses)

    assert overall == "PASSED"
    assert exit_code == 0
