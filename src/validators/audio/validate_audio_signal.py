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


def validate_audio_signal(input_path, output_path, mode):
    # -----------------------------------
    # RESOLVE THRESHOLDS (PROFILE-DRIVEN)
    # -----------------------------------
    profile = PROFILES.get(mode, PROFILES[DEFAULT_PROFILE])
    limits = profile["audio_signal"]

    max_dc_offset = limits["max_dc_offset"]
    max_clipping_ratio = limits["max_clipping_ratio"]

    # -----------------------------------
    # FFmpeg command
    # -----------------------------------
    cmd = [
        "ffmpeg",
        "-v", "info",
        "-i", input_path,
        "-af", "astats=metadata=1:reset=1,aphasemeter=video=0",
        "-f", "null",
        "-"
    ]

    report = {
        "module": "audio_signal_qc",
        "video_file": input_path,
        "status": "PASSED",
        "metrics": {},
        "events": []
    }

    duration = get_duration(input_path)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        logs = result.stderr

        # -----------------------------------
        # DC OFFSET (ASTATS)
        # -----------------------------------
        dc_offsets = re.findall(r"DC offset:\s+([0-9\.\-]+)", logs)
        if dc_offsets:
            dc_vals = [abs(float(x)) for x in dc_offsets]
            max_dc = max(dc_vals)
            report["metrics"]["max_dc_offset"] = max_dc

            if max_dc > max_dc_offset:
                report["status"] = "REJECTED"

        # -----------------------------------
        # CLIPPING / DISTORTION (ASTATS)
        # -----------------------------------
        peak_levels = re.findall(r"Peak level dB:\s+([0-9\.\-]+)", logs)
        if peak_levels:
            peak_vals = [float(x) for x in peak_levels]
            max_peak = max(peak_vals)
            report["metrics"]["max_peak_db"] = max_peak

            # Peak at or above 0 dBFS implies clipping
            if max_peak >= 0.0:
                report["status"] = "REJECTED"

        # Optional metric: proportion of clipped frames (best-effort)
        if peak_levels:
            clipped = sum(1 for x in peak_levels if float(x) >= 0.0)
            clip_ratio = clipped / max(len(peak_levels), 1)
            report["metrics"]["clipping_ratio"] = round(clip_ratio, 4)

            if clip_ratio > max_clipping_ratio:
                report["status"] = "REJECTED"

    except Exception as e:
        report["status"] = "ERROR"
        report["events"].append({
            "type": "audio_signal_analysis_error",
            "start_time": 0.0,
            "end_time": duration,
            "details": str(e)
        })

    # -----------------------------------
    # FALLBACK EVENT (CONTRACT ENFORCEMENT)
    # -----------------------------------
    if report["status"] != "PASSED" and not report["events"]:
        report["events"].append({
            "type": "audio_signal_failure",
            "start_time": 0.0,
            "end_time": duration,
            "details": (
                f"Audio signal defect detected "
                f"(max_dc_offset={report['metrics'].get('max_dc_offset')}, "
                f"max_peak_db={report['metrics'].get('max_peak_db')})"
            )
        })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audio Signal QC")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default=DEFAULT_PROFILE)
    args = parser.parse_args()

    validate_audio_signal(
        input_path=args.input,
        output_path=args.output,
        mode=args.mode
    )
