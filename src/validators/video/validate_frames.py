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


def validate_frames(input_path, output_path, mode):
    # -----------------------------------
    # RESOLVE THRESHOLDS (PROFILE-DRIVEN)
    # -----------------------------------
    profile = PROFILES.get(mode, PROFILES[DEFAULT_PROFILE])
    limits = profile["frames"]

    max_dup = limits["max_duplicate_frames"]
    max_drop = limits["max_dropped_frames"]
    pts_gap = limits["pts_gap_sec"]

    duration = get_duration(input_path)

    report = {
        "module": "frame_qc",
        "video_file": input_path,
        "status": "PASSED",
        "metrics": {},
        "events": []
    }

    # -----------------------------------
    # FFmpeg showinfo (PTS inspection)
    # -----------------------------------
    cmd = [
        "ffmpeg",
        "-v", "info",
        "-i", input_path,
        "-vf", "showinfo",
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

        if r.returncode != 0:
            raise RuntimeError("FFmpeg showinfo failed")

        pts = [float(x) for x in re.findall(r"pts_time:(\d+\.\d+)", r.stderr)]

        report["metrics"]["total_frames"] = len(pts)

        if len(pts) < 2:
            report["status"] = "REJECTED"
            raise ValueError("Insufficient frames detected")

        dup_count = 0
        drop_count = 0

        for i in range(1, len(pts)):
            delta = pts[i] - pts[i - 1]

            if delta == 0.0:
                dup_count += 1
            elif delta > pts_gap:
                drop_count += 1

        report["metrics"]["duplicate_frames"] = dup_count
        report["metrics"]["dropped_frames"] = drop_count
        report["metrics"]["pts_gap_threshold_sec"] = pts_gap

        if dup_count > max_dup or drop_count > max_drop:
            report["status"] = "REJECTED"

    except Exception as e:
        report["status"] = "ERROR"
        report["events"].append({
            "type": "frame_analysis_error",
            "start_time": 0.0,
            "end_time": duration,
            "details": str(e)
        })

    # -----------------------------------
    # FALLBACK EVENT (CONTRACT ENFORCEMENT)
    # -----------------------------------
    if report["status"] != "PASSED" and not report["events"]:
        report["events"].append({
            "type": "frame_integrity_failure",
            "start_time": 0.0,
            "end_time": duration,
            "details": (
                f"Frame continuity violation "
                f"(duplicates={dup_count}, dropped={drop_count}, "
                f"allowed_dup={max_dup}, allowed_drop={max_drop})"
            )
        })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Frame Integrity QC")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default=DEFAULT_PROFILE)
    args = parser.parse_args()

    validate_frames(
        input_path=args.input,
        output_path=args.output,
        mode=args.mode
    )
