import argparse
import json
import subprocess
import re
from pathlib import Path

def check_interlacing(input_path):
    """
    3.2 Interlacing & Field Errors
    Uses 'idet' (Interlace Detection) filter to classify frames.
    It counts: TFF (Top Field First), BFF (Bottom Field First), and Progressive.
    """
    events = []
    metrics = {
        "tff_frames": 0,
        "bff_frames": 0,
        "progressive_frames": 0,
        "interlace_ratio": 0.0,
        "scan_type": "undetermined"
    }
    
    # 1. IDET (Field Separation & Classification)
    # We scan up to 1000 frames to get a statistically significant sample
    cmd_idet = [
        "ffmpeg", "-v", "info", "-i", str(input_path),
        "-vf", "idet", "-frames:v", "1000", "-f", "null", "-"
    ]
    try:
        proc = subprocess.run(cmd_idet, capture_output=True, text=True, errors="replace")
        log = proc.stderr
        
        # Parse: "Multi frame detection: TFF: 120 BFF: 0 Progressive: 880 Undetermined: 0"
        match = re.search(r"Multi frame detection: TFF:\s*(\d+)\s*BFF:\s*(\d+)\s*Progressive:\s*(\d+)", log)
        if match:
            tff, bff, prog = map(int, match.groups())
            metrics["tff_frames"] = tff
            metrics["bff_frames"] = bff
            metrics["progressive_frames"] = prog
            
            total = tff + bff + prog
            if total > 0:
                # Calculate Interlace Ratio
                # TFF+BFF / Total
                interlace_ratio = (tff + bff) / total
                metrics["interlace_ratio"] = float(f"{interlace_ratio:.4f}")
                
                # Logic: If > 10% frames are TFF/BFF, it's likely Interlaced content
                if interlace_ratio > 0.10:
                    metrics["scan_type"] = "interlaced"
                    events.append({
                        "type": "interlace_detected",
                        "details": f"Content has significant interlacing artifacts (Ratio: {interlace_ratio:.2f}).",
                        "severity": "high"
                    })
                else:
                    metrics["scan_type"] = "progressive"

    except Exception as e:
        print(f"Interlace check warning: {e}")

    return events, metrics

def run_validator(input_path, output_path, mode="strict"):
    events, metrics = check_interlacing(input_path)
    
    status = "PASSED"
    # Strict mode: Reject if interlaced content is found 
    # (assuming delivery spec requires Progressive)
    if events:
        if mode == "strict":
            status = "REJECTED"
        else:
            status = "WARNING"

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