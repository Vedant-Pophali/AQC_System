import argparse
import json
import subprocess
import re
from pathlib import Path

def get_video_info(input_path):
    """
    Get basic resolution and duration.
    """
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration", 
            "-of", "json", str(input_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(res.stdout)
        stream = data["streams"][0]
        return int(stream["width"]), int(stream["height"]), float(stream.get("duration", 0))
    except:
        return 1920, 1080, 0.0 # Fallback

def detect_crop(input_path, start_time):
    """
    3.4 Geometry & Framing
    Uses 'cropdetect' to find the actual active video area.
    """
    # Run cropdetect on 10 frames in the middle of the video
    cmd = [
        "ffmpeg", "-ss", str(start_time), "-i", str(input_path),
        "-vf", "cropdetect=24:16:0", "-frames:v", "10", "-f", "null", "-"
    ]
    
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
        # Look for: "crop=1920:800:0:140" (Format: w:h:x:y)
        matches = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", proc.stderr)
        if matches:
            # Take the last match (filter stabilizes over time)
            w, h, x, y = matches[-1] 
            return int(w), int(h), int(x), int(y)
    except Exception:
        pass
    return None

def run_validator(input_path, output_path, mode="strict"):
    report = {
        "module": "validate_geometry",
        "status": "PASSED",
        "metrics": {},
        "events": []
    }
    
    # 1. Get Container Dimensions & Duration
    full_w, full_h, duration = get_video_info(input_path)
    
    # Calculate a safe seek time (Middle of video)
    # If video is < 2s, start at 0
    safe_seek = duration / 2.0 if duration > 2.0 else 0.0
    
    # 2. Detect Active Area
    crop = detect_crop(input_path, safe_seek)
    
    if crop:
        active_w, active_h, x, y = crop
        
        report["metrics"] = {
            "container_width": full_w,
            "container_height": full_h,
            "active_width": active_w,
            "active_height": active_h,
            "fill_percentage": round((active_w * active_h) / (full_w * full_h) * 100, 2)
        }
        
        # 3.4 Letterbox Detection (Bars at top/bottom)
        # Tolerance: Allow 1% difference for coding blocks
        if active_h < (full_h * 0.99):
            report["events"].append({
                "type": "letterbox_detected",
                "details": f"Active height {active_h}px < {full_h}px. Letterboxing detected."
            })
            
        # 3.4 Pillarbox Detection (Bars at sides)
        if active_w < (full_w * 0.99):
            report["events"].append({
                "type": "pillarbox_detected",
                "details": f"Active width {active_w}px < {full_w}px. Pillarboxing detected."
            })
            
        # 3.4 Unsafe Aperture / Clean Feed Check
        # If video fills < 80% of frame, warn.
        fill_rate = report["metrics"]["fill_percentage"]
        if fill_rate < 80.0:
            report["status"] = "WARNING"
            report["events"].append({
                "type": "unsafe_framing",
                "details": f"Video fills only {fill_rate}% of the frame. Large borders detected."
            })
    else:
        report["metrics"]["error"] = "Could not detect active crop area."

    with open(output_path, "w") as f:
        json.dump(report, f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default="strict")
    args = parser.parse_args()
    run_validator(args.input, args.output, args.mode)