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


def validate_interlace(input_path, output_path, mode):
    # -----------------------------------
    # RESOLVE THRESHOLDS (PROFILE-DRIVEN)
    # -----------------------------------
    profile = PROFILES.get(mode, PROFILES[DEFAULT_PROFILE])
    limits = profile["interlace"]

    max_interlaced_ratio = limits["max_interlaced_ratio"]

    duration = get_duration(input_path)

    report = {
        "module": "interlace_qc",
        "video_file": input_path,
        "status": "PASSED",
        "metrics": {},
        "events": []
    }

    # -----------------------------------
    # FFmpeg idet (interlace detection)
    # -----------------------------------
    cmd = [
        "ffmpeg",
        "-v", "info",
        "-i", input_path,
        "-vf", "idet",
        "-frames:v", "500",
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
            raise RuntimeError("FFmpeg idet failed")

        logs = r.stderr

        # idet summary example:
        # TFF: 120 BFF: 0 Progressive: 380 Undetermined: 0
        m = re.search(
            r"TFF:\s*(\d+)\s+BFF:\s*(\d+)\s+Progressive:\s*(\d+)",
            logs
        )

        if not m:
            raise ValueError("idet output could not be parsed")

        tff = int(m.group(1))
        bff = int(m.group(2))
        prog = int(m.group(3))

        total = tff + bff + prog
        interlaced = tff + bff
        ratio = interlaced / total if total > 0 else 0.0

        report["metrics"] = {
            "tff_frames": tff,
            "bff_frames": bff,
            "progressive_frames": prog,
            "interlaced_ratio": round(ratio, 4)
        }

        if ratio > max_interlaced_ratio:
            report["status"] = "REJECTED"

    except Exception as e:
        report["status"] = "ERROR"
        report["events"].append({
            "type": "interlace_analysis_error",
            "start_time": 0.0,
            "end_time": duration,
            "details": str(e)
        })

    # -----------------------------------
    # FALLBACK EVENT (CONTRACT ENFORCEMENT)
    # -----------------------------------
    if report["status"] != "PASSED" and not report["events"]:
        report["events"].append({
            "type": "interlace_detected",
            "start_time": 0.0,
            "end_time": duration,
            "details": (
                f"Interlaced content detected "
                f"(ratio={report['metrics'].get('interlaced_ratio')}, "
                f"max_allowed={max_interlaced_ratio})"
            )
        })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interlace Detection QC")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default=DEFAULT_PROFILE)
    args = parser.parse_args()

    validate_interlace(
        input_path=args.input,
        output_path=args.output,
        mode=args.mode
    )
