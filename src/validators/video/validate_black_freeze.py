import argparse
import json
import subprocess
import sys
import os
from pathlib import Path

def detect_black_freeze(input_path, duration_sec):
    """
    Detects Black frames and Freezes.
    Smart Logic: Ignores Black frames at strict start/end (Fades).
    """
    # 1. Black Detect: black_min_duration=2.0 (ignores flash frames)
    # 2. Freeze Detect: noise=-60dB (ignores grain), duration=2.0
    cmd = [
        "ffmpeg",
        "-v", "info",
        "-i", str(input_path),
        "-vf", "blackdetect=d=2.0:pix_th=0.10,freezedetect=n=-60dB:d=2.0",
        "-f", "null",
        "-"
    ]
    
    events = []
    try:
        process = subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, 
            text=True, encoding="utf-8", errors="replace"
        )
        log = process.stderr
        
        # Parse FFmpeg Log
        for line in log.split('\n'):
            # --- BLACK DETECT ---
            if "black_start" in line:
                # Format: black_start:12.5 black_end:15.5 black_duration:3.0
                parts = line.split()
                start = float(parts[3].split(':')[1])
                end = float(parts[4].split(':')[1])
                dur = float(parts[5].split(':')[1])
                
                # Fade Exclusion Logic
                # If black starts at 0.0 -> Fade In
                # If black ends near total duration -> Fade Out
                if start < 1.0:
                    ev_type = "fade_in"
                    desc = "Intentional Fade-In detected."
                elif end > (duration_sec - 1.0):
                    ev_type = "fade_out"
                    desc = "Intentional Fade-Out detected."
                else:
                    ev_type = "black_frame_error"
                    desc = f"Unexpected Black Screen for {dur}s."

                events.append({
                    "type": ev_type,
                    "details": desc,
                    "start_time": start,
                    "end_time": end
                })

            # --- FREEZE DETECT ---
            if "lavfi.freezedetect.freeze_start" in line:
                start = float(line.split(": ")[1])
                events.append({"type": "freeze_start", "time": start})
            if "lavfi.freezedetect.freeze_end" in line:
                end = float(line.split(": ")[1])
                # Find matching start
                for e in reversed(events):
                    if e.get("type") == "freeze_start" and "end_time" not in e:
                        e["type"] = "video_freeze"
                        e["start_time"] = e["time"]
                        e["end_time"] = end
                        e["details"] = f"Video Freeze detected for {round(end - e['time'], 2)}s."
                        del e["time"]
                        break

    except Exception as e:
        return []

    return [e for e in events if "time" not in e] # Clean up temp objects

def run_validator(input_path, output_path, mode="strict"):
    # Get Duration first for Fade Logic
    probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(input_path)]
    try:
        dur_str = subprocess.check_output(probe_cmd, text=True).strip()
        total_duration = float(dur_str)
    except:
        total_duration = 0.0

    events = detect_black_freeze(input_path, total_duration)
    
    # Filter: Strict mode rejects freezes, but allows fades
    status = "PASSED"
    for e in events:
        if e["type"] in ["video_freeze", "black_frame_error"]:
            status = "REJECTED"
    
    report = {
        "module": "validate_black_freeze",
        "status": status,
        "details": {
            "events": events
        }
    }
    
    with open(output_path, "w") as f:
        json.dump(report, f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default="strict")
    args = parser.parse_args()
    run_validator(args.input, args.output, args.mode)