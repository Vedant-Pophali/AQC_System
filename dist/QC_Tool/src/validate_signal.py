import sys
import os
import json
import subprocess
import argparse
import re

# 1. Prevent Windows Console Encoding Crashes
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

def load_config(config_path="qc_config.json"):
    """Loads config with fallbacks for safety."""
    defaults = {
        "broadcast_safety": {
            "broadcast_safe_y_min": 16,
            "broadcast_safe_y_max": 235,
            "saturation_max": 240,
            "allowed_outlier_percentage": 0.01
        }
    }
    try:
        if not os.path.exists(config_path):
            candidate = os.path.join(os.path.dirname(os.path.dirname(__file__)), config_path)
            if os.path.exists(candidate):
                config_path = candidate

        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                data = json.load(f)
                if "broadcast_safety" not in data:
                    data["broadcast_safety"] = defaults["broadcast_safety"]
                return data
    except Exception as e:
        print(f"Warning: Config load failed ({e}), using defaults.")

    return defaults

def parse_ffmpeg_output(stream_lines, thresholds):
    """
    Parses FFmpeg metadata output from STDOUT.
    Looks for: lavfi.signalstats.YMIN=...
    """
    y_min_limit = thresholds['broadcast_safe_y_min']
    y_max_limit = thresholds['broadcast_safe_y_max']
    sat_max_limit = thresholds['saturation_max']

    total_frames = 0
    violation_frames = 0

    # Store temporary values for the current frame
    current_frame_stats = {}

    # Regex to capture keys and values like: lavfi.signalstats.YMIN=16
    # We look for lines that contain 'lavfi.signalstats.'

    for line in stream_lines:
        try:
            line_str = line.decode('utf-8', errors='ignore').strip()
        except:
            continue

        if "lavfi.signalstats" in line_str:
            # Extract Key and Value
            # Example: lavfi.signalstats.YMIN=0
            try:
                key, value = line_str.split("=")
                key = key.strip().split(".")[-1] # Get 'YMIN' from 'lavfi.signalstats.YMIN'
                value = int(value.strip())

                current_frame_stats[key] = value

                # Once we have the 3 key metrics, verify the frame
                if "YMIN" in current_frame_stats and "YMAX" in current_frame_stats and "SATMAX" in current_frame_stats:
                    total_frames += 1

                    y_min = current_frame_stats["YMIN"]
                    y_max = current_frame_stats["YMAX"]
                    sat_max = current_frame_stats["SATMAX"]

                    is_unsafe = (y_min < y_min_limit) or (y_max > y_max_limit) or (sat_max > sat_max_limit)
                    if is_unsafe:
                        violation_frames += 1

                    # Reset for next frame
                    current_frame_stats = {}
            except ValueError:
                continue

    return total_frames, violation_frames

def analyze_signal(video_path, output_path, config):
    thresholds = config["broadcast_safety"]

    # UPDATED COMMAND: We chain 'metadata=print' to force output to stdout
    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vf", "signalstats,metadata=print:file=-", # critical change
        "-f", "null",
        "-"
    ]

    print(f"Starting Signal Analysis on: {video_path}")

    try:
        # We now capture STDOUT because that's where metadata=print sends data
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL # We ignore the logs now
        )

        total_frames, violations = parse_ffmpeg_output(process.stdout, thresholds)

        process.wait()

        if total_frames == 0:
            # If strictly 0 frames found, check if input exists
            if not os.path.exists(video_path):
                raise ValueError(f"Input file not found: {video_path}")
            else:
                # It might be a very short file or parsing failed
                raise ValueError("No frame data parsed. FFmpeg output format might differ.")

        violation_ratio = violations / total_frames
        allowed_ratio = thresholds['allowed_outlier_percentage']

        status = "PASSED" if violation_ratio <= allowed_ratio else "REJECTED"

        report = {
            "module": "signal_qc",
            "status": status,
            "metrics": {
                "analyzed_frames": total_frames,
                "violation_frames": violations,
                "violation_percentage": round(violation_ratio * 100, 2),
                "thresholds_used": thresholds
            },
            "events": []
        }

        if status == "REJECTED":
            report["events"].append({
                "type": "Broadcast Violation",
                "error": "Signal Out of Bounds",
                "details": f"Video exceeds safety limits in {report['metrics']['violation_percentage']}% of frames.",
                "start_time": 0,
                "end_time": None
            })

    except Exception as e:
        report = {
            "module": "signal_qc",
            "status": "ERROR",
            "error_details": str(e)
        }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=4)
    print(f"Signal QC Completed. Status: {report['status']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    cfg = load_config()
    analyze_signal(args.input, args.output, cfg)