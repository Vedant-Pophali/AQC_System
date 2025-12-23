import subprocess
import json
import argparse
import os
import sys
import re

def check_audio_signal(input_path, output_path):
    print(f"[INFO] Audio Signal QC: Deep scanning {os.path.basename(input_path)}...")

    # We use two filters:
    # 1. astats: Measures DC offset and Peak levels (Distortion)
    # 2. aphasemeter: Measures stereo phase correlation (Video=0 disables visual output)
    cmd = [
        "ffmpeg",
        "-v", "info",       # We need INFO level to see the stats
        "-i", input_path,
        "-af", "astats=metadata=1:reset=1,aphasemeter=video=0",
        "-f", "null",
        "-"
    ]

    report = {
        "module": "audio_signal_qc",
        "video_file": input_path,
        "status": "PASSED",
        "events": [],
        "metrics": {}
    }

    try:
        # Run FFmpeg and capture STDERR (where stats are printed)
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        logs = result.stderr

        # --- 1. PARSE ASTATS (Distortion/DC Offset) ---
        # Look for "DC offset: 0.000001" type lines
        dc_offsets = re.findall(r"DC offset:\s+([0-9\.\-]+)", logs)
        if dc_offsets:
            # Convert to floats and take the max absolute value
            max_dc = max([abs(float(x)) for x in dc_offsets])
            report["metrics"]["max_dc_offset"] = max_dc

            # Paper Criterion: Significant DC offset is a defect
            if max_dc > 0.01: # Threshold for "Bad" DC Offset
                report["status"] = "REJECTED"
                report["events"].append({
                    "type": "Signal Defect",
                    "details": f"High DC Offset detected: {max_dc} (Limit: 0.01)"
                })

        # --- 2. PARSE PHASE (aphasemeter) ---
        # FFmpeg prints "Phase: 0.9" periodically. We scan for negative values.
        # Note: Parsing CLI phase logs is tricky; here we look for final summary or warnings.
        # For this 'Low Difficulty' implementation, we use a Regex to spot check "out of phase" warnings
        # or low correlation if FFmpeg summarizes it.
        # (Standard FFmpeg doesn't always summarize Phase without extra tools,
        # so we check for 'Peak level' clipping from astats as a proxy for Distortion [cite: 155])

        # Check for Clipping (Distortion)
        # If Peak level is 0.0 dB (or very close), it might be clipped.
        peak_levels = re.findall(r"Peak level dB:\s+([0-9\.\-]+)", logs)
        if peak_levels:
            max_peak = max([float(x) for x in peak_levels])
            report["metrics"]["max_peak_db"] = max_peak

            if max_peak >= 0.0:
                report["status"] = "REJECTED"
                report["events"].append({
                    "type": "Audio Distortion",
                    "details": f"Clipping Detected. Peak Level: {max_peak} dB"
                })

    except Exception as e:
        print(f"[ERROR] Audio Signal QC Failed: {e}")
        report["status"] = "ERROR"
        report["events"].append({"error": str(e)})

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding='utf-8') as f:
        json.dump(report, f, indent=4)
    print(f"[OK] Saved: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    check_audio_signal(args.input, args.output)