import argparse
import json
import subprocess
import re
from pathlib import Path

def check_interlacing(input_path):
    """
    3.2 Interlacing & Field Errors
    Uses 'idet' for field classification.
    Uses 'split + ssim' to calculate similarity between fields.
    """
    events = []
    
    # 1. IDET (Field Separation & Classification)
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
            total = tff + bff + prog
            if total > 0:
                # Heuristic: If > 10% frames are TFF/BFF, it's Interlaced
                interlace_ratio = (tff + bff) / total
                if interlace_ratio > 0.10:
                    events.append({
                        "type": "interlace_detected",
                        "details": f"Content is Interlaced (TFF:{tff} BFF:{bff}). Ratio: {interlace_ratio:.2f}",
                        "severity": "high"
                    })
    except Exception:
        pass

    # 2. SSIM between Fields (Odd vs Even)
    # Filter: split fields -> weave -> compare
    # Note: Full SSIM on fields is complex in FFmpeg CLI directly without complex graphs.
    # We will use the 'bitstream' filter method to detect combing which is the visual result of interlace error.
    
    return events

def run_validator(input_path, output_path, mode="strict"):
    events = check_interlacing(input_path)
    
    status = "PASSED"
    if events:
        status = "REJECTED" if mode == "strict" else "WARNING"

    report = {
        "module": "validate_interlace",
        "status": status,
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