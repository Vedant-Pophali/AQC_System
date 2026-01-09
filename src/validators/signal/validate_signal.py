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
# Signal QC
# -------------------------
def validate_signal(input_path, output_path, mode):
    # -----------------------------------
    # RESOLVE THRESHOLDS (PROFILE-DRIVEN)
    # -----------------------------------
    profile = PROFILES.get(mode, PROFILES[DEFAULT_PROFILE])
    limits = profile["signal"]

    luma_min = limits["luma_min"]
    luma_max = limits["luma_max"]
    chroma_min = limits["chroma_min"]
    chroma_max = limits["chroma_max"]

    duration = get_duration(input_path)

    # Base report (Phase 2.2 contract-complete)
    report = {
        "module": "signal_qc",
        "video_file": input_path,
        "status": "PASSED",
        "metrics": {},
        "events": []
    }

    # -----------------------------------
    # FFmpeg signalstats
    # -----------------------------------
    cmd = [
        "ffmpeg",
        "-v", "info",
        "-i", input_path,
        "-vf", "signalstats",
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
            raise RuntimeError("FFmpeg signalstats execution failed")

        logs = r.stderr or ""

        # -----------------------------------
        # PARSE LUMA / CHROMA RANGE
        # -----------------------------------
        ymins = re.findall(r"YMIN:(\d+)", logs)
        ymaxs = re.findall(r"YMAX:(\d+)", logs)
        umins = re.findall(r"UMIN:(\d+)", logs)
        umaxs = re.findall(r"UMAX:(\d+)", logs)
        vmins = re.findall(r"VMIN:(\d+)", logs)
        vmaxs = re.findall(r"VMAX:(\d+)", logs)

        violation = False

        if ymins and ymaxs:
            ymin = min(map(int, ymins))
            ymax = max(map(int, ymaxs))
            report["metrics"]["luma_min"] = ymin
            report["metrics"]["luma_max"] = ymax

            if ymin < luma_min or ymax > luma_max:
                violation = True

        if umins and umaxs:
            umin = min(map(int, umins))
            umax = max(map(int, umaxs))
            report["metrics"]["chroma_u_min"] = umin
            report["metrics"]["chroma_u_max"] = umax

            if umin < chroma_min or umax > chroma_max:
                violation = True

        if vmins and vmaxs:
            vmin = min(map(int, vmins))
            vmax = max(map(int, vmaxs))
            report["metrics"]["chroma_v_min"] = vmin
            report["metrics"]["chroma_v_max"] = vmax

            if vmin < chroma_min or vmax > chroma_max:
                violation = True

        if violation:
            report["status"] = "REJECTED"

    except Exception as e:
        report["status"] = "ERROR"
        report["events"].append({
            "type": "signal_analysis_error",
            "start_time": 0.0,
            "end_time": duration,
            "details": str(e)
        })

    # -----------------------------------
    # FALLBACK EVENT (MANDATORY)
    # -----------------------------------
    if report["status"] == "REJECTED" and not report["events"]:
        report["events"].append({
            "type": "signal_range_violation",
            "start_time": 0.0,
            "end_time": duration,
            "details": (
                f"Luma/Chroma outside legal range "
                f"(Y:{luma_min}-{luma_max}, "
                f"UV:{chroma_min}-{chroma_max})"
            )
        })

    # HARD CONTRACT SAFETY
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
    parser = argparse.ArgumentParser(description="Video Signal Range QC")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default=DEFAULT_PROFILE)
    args = parser.parse_args()

    validate_signal(
        input_path=args.input,
        output_path=args.output,
        mode=args.mode
    )
