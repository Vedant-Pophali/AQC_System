import subprocess
import json
import argparse
import os
import sys
import re

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


def validate_black_freeze(input_path, output_path, mode):
    # -----------------------------------
    # PROFILE-DRIVEN THRESHOLDS
    # -----------------------------------
    profile = PROFILES.get(mode, PROFILES[DEFAULT_PROFILE])
    limits = profile["black_freeze"]

    min_black_dur = limits["min_black_duration_sec"]
    min_freeze_dur = limits["min_freeze_duration_sec"]
    pix_th = limits["black_pixel_threshold"]

    duration = get_duration(input_path)

    report = {
        "module": "black_freeze_qc",
        "video_file": input_path,
        "status": "PASSED",
        "metrics": {
            "min_black_duration_sec": min_black_dur,
            "min_freeze_duration_sec": min_freeze_dur,
            "black_pixel_threshold": pix_th,
            "profile": mode
        },
        "events": []
    }

    # -----------------------------------
    # SINGLE FFmpeg PASS
    # -----------------------------------
    cmd = [
        "ffmpeg",
        "-v", "info",
        "-i", input_path,
        "-vf",
        (
            f"blackdetect=d={min_black_dur}:pix_th={pix_th},"
            f"freezedetect=n=0.01:d={min_freeze_dur}"
        ),
        "-f", "null",
        "-"
    ]

    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        stderr = r.stderr

        # -----------------------------
        # Parse black segments
        # -----------------------------
        for m in re.finditer(
                r"black_start:(\d+(\.\d+)?)\s+black_end:(\d+(\.\d+)?)",
                stderr
        ):
            start = float(m.group(1))
            end = float(m.group(3))
            report["events"].append({
                "type": "Black Segment",
                "start_time": start,
                "end_time": end,
                "details": "Black video segment detected"
            })

        # -----------------------------
        # Parse freeze segments
        # -----------------------------
        for m in re.finditer(
                r"freeze_start:(\d+(\.\d+)?)\s+freeze_end:(\d+(\.\d+)?)",
                stderr
        ):
            start = float(m.group(1))
            end = float(m.group(3))
            report["events"].append({
                "type": "Frozen Segment",
                "start_time": start,
                "end_time": end,
                "details": "Frozen video segment detected"
            })

        if report["events"]:
            report["status"] = "REJECTED"

    except Exception as e:
        report["status"] = "ERROR"
        report["events"].append({
            "type": "black_freeze_analysis_error",
            "start_time": 0.0,
            "end_time": duration,
            "details": str(e)
        })

    # -----------------------------------
    # CONTRACT FALLBACK (NON-NEGOTIABLE)
    # -----------------------------------
    if report["status"] != "PASSED" and not report["events"]:
        report["events"].append({
            "type": "black_freeze_failure",
            "start_time": 0.0,
            "end_time": duration,
            "details": (
                "Black or freeze condition detected "
                f"(black≥{min_black_dur}s, freeze≥{min_freeze_dur}s)"
            )
        })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Black / Freeze QC")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default=DEFAULT_PROFILE)
    args = parser.parse_args()

    validate_black_freeze(
        input_path=args.input,
        output_path=args.output,
        mode=args.mode
    )
