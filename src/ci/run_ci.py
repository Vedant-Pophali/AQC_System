# src/policy/policy_engine.py

from datetime import datetime
from pathlib import Path

# -------------------------
# CI POLICY (ABSOLUTE)
# -------------------------
CI_POLICY = {
    "PASSED": 0,
    "WARNING": 0,
    "REJECTED": 2,
    "ERROR": 3
}

# -------------------------
# Tooling definitions
# -------------------------
TOOLING_MODULES = {
    "qctools_qc"
}

DEVIATION_ELIGIBLE_ERRORS = {
    "QCTOOLS_UNAVAILABLE",
    "QCTOOLS_NOT_INSTALLED",
    "QCTOOLS_BUILD_MISSING"
}


# -------------------------
# Load Known Deviations
# -------------------------
def load_known_deviations(md_path: Path, profile: str):
    """
    Load valid deviations for OTT profile only.
    STRICT profile ignores deviations entirely.
    """
    if profile != "ott":
        return []

    if not md_path.exists():
        return []

    today = datetime.utcnow().date()
    deviations = []
    block = {}

    with open(md_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                if block:
                    _commit_deviation(block, deviations, today)
                    block = {}
                continue

            if ":" in line:
                k, v = line.split(":", 1)
                block[k.strip()] = v.strip()

        if block:
            _commit_deviation(block, deviations, today)

    return deviations


def _commit_deviation(block, deviations, today):
    """
    Validate and commit a single deviation block.
    """
    try:
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
    Apply policy rules to a single module report.
    Returns (effective_status, policy_notes).
    """
    status = module_report.get("status")
    module = module_report.get("module")
    error_code = module_report.get("error_code")

    policy_notes = []

    # PASSED / WARNING → untouched
    if status in ("PASSED", "WARNING"):
        return status, policy_notes

    # REJECTED → always fatal
    if status == "REJECTED":
        return status, policy_notes

    # ERROR handling
    if status == "ERROR":
        # STRICT: no deviations allowed
        if profile == "strict":
            return status, policy_notes

        # OTT: deviations allowed ONLY for tooling + exact condition match
        if (
                module in TOOLING_MODULES and
                error_code in DEVIATION_ELIGIBLE_ERRORS
        ):
            for dev in deviations:
                if dev.get("module") != module:
                    continue

                if dev.get("condition") != error_code:
                    continue

                policy_notes.append(
                    f"Deviation applied: {dev.get('id')}"
                )
                return "NOT_APPLICABLE", policy_notes

        return status, policy_notes

    # Fallback safety
    return status, policy_notes


# -------------------------
# CI Computation (FIXED)
# -------------------------
def compute_ci(modules_effective_status):
    """
    Compute final CI status and exit code.
    Preserves semantic difference between REJECTED and ERROR.
    """
    worst = "PASSED"

    for status in modules_effective_status.values():
        if status == "ERROR":
            return "ERROR", CI_POLICY["ERROR"]

        if status == "REJECTED":
            worst = "REJECTED"

        elif status == "WARNING" and worst == "PASSED":
            worst = "WARNING"

    return worst, CI_POLICY[worst]
