# src/schema/qc_schema.py

# -------------------------
# Allowed status enums
# -------------------------
STATUS_ENUM = {
    "PASSED",
    "WARNING",
    "REJECTED",
    "ERROR"
}

# -------------------------
# Required keys + types per module
# -------------------------
BASE_MODULE_SCHEMA = {
    "module": str,
    "video_file": str,
    "status": str,
    "metrics": dict,
    "events": list
}

# -------------------------
# Known module registry
# -------------------------
KNOWN_MODULES = {
    "structure_qc",
    "frame_qc",
    "timestamp_qc",
    "avsync_qc",
    "black_freeze_qc",
    "gop_qc",
    "audio_qc",
    "audio_signal_qc",
    "signal_qc",
    "interlace_qc",
    "qctools_qc",
    "artifact_qc"
}

# -------------------------
# Known deviation schema
# -------------------------
KNOWN_DEVIATION_SCHEMA = {
    "id": str,
    "module": str,
    "condition": str,
    "scope": str,
    "justification": str,
    "approved_by": str,
    "created_on": str,
    "expires_on": str
}

# -------------------------
# Master report schema
# -------------------------
MASTER_SCHEMA = {
    "metadata": dict,
    "overall_status": str,
    "modules": dict,
    # Optional, but validated if present
    "known_deviations": list
}

def validate_validator_output(report: dict):
    """
    Hard validator contract enforcement.

    Rules:
    - status must be valid
    - required keys must exist
    - if status != PASSED => events must be non-empty
    """

    required_keys = {"module", "video_file", "status", "metrics", "events"}

    missing = required_keys - report.keys()
    if missing:
        raise ValueError(
            f"Validator output missing required keys: {missing}"
        )

    status = report.get("status")
    events = report.get("events")

    if status not in STATUS_ENUM:
        raise ValueError(f"Invalid validator status: {status}")

    if status != "PASSED" and not events:
        raise ValueError(
            f"Validator '{report.get('module')}' violated contract: "
            f"status={status} but no events emitted"
        )

    return True
