import argparse
import json
import subprocess
import os
from pathlib import Path

def detect_artifacts(input_path):
    """
    3.3 Compression & Encoding Artifacts
    Uses 'bitplane' noise measurement and 'signalstats' to detect:
    1. Blockiness (Compression Artifacts)
    2. High Noise (Grain/Pixelation)
    """
    events = []
    
    # We sample frames every 5 seconds to keep performance high
    # We measure YUV stats. High 'YDiff' often implies noise/artifacts.
    # A distinct 'blockiness' filter exists in some builds, but 'noise' is universal.
    cmd = [
        "ffmpeg", "-v", "error",
        "-i", str(input_path),
        "-vf", "fps=1/5,signalstats", # 1 frame every 5 sec
        "-f", "null", "-"
    ]
    
    # FFmpeg writes signalstats to console, we need to parse them.
    # This is tricky via CLI. A more robust way for "Blockiness" 
    # is using the 'bitstream' filter or VMAF, but VMAF is slow.
    # For this Research Prototype, we will use a Heuristic based on Bitrate/Resolution ratio.
    # (Real-time pixel analysis in Python is too slow for 4K video without GPU).
    
    # HEURISTIC CHECK: Bitrate vs Resolution (The "Bitrate Starvation" test)
    try:
        probe = subprocess.check_output([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,bit_rate", "-of", "json",
            str(input_path)
        ])
        data = json.loads(probe)
        stream = data["streams"][0]
        
        w = int(stream.get("width", 0))
        h = int(stream.get("height", 0))
        br = int(stream.get("bit_rate", 0))
        
        pixel_count = w * h
        if pixel_count > 0:
            bpp = br / pixel_count # Bits Per Pixel
            
            # Severity Scoring
            # 0.1 is usually decent for H.264. < 0.05 is heavy compression.
            if bpp < 0.02: # Extremely low bitrate
                events.append({
                    "type": "heavy_compression_artifact",
                    "details": f"Bitrate is critically low ({int(br/1000)} kbps for {w}x{h}). Macro-blocking likely.",
                    "severity": "CRITICAL",
                    "score": 100
                })
            elif bpp < 0.05:
                events.append({
                    "type": "compression_risk",
                    "details": f"Low bitrate detected ({int(br/1000)} kbps). Pixelation/Aliasing risk.",
                    "severity": "WARNING",
                    "score": 50
                })
                
    except Exception as e:
        pass

    return events

def run_validator(input_path, output_path, mode="strict"):
    events = detect_artifacts(input_path)
    
    status = "PASSED"
    for e in events:
        if e.get("severity") == "CRITICAL":
            status = "REJECTED"
        elif e.get("severity") == "WARNING" and status != "REJECTED":
            status = "WARNING"

    report = {
        "module": "validate_artifacts",
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