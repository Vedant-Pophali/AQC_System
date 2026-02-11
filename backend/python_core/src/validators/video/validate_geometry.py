import argparse
import json
import subprocess
import re
from fractions import Fraction
from pathlib import Path

def load_profile(mode="strict"):
    default_profile = {
        "blanking_tolerance_pct": 1.0,
        "ar_tolerance": 0.05
    }
    try:
        config_path = Path(__file__).parent.parent.parent / "config" / "signal_profiles.json"
        if config_path.exists():
            with open(config_path, "r") as f:
                data = json.load(f)
                profiles = data.get("profiles", {})
                key = "STRICT"
                if mode.lower() == "netflix": key = "NETFLIX_HD"
                if mode.lower() == "youtube": key = "YOUTUBE"
                if key in profiles:
                    return profiles[key].get("validate_geometry", default_profile)
    except Exception:
        pass
    return default_profile

def get_geometry_metadata(input_path):
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
    try:
        if ":" in ratio_str:
            num, den = map(int, ratio_str.split(":"))
            return num / den if den != 0 else 0.0
        return float(ratio_str)
    except:
        return 0.0

def detect_active_area(input_path, start_time):
    cmd = [
        "ffmpeg", "-ss", str(start_time), "-i", str(input_path),
        "-vf", "cropdetect=24:16:0", "-frames:v", "5", "-f", "null", "-"
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
        matches = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", proc.stderr)
        if matches:
            w, h, x, y = map(int, matches[-1])
            return w, h, x, y
    except:
        pass
    return None

def run_validator(input_path, output_path, mode="strict"):
    profile = load_profile(mode)
    report = {
        "module": "validate_geometry",
        "status": "PASSED",
        "metrics": {},
        "events": []
    }
    
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
    dar = parse_ratio(dar_str)
    
    res_ratio = width / height if height > 0 else 0
    calc_dar = res_ratio * sar if sar > 0 else res_ratio
    
    report["metrics"] = {
        "container_res": f"{width}x{height}",
        "sar": sar_str,
        "metadata_dar": dar_str,
        "calculated_dar": round(calc_dar, 4)
    }

    # CHECK 1: Metadata AR
    AR_TOL = profile.get("ar_tolerance", 0.05)
    if dar > 0 and abs(dar - calc_dar) > AR_TOL:
        report["status"] = "WARNING"
        report["events"].append({
            "type": "ar_distortion",
            "details": f"Metadata DAR ({dar:.2f}) mismatch with Resolution-based DAR ({calc_dar:.2f})."
        })

    # CHECK 2: Active Picture Area
    safe_seek = duration / 2.0 if duration > 5.0 else 0.0
    crop = detect_active_area(input_path, safe_seek)
    
    if crop:
        act_w, act_h, x, y = crop
        report["metrics"]["active_res"] = f"{act_w}x{act_h}"
        
        # Blanking Tolerance Calculation
        active_area = act_w * act_h
        total_area = width * height
        blanking_pct = 100.0 * (1.0 - (active_area / total_area))
        
        TOL_PCT = profile.get("blanking_tolerance_pct", 1.0)
        
        # Only flag if blanking > tolerance
        if blanking_pct > TOL_PCT:
            
            # Identify Letterbox/Pillarbox
            is_letterbox = act_h < height * 0.99
            is_pillarbox = act_w < width * 0.99
            
            if is_letterbox:
                report["events"].append({
                    "type": "letterbox_detected",
                    "details": f"Content is letterboxed. Active height {act_h} < {height} (Blanking: {blanking_pct:.1f}%)"
                })
                
            if is_pillarbox:
                report["events"].append({
                    "type": "pillarbox_detected",
                    "details": f"Content is pillarboxed. Active width {act_w} < {width} (Blanking: {blanking_pct:.1f}%)"
                })

            # "Postage Stamp" check (both dimensions shrunk)
            if (active_area / total_area) < 0.75:
                severity = "REJECTED" if mode == "strict" else "WARNING"
                if severity == "REJECTED": report["status"] = "REJECTED"
                report["events"].append({
                    "type": "small_active_area",
                    "details": f"Active video uses only {int((active_area / total_area)*100)}% of canvas. 'Postage stamp' artifact."
                })
        else:
             report["metrics"]["note"] = f"Detected blanking ({blanking_pct:.2f}%) within tolerance ({TOL_PCT}%)."

    with open(output_path, "w") as f:
        json.dump(report, f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default="strict")
    args = parser.parse_args()
    run_validator(args.input, args.output, args.mode)