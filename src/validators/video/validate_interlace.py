import argparse
import json
import cv2
import numpy as np
from pathlib import Path

def calculate_psnr(img1, img2):
    """
    Calculate Peak Signal-to-Noise Ratio between two images.
    Used here to compare Odd vs Even fields.
    """
    diff = img1 - img2
    rmse = np.sqrt(np.mean(diff ** 2))
    if rmse == 0:
        return 100.0
    return 20 * np.log10(255.0 / rmse)

def calculate_ssim_approx(img1, img2):
    """
    A lightweight Structural Similarity (SSIM) approximation.
    Full SSIM is too heavy for a quick scanner, so we use Mean/Variance correlation.
    """
    C1 = 6.5025
    C2 = 58.5225
    
    # Convert to float
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

def analyze_fields(input_path):
    """
    Scans video to calculate interlace metrics and map defects to timecodes.
    """
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
    
    # Accumulators
    total_psnr = 0.0
    total_ssim = 0.0
    total_temp_div = 0.0
    
    prev_odd_field = None
    
    # Time mapping state
    in_interlace_seq = False
    seq_start_time = 0.0
    
    frame_idx = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Optimization: Analyze every 2nd frame to speed up (Interlace usually affects sequences)
        if frame_idx % 2 != 0:
            frame_idx += 1
            continue

        current_time = frame_idx / fps
        
        # 1. Field Separation (Split rows)
        # Even rows (0, 2, 4...) -> Field 1
        # Odd rows (1, 3, 5...) -> Field 2
        # We perform analysis on Grayscale to be fast
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Slice rows
        even_field = gray[0::2, :]
        odd_field = gray[1::2, :]
        
        # Ensure sizes match (sometimes odd height images drop the last line)
        min_h = min(even_field.shape[0], odd_field.shape[0])
        even_field = even_field[:min_h, :]
        odd_field = odd_field[:min_h, :]
        
        # 2. PSNR & SSIM (Spatial comparison between fields)
        # Low PSNR between fields implies they look very different -> Motion comb artifacts
        psnr = calculate_psnr(even_field, odd_field)
        ssim = calculate_ssim_approx(even_field, odd_field)
        
        total_psnr += psnr
        total_ssim += ssim
        
        # 3. Temporal Divergence (Motion check)
        temp_div = 0.0
        if prev_odd_field is not None:
            # How much did the Odd field change since last frame?
            temp_div = np.mean(np.abs(odd_field - prev_odd_field))
            total_temp_div += temp_div
        
        prev_odd_field = odd_field.copy()
        
        # 4. Detect Interlacing Artifacts (The "Comb" check)
        # Heuristic: If there is significant motion (temp_div > 5) 
        # AND the fields are very different (PSNR < 30), it's likely combing.
        # Static scenes (temp_div ~ 0) always have high PSNR, so we ignore them.
        is_interlaced_frame = False
        
        if temp_div > 5.0 and psnr < 32.0:
            is_interlaced_frame = True
            metrics["interlaced_frame_count"] += 1
            
        # 5. Time-Range Mapping
        if is_interlaced_frame:
            if not in_interlace_seq:
                in_interlace_seq = True
                seq_start_time = current_time
        else:
            if in_interlace_seq:
                in_interlace_seq = False
                duration = current_time - seq_start_time
                # Only log if it persists for > 0.2s (5 frames)
                if duration > 0.2:
                    events.append({
                        "type": "interlace_artifact",
                        "details": f"Combing artifacts detected ({duration:.2f}s)",
                        "start_time": round(seq_start_time, 2),
                        "end_time": round(current_time, 2)
                    })

        metrics["scanned_frames"] += 1
        frame_idx += 1
        
        # Safety limit for very long videos (check first 2 minutes)
        if frame_idx > (fps * 120): 
            break

    cap.release()
    
    # Close pending sequence
    if in_interlace_seq:
        events.append({
            "type": "interlace_artifact",
            "details": f"Combing artifacts detected (End of check)",
            "start_time": round(seq_start_time, 2),
            "end_time": round(current_time, 2)
        })

    # Average Metrics
    count = metrics["scanned_frames"]
    if count > 0:
        metrics["avg_field_psnr"] = round(total_psnr / count, 2)
        metrics["avg_field_ssim"] = round(total_ssim / count, 4)
        metrics["avg_temporal_divergence"] = round(total_temp_div / count, 2)
        
    return events, metrics

def run_validator(input_path, output_path, mode="strict"):
    events, metrics = analyze_fields(input_path)
    
    status = "PASSED"
    
    # Logic: If we found distinct interlace sequences, or the global field PSNR is consistently low
    if events:
        status = "REJECTED" if mode == "strict" else "WARNING"
        
    # Secondary check: Global metrics
    # If Avg PSNR is very low (< 35) on a long file, the whole thing might be interlaced encoding
    if metrics["avg_field_psnr"] > 0 and metrics["avg_field_psnr"] < 35.0:
        if not events: # If we didn't catch specific ranges but stats are bad
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