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


def validate_loudness(input_path, output_path, mode):
    # -----------------------------------
    # RESOLVE THRESHOLDS (PROFILE-DRIVEN)
    # -----------------------------------
    profile = PROFILES.get(mode, PROFILES[DEFAULT_PROFILE])
    limits = profile["loudness"]

    target_lufs = limits["target_lufs"]
    lufs_tolerance = limits["lufs_tolerance"]
    true_peak_max = limits["true_peak_max"]
    lra_max = limits["lra_max"]

    # -----------------------------------
    # FFmpeg loudnorm command
    # -----------------------------------
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-af",
        f"loudnorm=I={target_lufs}:TP={true_peak_max}:LRA={lra_max}:print_format=json",
        "-f", "null",
        "-"
    ]

    report = {
        "module": "audio_qc",
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
        start = logs.rfind("{")
        end = logs.rfind("}") + 1
        if start == -1 or end == -1:
            raise ValueError("Failed to parse loudnorm JSON output")

        data = json.loads(logs[start:end])

        integrated_lufs = float(data.get("input_i"))
        true_peak = float(data.get("input_tp"))
        lra = float(data.get("input_lra", 0.0))

        report["metrics"] = {
            "integrated_lufs": integrated_lufs,
            "true_peak_db": true_peak,
            "lra": lra,
            "profile": mode
        }

        # -----------------------------------
        # QC DECISION (PROFILE-DRIVEN)
        # -----------------------------------
        if abs(integrated_lufs - target_lufs) > lufs_tolerance:
            report["status"] = "REJECTED"
        elif true_peak > true_peak_max:
            report["status"] = "WARNING"

    except Exception as e:
        report["status"] = "ERROR"
        report["events"].append({
            "type": "loudness_analysis_error",
            "start_time": 0.0,
            "end_time": duration,
            "details": str(e)
        })

    # -----------------------------------
    # FALLBACK EVENT (CONTRACT ENFORCEMENT)
    # -----------------------------------
    if report["status"] != "PASSED" and not report["events"]:
        report["events"].append({
            "type": "loudness_failure",
            "start_time": 0.0,
            "end_time": duration,
            "details": (
                f"Loudness out of range: "
                f"target={target_lufs} LUFS ±{lufs_tolerance}, "
                f"TP≤{true_peak_max} dB"
            )
        })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audio Loudness QC")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default=DEFAULT_PROFILE)
    args = parser.parse_args()

    validate_loudness(
        input_path=args.input,
        output_path=args.output,
        mode=args.mode
    )
