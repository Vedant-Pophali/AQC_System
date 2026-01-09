import subprocess
import json
import argparse
import os
import sys

from src.config.threshold_registry import PROFILES, DEFAULT_PROFILE

# UTF-8 safety (Windows)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def get_duration(path):
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


def validate_timestamps(input_path, output_path, mode):
    # -----------------------------------
    # RESOLVE THRESHOLDS (PROFILE-DRIVEN)
    # -----------------------------------
    profile = PROFILES.get(mode, PROFILES[DEFAULT_PROFILE])
    limits = profile["timestamps"]

    allow_non_monotonic = limits["allow_non_monotonic"]

    duration = get_duration(input_path)

    report = {
        "module": "timestamp_qc",
        "video_file": input_path,
        "status": "PASSED",
        "metrics": {},
        "events": []
    }

    # -----------------------------------
    # FFprobe packet inspection
    # -----------------------------------
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_packets",
        "-show_entries", "packet=pts_time,dts_time",
        "-of", "json",
        input_path
    ]

    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        if r.returncode != 0:
            raise RuntimeError("ffprobe packet inspection failed")

        packets = json.loads(r.stdout).get("packets", [])
        if not packets:
            report["status"] = "REJECTED"
            raise ValueError("No packets found for timestamp inspection")

        last_pts = None
        regressions = 0

        for pkt in packets:
            pts = pkt.get("pts_time")
            if pts is None:
                continue

            pts = float(pts)

            if last_pts is not None and pts < last_pts:
                regressions += 1
                if not allow_non_monotonic:
                    report["status"] = "REJECTED"
                    break

            last_pts = pts

        report["metrics"] = {
            "packet_count": len(packets),
            "pts_regressions": regressions,
            "allow_non_monotonic": allow_non_monotonic
        }

        if regressions > 0 and not allow_non_monotonic:
            report["status"] = "REJECTED"

    except Exception as e:
        if report["status"] == "PASSED":
            report["status"] = "ERROR"
        report["events"].append({
            "type": "timestamp_analysis_error",
            "start_time": 0.0,
            "end_time": duration,
            "details": str(e)
        })

    # -----------------------------------
    # FALLBACK EVENT (CONTRACT ENFORCEMENT)
    # -----------------------------------
    if report["status"] != "PASSED" and not report["events"]:
        report["events"].append({
            "type": "timestamp_monotonicity_violation",
            "start_time": 0.0,
            "end_time": duration,
            "details": (
                f"PTS monotonicity violation "
                f"(regressions={report['metrics'].get('pts_regressions')})"
            )
        })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Timestamp Monotonicity QC")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default=DEFAULT_PROFILE)
    args = parser.parse_args()

    validate_timestamps(
        input_path=args.input,
        output_path=args.output,
        mode=args.mode
    )