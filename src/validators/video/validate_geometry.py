import argparse
import json
import subprocess
import re
from fractions import Fraction
from pathlib import Path

def get_geometry_metadata(input_path):
    """
    Extracts deep geometry metadata: SAR, DAR, and Resolution.
    """
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,sample_aspect_ratio,display_aspect_ratio,duration", 
            "-of", "json", str(input_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(res.stdout)
        if not data.get("streams"):
            return None
        return data["streams"][0]
    except Exception:
        return None

def parse_ratio(ratio_str):
    """Converts '16:9' or '1:1' string to float."""
    try:
        if ":" in ratio_str:
            num, den = map(int, ratio_str.split(":"))
            return num / den if den != 0 else 0.0
        return float(ratio_str)
    except:
        return 0.0

def detect_active_area(input_path, start_time):
    """
    Uses cropdetect to find black bars.
    """
    cmd = [
        "ffmpeg", "-ss", str(start_time), "-i", str(input_path),
        "-vf", "cropdetect=24:16:0", "-frames:v", "5", "-f", "null", "-"
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
        matches = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", proc.stderr)
        if matches:
            # Return last match (stabilized)
            w, h, x, y = map(int, matches[-1])
            return w, h, x, y
    except:
        pass
    return None

def run_validator(input_path, output_path, mode="strict"):
    report = {
        "module": "validate_geometry",
        "status": "PASSED",
        "metrics": {},
        "events": []
    }
    
    # 1. Get Metadata
    meta = get_geometry_metadata(input_path)
    if not meta:
        report["status"] = "SKIPPED"
        report["metrics"]["error"] = "Could not probe video geometry"
        with open(output_path, "w") as f: json.dump(report, f, indent=4)
        return

    width = int(meta.get("width", 0))
    height = int(meta.get("height", 0))
    sar_str = meta.get("sample_aspect_ratio", "1:1")
    dar_str = meta.get("display_aspect_ratio", "0:0")
    duration = float(meta.get("duration", 0))

    sar = parse_ratio(sar_str)
    dar = parse_ratio(dar_str) # Metadata DAR
    
    # Calculate Theoretical DAR based on resolution and SAR
    # Formula: DAR = (Width / Height) * SAR
    res_ratio = width / height if height > 0 else 0
    calc_dar = res_ratio * sar if sar > 0 else res_ratio

    report["metrics"] = {
        "container_res": f"{width}x{height}",
        "sar": sar_str,
        "metadata_dar": dar_str,
        "calculated_dar": round(calc_dar, 4)
    }

    # -------------------------------------------------
    # CHECK 1: Aspect Ratio Distortion / Metadata Mismatch
    # -------------------------------------------------
    # If the metadata DAR differs significantly from (W/H * SAR), the player will stretch it wrong.
    # 0:0 usually means FFmpeg couldn't calculate it, usually safe to ignore if SAR is 1:1
    if dar > 0 and abs(dar - calc_dar) > 0.05:
        report["status"] = "WARNING"
        report["events"].append({
            "type": "ar_distortion",
            "details": f"Metadata DAR ({dar:.2f}) mismatch with Resolution-based DAR ({calc_dar:.2f}). Video may appear stretched."
        })

    # -------------------------------------------------
    # CHECK 2: Active Picture Area (Crop/Framing)
    # -------------------------------------------------
    safe_seek = duration / 2.0 if duration > 5.0 else 0.0
    crop = detect_active_area(input_path, safe_seek)
    
    if crop:
        act_w, act_h, x, y = crop
        report["metrics"]["active_res"] = f"{act_w}x{act_h}"
        
        # Letterbox (Top/Bottom bars)
        if act_h < height * 0.99:
            report["events"].append({
                "type": "letterbox_detected",
                "details": f"Active height {act_h} < {height}. Content is letterboxed."
            })

        # Pillarbox (Side bars)
        if act_w < width * 0.99:
            report["events"].append({
                "type": "pillarbox_detected",
                "details": f"Active width {act_w} < {width}. Content is pillarboxed."
            })

        # Unsafe Aperture / Clean Feed (Encode vs Display bounds mismatch)
        # If the active video is significantly smaller than the encoded area, we are wasting bitrate
        # or have a "Postage Stamp" defect.
        fill_factor = (act_w * act_h) / (width * height)
        report["metrics"]["fill_factor"] = round(fill_factor, 2)
        
        if fill_factor < 0.75:
            severity = "REJECTED" if mode == "strict" else "WARNING"
            if severity == "REJECTED": report["status"] = "REJECTED"
            report["events"].append({
                "type": "small_active_area",
                "details": f"Active video uses only {int(fill_factor*100)}% of canvas. 'Postage stamp' artifact detected."
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