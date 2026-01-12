import argparse
import json
import subprocess
import re
import cv2
import numpy as np
from pathlib import Path

# Config
DUPLICATE_THRESHOLD = 1.0  # Pixel diff sum (extremely low = duplicate)

def scan_bitstream(input_path):
    """
    2.1 Frame Continuity Scan (Fast)
    Parses FFmpeg stderr for PTS/DTS errors and packet drops.
    """
    cmd = [
        "ffmpeg", "-v", "info", "-i", str(input_path), "-f", "null", "-"
    ]
    try:
        process = subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, 
            text=True, encoding="utf-8", errors="replace"
        )
        return process.stderr
    except Exception as e:
        return str(e)

def parse_ffmpeg_errors(log_text):
    events = []
    patterns = {
        "non_monotonic_dts": r"DTS .* < .*",
        "non_monotonic_pts": r"PTS .* < .*",
        "timestamp_discontinuity": r"Timestamp discontinuity",
        "corrupt_packet": r"corrupt decoded frame",
    }

    for line in log_text.split('\n'):
        # Extract time
        time_match = re.search(r"time=(\d{2}:\d{2}:\d{2}\.\d+)", line)
        t_sec = 0.0
        if time_match:
            h, m, s = time_match.group(1).split(':')
            t_sec = float(h)*3600 + float(m)*60 + float(s)

        for err_type, regex in patterns.items():
            if re.search(regex, line, re.IGNORECASE):
                if len([e for e in events if e["type"] == err_type]) < 10:
                    events.append({
                        "type": err_type,
                        "details": line.strip()[:100],
                        "start_time": t_sec,
                        "end_time": t_sec
                    })
    return events

def scan_duplicates(input_path):
    """
    2.1 Visual Duplicate Frame Detection (Slow)
    Uses OpenCV to compare consecutive frames.
    """
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        return [], 0

    events = []
    prev_frame = None
    frame_idx = 0
    duplicate_count = 0
    
    # Optimization: Check every Nth frame? No, duplicates must be consecutive.
    # Optimization: Resize frame to tiny thumbnail for diffing.
    
    in_dup_seq = False
    seq_start_sec = 0.0
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        current_time = frame_idx / fps

        if prev_frame is not None:
            # Resize for speed (64x64 is enough)
            curr_small = cv2.resize(frame, (64, 64))
            prev_small = cv2.resize(prev_frame, (64, 64))
            
            # Simple absolute difference
            diff = cv2.absdiff(curr_small, prev_small)
            non_zero_count = np.count_nonzero(diff)
            
            # If pixels are basically identical
            is_dup = (non_zero_count < 50) # Strict threshold

            if is_dup:
                duplicate_count += 1
                if not in_dup_seq:
                    in_dup_seq = True
                    seq_start_sec = current_time
            else:
                if in_dup_seq:
                    in_dup_seq = False
                    duration = current_time - seq_start_sec
                    # Only report if frozen for more than 2 frames
                    if duration > (2/fps):
                        events.append({
                            "type": "freeze_frame",
                            "details": f"Content frozen for {duration:.2f}s",
                            "start_time": seq_start_sec,
                            "end_time": current_time
                        })

        prev_frame = frame
        frame_idx += 1

    cap.release()
    return events, duplicate_count

def run_validator(input_path, output_path, mode="strict"):
    report = {
        "module": "validate_frames",
        "status": "PASSED",
        "events": []
    }

    # 1. Bitstream Scan (PTS/DTS)
    log_data = scan_bitstream(input_path)
    bitstream_events = parse_ffmpeg_errors(log_data)
    report["events"].extend(bitstream_events)

    # 2. Visual Scan (Duplicates)
    # Only run visual scan if bitstream didn't crash
    visual_events, dup_count = scan_duplicates(input_path)
    report["events"].extend(visual_events)
    
    report["metrics"] = {"duplicate_frame_count": dup_count}

    # Severity Logic
    if any(e["type"] in ["non_monotonic_pts", "corrupt_packet"] for e in report["events"]):
        report["status"] = "REJECTED"
    elif report["metrics"]["duplicate_frame_count"] > 24: # >1 sec of duplicates total
        report["status"] = "WARNING"

    with open(output_path, "w") as f:
        json.dump(report, f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default="strict")
    args = parser.parse_args()
    run_validator(args.input, args.output, args.mode)