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
    Return media duration in seconds.
    Safe fallback to 0.0 on failure.
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
# Structure QC
# -------------------------
def check_structure(input_path, output_path):
    duration = get_duration(input_path)

    # Base report (Phase 2.2 contract-complete)
    report = {
        "module": "structure_qc",
        "video_file": input_path,
        "status": "PASSED",
        "metrics": {},
        "events": []
    }

    # Minimal container / stream sanity check
    probe = subprocess.run(
        ["ffprobe", "-v", "error", input_path],
        capture_output=True,
        text=True
    )

    if probe.returncode != 0:
        report["status"] = "ERROR"

    # Mandatory event on failure
    if report["status"] != "PASSED":
        report["events"].append({
            "type": "structure_failure",
            "start_time": 0.0,
            "end_time": duration,
            "details": "Container or stream structure invalid"
        })

    # HARD CONTRACT SAFETY (never optional)
    report.setdefault("metrics", {})
    report.setdefault("events", [])

    # Write output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)


# -------------------------
# CLI
# -------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Structure QC")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    check_structure(args.input, args.output)
