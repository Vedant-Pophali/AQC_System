# src/policy/policy_engine.py

from datetime import datetime
from pathlib import Path
import json

# -------------------------
# CI POLICY (ABSOLUTE)
# -------------------------
CI_POLICY = {
    "PASSED": 0,
    "WARNING": 0,
    "REJECTED": 2,
    "ERROR": 3
}

# Tooling-only modules
TOOLING_MODULES = {
    "qctools_qc"
}

# Tooling error codes eligible for deviation
DEVIATION_ELIGIBLE_ERRORS = {
    "QCTOOLS_UNAVAILABLE",
    "QCTOOLS_NOT_INSTALLED",
    "QCTOOLS_BUILD_MISSING"
}


# -------------------------
# Deviation Loader
# -------------------------
def load_known_deviations(md_path: Path, profile: str):
    """
    Load valid (non-expired, profile-matching) deviations.
    """
    if not md_path.exists():
        return []

    today = datetime.utcnow().date()
    deviations = []

    with open(md_path, "r", encoding="utf-8") as f:
        block = {}

        for line in f:
            line = line.strip()

            if not line:
                if block:
                    _commit(block, deviations, today, profile)
                    block = {}
                continue

            if ":" in line:
                k, v = line.split(":", 1)
                block[k.strip()] = v.strip()

        if block:
            _commit(block, deviations, today, profile)

    return deviations


def _commit(block, deviations, today, profile):
    try:
        if profile not in block["profiles"]:
            return

        expires = datetime.strptime(block["expires"], "%Y-%m-%d").date()
        if expires < today:
            return

        deviations.append(block)
    except Exception:
        return


# -------------------------
# Policy Resolution
# -------------------------
def resolve_module_status(module_report, profile, deviations):
    """
    Apply policy to a single module.
    Returns effective_status and annotations.
    """
    status = module_report["status"]
    module = module_report["module"]
    error_code = module_report.get("error_code")

    annotations = []

    # PASSED / WARNING → untouched
    if status in ("PASSED", "WARNING"):
        return status, annotations

    # REJECTED → always fatal
    if status == "REJECTED":
        return status, annotations

    # ERROR handling
    if status == "ERROR":
        # STRICT → no deviations allowed
        if profile == "strict":
            return status, annotations

        # OTT → only tooling errors may be softened
        if module in TOOLING_MODULES and error_code in DEVIATION_ELIGIBLE_ERRORS:
            for dev in deviations:
                if dev.get("module") == module:
                    annotations.append(f"Deviation applied: {dev.get('id')}")
                    return "NOT_APPLICABLE", annotations

        return status, annotations

    return status, annotations


# -------------------------
# Final CI Decision
# -------------------------
def compute_ci(modules_effective_status):
    """
    Compute final CI exit code.
    """
    worst = "PASSED"

    for status in modules_effective_status.values():
        if status in ("ERROR", "REJECTED"):
            worst = "ERROR"
            break
        if status == "WARNING" and worst == "PASSED":
            worst = "WARNING"

    return worst, CI_POLICY[worst]
