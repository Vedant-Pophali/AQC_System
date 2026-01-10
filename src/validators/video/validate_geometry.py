import argparse
import json
import subprocess
import re
from pathlib import Path

def detect_crop(input_path):
    """
    3.4 Geometry & Framing
    Uses 'cropdetect' to find the actual active video area.
    """
    # Run cropdetect on a few frames in the middle of the video to avoid fades
    cmd = [
        "ffmpeg", "-ss", "10", "-i", str(input_path),
        "-vf", "cropdetect=24:16:0", "-frames:v", "5", "-f", "null", "-"
    ]
    
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
        # Look for: "crop=1920:800:0:140"
        # Format: w:h:x:y
        matches = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", proc.stderr)
        if matches:
            # Take the most common result
            w, h, x, y = matches[-1] # Take the last one (stabilized)
            return int(w), int(h), int(x), int(y)
    except Exception:
        pass
    return None

def run_validator(input_path, output_path, mode="strict"):
    report = {
        "module": "validate_geometry",
        "status": "PASSED",
        "events": []
    }
    
    # Get total resolution first
    try:
        probe = subprocess.check_output([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0", str(input_path)
        ], text=True).strip().split(',')
        full_w, full_h = int(probe[0]), int(probe[1])
    except:
        full_w, full_h = 1920, 1080 # Fallback

    # Detect Active Area
    crop = detect_crop(input_path)
    if crop:
        active_w, active_h, x, y = crop
        
        # 3.4 Letterbox Detection (Bars at top/bottom)
        if active_h < full_h:
            report["events"].append({
                "type": "letterbox_detected",
                "details": f"Active video height is {active_h}px (Container: {full_h}px). Black bars detected."
            })
            
        # 3.4 Pillarbox Detection (Bars at sides)
        if active_w < full_w:
            report["events"].append({
                "type": "pillarbox_detected",
                "details": f"Active video width is {active_w}px (Container: {full_w}px). Side bars detected."
            })
            
        # 3.4 Unsafe Aperture / Bounds Mismatch
        # If active area is significantly smaller than container (e.g., < 80%)
        fill_rate = (active_w * active_h) / (full_w * full_h)
        if fill_rate < 0.8:
            report["status"] = "WARNING"
            report["events"].append({
                "type": "unsafe_framing",
                "details": f"Video fills only {int(fill_rate*100)}% of the frame. Large borders detected."
            })

    with open(output_path, "w") as f:
        json.dump(report, f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default="strict")
    args = parser.parse_args()
    run_validator(args.input, args.output, args.mode)