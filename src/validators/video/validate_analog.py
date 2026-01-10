import argparse
import json
import subprocess
import os
import sys
from pathlib import Path

def get_signal_stats(input_path):
    """
    2.2 Analog Defect Detection
    Uses FFmpeg 'signalstats' to extract VREP (Vertical Repetition).
    High VREP = Analog Head Clog or TBC Failure.
    """
    # We analyze frame-by-frame. 
    # VREP is typically < 0.1 for clean video. > 0.5 is a serious defect.
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_frames",
        "-show_entries", "frame=pkt_pts_time : frame_tags=gavf.signalstats.VREP",
        "-f", "lavfi",
        f"movie={str(input_path).replace(':', r'\:')},signalstats"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(result.stdout)
    except Exception:
        return None

def analyze_vrep(frames_data, threshold=0.2):
    events = []
    
    if not frames_data or "frames" not in frames_data:
        return events
        
    consecutive_frames = 0
    start_time = None
    
    for frame in frames_data["frames"]:
        tags = frame.get("tags", {})
        # FFprobe returns tags like "gavf.signalstats.VREP"
        vrep_str = tags.get("gavf.signalstats.VREP")
        timestamp = float(frame.get("pkt_pts_time", 0))
        
        if vrep_str:
            vrep = float(vrep_str)
            if vrep > threshold:
                if consecutive_frames == 0:
                    start_time = timestamp
                consecutive_frames += 1
            else:
                # Spike ended
                if consecutive_frames > 2: # Ignore single frame blips (noise)
                    events.append({
                        "type": "analog_defect_vrep",
                        "details": f"High Vertical Repetition (VREP: {vrep}). Possible Head Clog or TBC Error.",
                        "start_time": start_time,
                        "end_time": timestamp
                    })
                consecutive_frames = 0
                
    return events

def run_validator(input_path, output_path, mode="strict"):
    # 2.2 Sensitivity Thresholding
    # Strict = 0.15 (Very sensitive), OTT = 0.3 (Looser)
    vrep_limit = 0.15 if mode == "strict" else 0.3
    
    input_path = Path(input_path)
    report = {
        "module": "validate_analog",
        "status": "PASSED",
        "events": []
    }

    frames = get_signal_stats(input_path)
    events = analyze_vrep(frames, threshold=vrep_limit)
    
    if events:
        report["events"] = events
        report["status"] = "WARNING" # Analog errors are often warnings unless severe
        
    with open(output_path, "w") as f:
        json.dump(report, f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default="strict")
    args = parser.parse_args()
    
    run_validator(args.input, args.output, args.mode)