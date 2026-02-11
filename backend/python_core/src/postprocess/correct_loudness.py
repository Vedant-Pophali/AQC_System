import subprocess
import json
import argparse
import os
import sys
from pathlib import Path

# UTF-8 safety (Windows)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# -------------------------
# CONSTANTS
# -------------------------
# Default targets from EBU R.128 / Research Source [146, 216]
TARGET_I = -23.0
TARGET_TP = -1.0
TARGET_LRA = 7.0  # Standard broadcast range

def measure_loudness(input_path):
    """
    PASS 1: Measurement
    Runs the loudnorm filter in print_format=json mode to extract
    integrated loudness (I), True Peak (TP), LRA, and Thresholds.
    """
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-af", f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:print_format=json",
        "-f", "null",
        "-"
    ]

    print(f" [INFO] Pass 1: Measuring '{Path(input_path).name}'...")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        # FFmpeg loudnorm writes JSON to stderr
        logs = result.stderr

        # Extract JSON block
        start = logs.rfind("{")
        end = logs.rfind("}") + 1
        if start == -1 or end == -1:
            raise ValueError("Could not find loudnorm JSON output in stderr")

        data = json.loads(logs[start:end])
        return data

    except Exception as e:
        print(f" [ERROR] Measurement failed: {e}")
        return None

def apply_correction(input_path, output_path, measured_stats):
    """
    PASS 2: Normalization
    Feeds the measured stats back into loudnorm for precise linear correction.
    """
    # Extract measured values
    # Note: 'input_i', 'input_tp', etc. come from the JSON output of Pass 1
    measured_i = measured_stats.get("input_i")
    measured_tp = measured_stats.get("input_tp")
    measured_lra = measured_stats.get("input_lra")
    measured_thresh = measured_stats.get("input_thresh")

    # Construct filter string with measured values
    # linear=true ensures cleaner processing without dynamic compression artifacts if possible
    filter_str = (
        f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:"
        f"measured_I={measured_i}:measured_TP={measured_tp}:"
        f"measured_LRA={measured_lra}:measured_thresh={measured_thresh}:"
        "linear=true:print_format=summary"
    )

    cmd = [
        "ffmpeg",
        "-y",               # Overwrite output
        "-i", input_path,
        "-af", filter_str,
        "-c:v", "copy",     # Copy video stream (don't re-encode video)
        "-c:a", "aac",      # Re-encode audio (required for filter)
        "-b:a", "192k",     # Standard bitrate
        output_path
    ]

    print(f" [INFO] Pass 2: Normalizing to {output_path}...")
    try:
        subprocess.run(cmd, check=True)
        print(" [SUCCESS] Normalization complete.")
        return True
    except subprocess.CalledProcessError as e:
        print(f" [ERROR] Normalization failed: {e}")
        return False

def correct_loudness_workflow(input_path, output_path):
    # 1. Measure
    stats = measure_loudness(input_path)
    if not stats:
        sys.exit(1)

    print(f"    Measured I: {stats.get('input_i')} LUFS")
    print(f"    Measured TP: {stats.get('input_tp')} dBTP")

    # 2. Correct
    success = apply_correction(input_path, output_path, stats)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EBU R.128 2-Pass Loudness Correction")
    parser.add_argument("--input", required=True, help="Input video file")
    parser.add_argument("--output", required=True, help="Output normalized video file")

    args = parser.parse_args()

    correct_loudness_workflow(args.input, args.output)