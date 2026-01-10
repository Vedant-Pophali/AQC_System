import argparse
import json
import subprocess
import re
import sys
from pathlib import Path

def scan_bitstream(input_path):
    """
    2.1 Frame Continuity Scan
    Runs a fast 'null' decode. If FFmpeg encounters PTS/DTS errors 
    or dropped frames, it screams into stderr. We capture that.
    """
    cmd = [
        "ffmpeg",
        "-v", "info",          # Need info/warning level to catch drops
        "-i", str(input_path),
        "-f", "null",
        "-"
    ]
    
    # We use 'replace' for errors to avoid crashing on binary garbage output
    try:
        process = subprocess.run(
            cmd, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.PIPE, 
            text=True, 
            encoding="utf-8", 
            errors="replace"
        )
        return process.stderr
    except Exception as e:
        return str(e)

def parse_errors(log_text):
    events = []
    
    # Regex library for Section 2.1 Defects
    patterns = {
        "non_monotonic_dts": r"DTS .* < .*",
        "non_monotonic_pts": r"PTS .* < .*",
        "timestamp_discontinuity": r"Timestamp discontinuity",
        "buffer_underflow": r"buffer underflow",
        "corrupt_packet": r"corrupt decoded frame",
        "invalid_nal_unit": r"Invalid NAL unit",
        "dropped_frame": r"drop="  # FFmpeg summary line usually has drop=N
    }

    # 1. Check for specific line errors
    for line in log_text.split('\n'):
        # Extract timestamp if present (e.g., "time=00:01:23.45")
        time_match = re.search(r"time=(\d{2}:\d{2}:\d{2}\.\d+)", line)
        t_sec = 0.0
        if time_match:
            # Convert HH:MM:SS to seconds
            h, m, s = time_match.group(1).split(':')
            t_sec = float(h)*3600 + float(m)*60 + float(s)

        for err_type, regex in patterns.items():
            if re.search(regex, line, re.IGNORECASE):
                # Avoid flooding report with thousands of similar errors
                # Limit to first 10 per type or handle aggregation
                if len([e for e in events if e["type"] == err_type]) < 10:
                    events.append({
                        "type": err_type,
                        "details": line.strip()[:150], # Truncate long logs
                        "start_time": t_sec,
                        "end_time": t_sec
                    })

    # 2. Check Summary for Dropped Frames (The "drop=" stat)
    # FFmpeg summary: "frame= 100 fps=0.0 q=-0.0 size=N/A time=00:00:05.00 bitrate=N/A speed=10x drop=5"
    drop_match = re.search(r"drop=(\d+)", log_text)
    if drop_match:
        drop_count = int(drop_match.group(1))
        if drop_count > 0:
            events.append({
                "type": "dropped_frame_summary",
                "details": f"Total frames dropped during decode: {drop_count}. Possible performance issue or corrupt stream.",
                "start_time": 0,
                "end_time": 0
            })

    return events

def run_validator(input_path, output_path, mode="strict"):
    input_path = Path(input_path)
    report = {
        "module": "validate_frames",
        "status": "PASSED",
        "events": []
    }

    if not input_path.exists():
        report["status"] = "CRASHED"
        with open(output_path, "w") as f:
            json.dump(report, f)
        return

    # Execute
    log_data = scan_bitstream(input_path)
    events = parse_errors(log_data)
    
    report["events"] = events
    
    # Severity Logic
    if events:
        report["status"] = "REJECTED" # Structural errors are usually fatal
        if all(e["type"] == "dropped_frame_summary" for e in events):
             # Drops might just be warnings, but PTS/DTS are fatal
             pass 

    with open(output_path, "w") as f:
        json.dump(report, f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default="strict")
    args = parser.parse_args()
    
    run_validator(args.input, args.output, args.mode)