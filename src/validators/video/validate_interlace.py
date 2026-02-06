import argparse
import json
import cv2
import numpy as np
from pathlib import Path

# Try to import config, fallback to defaults
try:
    from src.utils.logger import setup_logger
    logger = setup_logger("validate_interlace")
except ImportError:
    import logging
    logger = logging.getLogger("validate_interlace")

def load_profile(mode="strict"):
    default_profile = {
        "psnr_threshold": 32.0,
        "ssim_threshold": 0.90,
        "temporal_divergence_threshold": 5.0,
        "min_duration_sec": 0.2
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
                    return profiles[key].get("validate_interlace", default_profile)
    except Exception:
        pass
    return default_profile

def calculate_psnr(img1, img2):
    diff = img1 - img2
    rmse = np.sqrt(np.mean(diff ** 2))
    if rmse == 0:
        return 100.0
    return 20 * np.log10(255.0 / rmse)

def calculate_ssim_approx(img1, img2):
    """
    Mean/Variance correlation suitable for field comparison.
    """
    C1 = 6.5025
    C2 = 58.5225
    
    i1 = img1.astype(np.float64)
    i2 = img2.astype(np.float64)
    
    mu1 = np.mean(i1)
    mu2 = np.mean(i2)
    sig1 = np.var(i1)
    sig2 = np.var(i2)
    covar = np.mean((i1 - mu1) * (i2 - mu2))
    
    numerator = (2 * mu1 * mu2 + C1) * (2 * covar + C2)
    denominator = (mu1**2 + mu2**2 + C1) * (sig1 + sig2 + C2)
    
    return numerator / denominator

def analyze_fields(input_path, profile):
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        return [], {}

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0: fps = 25.0
    
    metrics = {
        "avg_field_psnr": 0.0,
        "avg_field_ssim": 0.0,
        "avg_temporal_divergence": 0.0,
        "interlaced_frame_count": 0,
        "scanned_frames": 0
    }
    
    events = []
    
    total_psnr = 0.0
    total_ssim = 0.0
    total_temp_div = 0.0
    
    prev_odd_field = None
    
    in_interlace_seq = False
    seq_start_time = 0.0
    
    frame_idx = 0
    
    # Thresholds
    TH_PSNR = profile["psnr_threshold"]
    TH_SSIM = profile["ssim_threshold"]
    TH_MOTION = profile["temporal_divergence_threshold"]
    MIN_DUR = profile["min_duration_sec"]

    while True:
        ret, frame = cap.read()
        if not ret: break
            
        # Optimization: Analyze every 2nd frame
        if frame_idx % 2 != 0:
            frame_idx += 1
            continue

        current_time = frame_idx / fps
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Field Split
        even_field = gray[0::2, :]
        odd_field = gray[1::2, :]
        min_h = min(even_field.shape[0], odd_field.shape[0])
        even_field = even_field[:min_h, :]
        odd_field = odd_field[:min_h, :]
        
        # Metrics
        psnr = calculate_psnr(even_field, odd_field)
        ssim = calculate_ssim_approx(even_field, odd_field)
        
        total_psnr += psnr
        total_ssim += ssim
        
        temp_div = 0.0
        if prev_odd_field is not None:
            temp_div = np.mean(np.abs(odd_field - prev_odd_field))
            total_temp_div += temp_div
        
        prev_odd_field = odd_field.copy()
        
        # ---------------------------------------------------------
        # ROBUST INTERLACE DETECTION LOGIC
        # We need significant motion (temp_div) AND (low PSNR OR low SSIM)
        # SSIM is often better at catching fine comb artifacts
        # ---------------------------------------------------------
        is_interlaced_frame = False
        
        if temp_div > TH_MOTION:
            if psnr < TH_PSNR or ssim < TH_SSIM:
                is_interlaced_frame = True
                metrics["interlaced_frame_count"] += 1
            
        if is_interlaced_frame:
            if not in_interlace_seq:
                in_interlace_seq = True
                seq_start_time = current_time
        else:
            if in_interlace_seq:
                in_interlace_seq = False
                duration = current_time - seq_start_time
                if duration > MIN_DUR:
                    events.append({
                        "type": "interlace_artifact",
                        "details": f"Combing artifacts detected ({duration:.2f}s). PSNR:{psnr:.1f} SSIM:{ssim:.2f}",
                        "start_time": round(seq_start_time, 2),
                        "end_time": round(current_time, 2)
                    })
 
        metrics["scanned_frames"] += 1
        frame_idx += 1
        
        # Safety limit for very long videos (check first 2 minutes)
        if frame_idx > (fps * 120): break

    cap.release()
    
    if in_interlace_seq:
        events.append({
            "type": "interlace_artifact",
            "details": f"Combing artifacts detected (End of check)",
            "start_time": round(seq_start_time, 2),
            "end_time": round(current_time, 2)
        })

    count = metrics["scanned_frames"]
    if count > 0:
        metrics["avg_field_psnr"] = round(total_psnr / count, 2)
        metrics["avg_field_ssim"] = round(total_ssim / count, 4)
        metrics["avg_temporal_divergence"] = round(total_temp_div / count, 2)
        
    return events, metrics

def run_validator(input_path, output_path, mode="strict"):
    profile = load_profile(mode)
    events, metrics = analyze_fields(input_path, profile)
    
    status = "PASSED"
    if events:
        status = "REJECTED" if mode == "strict" else "WARNING"
        
    # Global check via avg PSNR
    if metrics["avg_field_psnr"] > 0 and metrics["avg_field_psnr"] < (profile["psnr_threshold"] + 3):
        if not events:
            status = "WARNING"
            events.append({
                "type": "global_interlace_warning",
                "details": f"Low average Field PSNR ({metrics['avg_field_psnr']} dB). Content appears globally interlaced.",
                "start_time": 0.0,
                "end_time": 0.0
            })

    report = {
        "module": "validate_interlace",
        "status": status,
        "metrics": metrics,
        "events": events
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