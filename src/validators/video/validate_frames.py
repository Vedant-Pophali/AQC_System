import argparse
import json
import subprocess
import re
import cv2
import numpy as np
from pathlib import Path

# Config
DUPLICATE_THRESHOLD = 1.0  # Pixel diff sum
GAP_TOLERANCE_PCT = 0.5    # Allow 50% deviation in frame duration before flagging Gap

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

def scan_visual_integrity(input_path):
    """
    2.1 Visual Scan (Duplicates, Gaps, Drift)
    """
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        return [], 0, 0.0

    events = []
    prev_frame = None
    duplicate_count = 0
    
    # Timing Tracking
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0: fps = 24.0 # Fallback
    expected_interval = 1000.0 / fps
    
    prev_pts = -1.0
    frame_idx = 0
    max_drift_ms = 0.0
    
    in_dup_seq = False
    dup_start_time = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        current_pts = cap.get(cv2.CAP_PROP_POS_MSEC)
        
        # --- A. Gap & Drift Detection ---
        if frame_idx > 0 and prev_pts >= 0:
            delta = current_pts - prev_pts
            
            # 1. Gap Detection
            # If delta is 1.5x larger than expected, we missed a frame (or variable framerate gap)
            if delta > (expected_interval * (1.0 + GAP_TOLERANCE_PCT)):
                events.append({
                    "type": "frame_gap",
                    "details": f"Time jump of {delta:.2f}ms (Expected {expected_interval:.2f}ms)",
                    "start_time": prev_pts / 1000.0,
                    "end_time": current_pts / 1000.0
                })
            
            # 2. Drift Tracking
            # Theoretical time vs Actual PTS
            theoretical_time = frame_idx * expected_interval
            drift = abs(current_pts - theoretical_time)
            max_drift_ms = max(max_drift_ms, drift)

        prev_pts = current_pts

        # --- B. Duplicate Detection ---
        if prev_frame is not None:
            # Resize for speed (64x64 is enough)
            curr_small = cv2.resize(frame, (64, 64))
            prev_small = cv2.resize(prev_frame, (64, 64))
            
            diff = cv2.absdiff(curr_small, prev_small)
            non_zero_count = np.count_nonzero(diff)
            
            is_dup = (non_zero_count < 50) # Strict threshold

            if is_dup:
                duplicate_count += 1
                if not in_dup_seq:
                    in_dup_seq = True
                    dup_start_time = current_pts / 1000.0
            else:
                if in_dup_seq:
                    in_dup_seq = False
                    dup_end = prev_pts / 1000.0
                    duration = dup_end - dup_start_time
                    if duration > (2.0 / fps): # Ignore single dupes
                        events.append({
                            "type": "freeze_frame",
                            "details": f"Content frozen for {duration:.2f}s",
                            "start_time": dup_start_time,
                            "end_time": dup_end
                        })

        prev_frame = frame
        frame_idx += 1

    cap.release()
    
    # Check Max Drift
    if max_drift_ms > 100.0: # >100ms drift is concerning
        events.append({
            "type": "timestamp_drift",
            "details": f"High PTS Drift detected (Max: {max_drift_ms:.2f}ms).",
            "severity": "WARNING"
        })

    return events, duplicate_count, max_drift_ms

def run_validator(input_path, output_path, mode="strict"):
    report = {
        "module": "validate_frames",
        "status": "PASSED",
        "events": [],
        "metrics": {}
    }

    # 1. Bitstream Scan (PTS/DTS)
    log_data = scan_bitstream(input_path)
    bitstream_events = parse_ffmpeg_errors(log_data)
    report["events"].extend(bitstream_events)

    # 2. Visual Scan (Duplicates, Gaps, Drift)
    visual_events, dup_count, drift = scan_visual_integrity(input_path)
    report["events"].extend(visual_events)
    
    report["metrics"] = {
        "duplicate_frame_count": dup_count,
        "max_pts_drift_ms": round(drift, 2)
    }

    # Severity Logic
    if any(e["type"] in ["non_monotonic_pts", "corrupt_packet"] for e in report["events"]):
        report["status"] = "REJECTED"
    elif report["metrics"]["duplicate_frame_count"] > 24: 
        report["status"] = "WARNING"
    elif any(e["type"] == "frame_gap" for e in report["events"]):
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