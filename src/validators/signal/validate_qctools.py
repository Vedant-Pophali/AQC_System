import subprocess
import json
import argparse
import os
import sys

# UTF-8 safety (Windows)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# -------------------------
# Utilities
# -------------------------
def get_duration(path):
    """
    Best-effort duration probe.
    Failure returns 0.0 (policy-safe).
    """
    try:
        p = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                path
            ],
            capture_output=True,
            text=True
        )
        return float(json.loads(p.stdout)["format"]["duration"])
    except Exception:
        return 0.0


# -------------------------
# Validator
# -------------------------
def validate_qctools(input_path, output_path):
    """
    QCTools availability validator.

    Contract:
    - PASSED  → qctools executes successfully
    - ERROR   → qctools missing or execution failure
    - No policy decisions here
    """

    duration = get_duration(input_path)

    # Base report (Phase 2.2 contract-complete)
    report = {
        "module": "qctools_qc",
        "video_file": input_path,
        "status": "PASSED",
        "error_code": None,
        "metrics": {},
        "events": []
    }

    # -------------------------
    # QCTools invocation
    # -------------------------
    try:
        result = subprocess.run(
            ["qcli", "-i", input_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        report["metrics"]["qctools_exit_code"] = result.returncode

        if result.returncode != 0:
            report["status"] = "ERROR"
            report["error_code"] = "QCTOOLS_EXECUTION_FAILED"

    except FileNotFoundError:
        report["status"] = "ERROR"
        report["error_code"] = "QCTOOLS_UNAVAILABLE"
        report["metrics"]["qctools_exit_code"] = None

    except Exception as e:
        report["status"] = "ERROR"
        report["error_code"] = "QCTOOLS_RUNTIME_ERROR"
        report["metrics"]["qctools_exit_code"] = None
        report["events"].append({
            "type": "qctools_runtime_error",
            "start_time": 0.0,
            "end_time": duration,
            "details": str(e)
        })

    # -------------------------
    # Mandatory event on ERROR
    # -------------------------
    if report["status"] == "ERROR" and not report["events"]:
        report["events"].append({
            "type": "qctools_unavailable",
            "start_time": 0.0,
            "end_time": duration,
            "details": "QCTools not available or failed to execute"
        })

    # HARD CONTRACT SAFETY (never optional)
    report.setdefault("metrics", {})
    report.setdefault("events", [])

    # -------------------------
    # Emit report
    # -------------------------
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)


# -------------------------
# CLI
# -------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QCTools Availability Validator")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    validate_qctools(
        input_path=args.input,
        output_path=args.output
    )
