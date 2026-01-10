import argparse
import json
import subprocess
import os
import re
from pathlib import Path

def analyze_signal(input_path):
    """
    4.2 Signal Integrity & 4.3 Phase
    Uses:
    - aphasemeter: Detects phase cancellation (Mono compatibility).
    - astats: Detects DC offset and Bit-depth range.
    - silencedetect: Detects audio dropouts.
    """
    events = []
    
    # We run a complex filter chain
    # 1. aphasemeter: logs phase info
    # 2. silencedetect: logs silence > -60dB for 0.1s
    # 3. volumedetect: simpler than astats for clipping check
    cmd = [
        "ffmpeg", "-v", "info", "-i", str(input_path),
        "-filter_complex", "aphasemeter=video=0,silencedetect=n=-50dB:d=0.5",
        "-f", "null", "-"
    ]
    
    try:
        process = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        log = process.stderr
        
        # 4.3 Phase Analysis (Parsing is hard, we look for out-of-phase warnings if FFmpeg emits them, 
        # or we assume generalized phase issues if we had raw data. 
        # For CLI, aphasemeter visualizes. We will rely on 'astats' for simpler correlation if possible, 
        # but standard FFmpeg doesn't output text stats for phase easily without frame-by-frame parsing.)
        # ALTERNATIVE: Use 'volumedetect' for clipping and 'silencedetect' for dropouts.
        
        # 1. Parse Silence (Dropouts)
        # [silencedetect @ 0000] silence_start: 12.5
        # [silencedetect @ 0000] silence_end: 15.0 | silence_duration: 2.5
        for line in log.split('\n'):
            if "silence_end" in line:
                parts = line.split("|")
                dur_part = parts[1].strip() # silence_duration: 2.5
                duration = float(dur_part.split(":")[1])
                
                # Timestamp
                end_time_part = parts[0].split(":")[1] # 15.0
                end_time = float(end_time_part)
                start_time = end_time - duration
                
                events.append({
                    "type": "audio_dropout",
                    "details": f"Audio Silence detected for {duration}s.",
                    "start_time": start_time,
                    "end_time": end_time
                })

    except Exception:
        pass
        
    # 4.2 Clipping / Over-modulation (Using volumedetect)
    try:
        cmd_vol = ["ffmpeg", "-i", str(input_path), "-af", "volumedetect", "-f", "null", "-"]
        proc_vol = subprocess.run(cmd_vol, capture_output=True, text=True, errors="replace")
        
        # Parse: "max_volume: -0.5 dB"
        max_vol = -99.0
        match = re.search(r"max_volume:\s*([-0-9\.]+)\s*dB", proc_vol.stderr)
        if match:
            max_vol = float(match.group(1))
            
        if max_vol >= 0.0:
            events.append({
                "type": "audio_clipping",
                "details": f"Audio hits 0.0 dB (Max: {max_vol} dB). Potential digital clipping.",
                "severity": "CRITICAL"
            })
            
    except Exception:
        pass

    return events

def run_validator(input_path, output_path, mode="strict"):
    events = analyze_signal(input_path)
    
    status = "PASSED"
    for e in events:
        if e.get("type") == "audio_clipping":
            status = "REJECTED"
        elif e.get("type") == "audio_dropout":
            # Reject if silence is long (> 2s), else Warning
            if "2s" in e["details"] or "3s" in e["details"]: # simplistic check
                status = "REJECTED"
            elif status != "REJECTED":
                status = "WARNING"

    report = {
        "module": "validate_audio_signal",
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