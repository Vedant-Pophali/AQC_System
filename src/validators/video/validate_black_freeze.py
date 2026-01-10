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
    # CONFIGURATION
    # -----------------------------------
    profile = PROFILES.get(mode, PROFILES[DEFAULT_PROFILE])

    # Black Detect Params [Source: 121]
    # pic_th: ratio of pixels that must be black (0.98 = 98%)
    # pix_th: brightness threshold for "black" (0.03 ~ 0.05)
    # duration: min duration to flag (2.0s to avoid flash cuts)
    bd_params = profile.get("visual_qc", {})
    bd_pic_th = bd_params.get("black_pixel_coverage", 0.98)
    bd_pix_th = bd_params.get("black_frame_threshold", 0.03)
    bd_min_dur = bd_params.get("min_black_duration", 2.0)

    # Freeze Detect Params
    # noise: tolerance for noise in "static" scenes (e.g. -60dB)
    # duration: min freeze duration to flag (e.g. 2.0s)
    fd_params = profile.get("freeze_qc", {})
    fd_noise = fd_params.get("noise_tolerance", -60) # dB
    fd_min_dur = fd_params.get("min_freeze_duration", 2.0)

    duration = get_duration(input_path)

    report = {
        "module": "black_freeze_qc",
        "video_file": input_path,
        "status": "PASSED",
        "metrics": {
            "black_events": 0,
            "freeze_events": 0
        },
        "events": []
    }

    # -----------------------------------
    # FFmpeg Filter Execution
    # -----------------------------------
    # We combine blackdetect and freezedetect in one pass
    # blackdetect output: black_start:X black_end:Y black_duration:Z
    # freezedetect output: lavfi.freezedetect.freeze_start: X

    filter_chain = (
        f"blackdetect=d={bd_min_dur}:pic_th={bd_pic_th}:pix_th={bd_pix_th},"
        f"freezedetect=n={fd_noise}dB:d={fd_min_dur}"
    )

    cmd = [
        "ffmpeg",
        "-v", "info", # Info level needed for blackdetect/freezedetect logs
        "-i", input_path,
        "-vf", filter_chain,
        "-f", "null",
        "-"
    ]

    try:
        # These filters write to stderr/stdout depending on version, usually stderr
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        logs = result.stderr + result.stdout

        # -----------------------------------
        # Parse Black Detect
        # -----------------------------------
        # Log line: "black_start:12.5 black_end:14.0 black_duration:1.5"
        black_matches = re.findall(
            r"black_start:([0-9\.]+)\s+black_end:([0-9\.]+)\s+black_duration:([0-9\.]+)",
            logs
        )

        for start, end, dur in black_matches:
            report["events"].append({
                "type": "visual_defect",
                "subtype": "black_frame_sequence",
                "start_time": float(start),
                "end_time": float(end),
                "details": f"Black screen detected for {dur}s (Threshold: {bd_min_dur}s)"
            })
            report["status"] = "REJECTED"

        report["metrics"]["black_events"] = len(black_matches)

        # -----------------------------------
        # Parse Freeze Detect
        # -----------------------------------
        # Log line: "lavfi.freezedetect.freeze_start: 12.0"
        # Freeze detect logs start/end/duration usually as metadata or separate lines
        # "freeze_start: 10.5" ... "freeze_end: 15.5" ... "freeze_duration: 5.0"

        # We look for pairs or duration lines.
        # Simpler approach: regex for duration line which usually comes at end of event
        freeze_matches = re.findall(
            r"freeze_start:\s*([0-9\.]+)",
            logs
        )
        freeze_ends = re.findall(
            r"freeze_end:\s*([0-9\.]+)",
            logs
        )
        freeze_durs = re.findall(
            r"freeze_duration:\s*([0-9\.]+)",
            logs
        )

        # Zip logic can be tricky if logs are interleaved, but usually sequential.
        # We map based on count.
        count = min(len(freeze_matches), len(freeze_ends), len(freeze_durs))

        for i in range(count):
            start = float(freeze_matches[i])
            end = float(freeze_ends[i])
            dur = float(freeze_durs[i])

            report["events"].append({
                "type": "visual_defect",
                "subtype": "freeze_frame",
                "start_time": start,
                "end_time": end,
                "details": f"Video freeze detected for {dur}s (Threshold: {fd_min_dur}s)"
            })
            report["status"] = "REJECTED"

        report["metrics"]["freeze_events"] = count

    except Exception as e:
        report["status"] = "ERROR"
        report["events"].append({
            "type": "black_freeze_analysis_error",
            "start_time": 0.0,
            "end_time": duration,
            "details": str(e)
        })

    _write(report, output_path)

def _write(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Black & Freeze Frame QC")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default=DEFAULT_PROFILE)
    args = parser.parse_args()

    validate_black_freeze(
        input_path=args.input,
        output_path=args.output,
        mode=args.mode
    )