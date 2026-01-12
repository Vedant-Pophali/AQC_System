import argparse
import json
import subprocess
import re
import sys
from pathlib import Path

def analyze_signal(input_path):
    """
    4.2 Signal Integrity
    Uses:
    - aphasemeter: Detects phase cancellation (Mono compatibility).
    - astats: Detects DC offset and Dynamic Range.
    - silencedetect: Detects audio dropouts.
    - volumedetect: Detects clipping.
    """
    events = []
    metrics = {
        "dc_offset_max": 0.0,
        "dynamic_range_db": 0.0,
        "peak_volume_db": -99.0
    }
    
    # --- 1. Complex Signal Chain (Phase, Silence, Stats) ---
    # We use 'astats' to check for DC Offset and Range
    # metadata=1 prints the stats to stderr
    # silencedetect: threshold -50dB, duration 0.5s
    cmd = [
        "ffmpeg", "-v", "info", "-i", str(input_path),
        "-filter_complex", 
        "aphasemeter=video=0,silencedetect=n=-50dB:d=0.5,astats=metadata=1:reset=1:measure_overall=DC_offset+Dynamic_range",
        "-f", "null", "-"
    ]
    
    try:
        process = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        log = process.stderr
        
        # Parse FFmpeg Log
        for line in log.split('\n'):
            # A. Silence Detect
            if "silence_end" in line:
                try:
                    parts = line.split("|")
                    dur_str = parts[1].strip() # silence_duration: 2.5
                    duration = float(dur_str.split(":")[1])
                    
                    end_time_str = parts[0].split(":")[1]
                    end_time = float(end_time_str)
                    start_time = end_time - duration
                    
                    events.append({
                        "type": "audio_dropout",
                        "details": f"Audio Silence detected for {duration}s.",
                        "start_time": round(start_time, 2),
                        "end_time": round(end_time, 2)
                    })
                except: pass

            # B. Astats (DC Offset & Dynamic Range)
            # Log format: "lavfi.astats.Overall.DC_offset=0.000001"
            if "lavfi.astats.Overall.DC_offset" in line:
                try:
                    val = float(line.split("=")[1])
                    metrics["dc_offset_max"] = max(metrics["dc_offset_max"], abs(val))
                except: pass
                
            if "lavfi.astats.Overall.Dynamic_range" in line:
                try:
                    val = float(line.split("=")[1])
                    metrics["dynamic_range_db"] = val
                except: pass

    except Exception as e:
        print(f"Filter chain warning: {e}")
        
    # --- 2. Clipping Check (VolumeDetect) ---
    # VolumeDetect is more reliable for True Peak finding than astats
    try:
        cmd_vol = ["ffmpeg", "-i", str(input_path), "-af", "volumedetect", "-f", "null", "-"]
        proc_vol = subprocess.run(cmd_vol, capture_output=True, text=True, errors="replace")
        
        # Parse: "max_volume: -0.5 dB"
        match = re.search(r"max_volume:\s*([-0-9\.]+)\s*dB", proc_vol.stderr)
        if match:
            max_vol = float(match.group(1))
            metrics["peak_volume_db"] = max_vol
            
            if max_vol >= 0.0:
                events.append({
                    "type": "audio_clipping",
                    "details": f"Audio hits 0.0 dB (Max: {max_vol} dB). Potential digital clipping.",
                    "severity": "CRITICAL"
                })
            
    except Exception:
        pass

    # --- 3. Final Logic Checks ---
    
    # DC Offset Check (Threshold: 0.01 is usually audible/bad)
    if metrics["dc_offset_max"] > 0.001:
        events.append({
            "type": "dc_offset_error",
            "details": f"High DC Offset detected ({metrics['dc_offset_max']}). Possible electrical grounding issue.",
            "severity": "WARNING"
        })

    # Noise Floor / Flatline Check
    # If dynamic range is super low (<5dB), audio might be missing or placeholder noise
    if metrics["dynamic_range_db"] < 5.0 and metrics["dynamic_range_db"] > 0:
         events.append({
            "type": "low_dynamic_range",
            "details": f"Dynamic Range is very low ({metrics['dynamic_range_db']} dB). Audio might be placeholder noise.",
            "severity": "WARNING"
        })

    return events, metrics

def run_validator(input_path, output_path, mode="strict"):
    events, metrics = analyze_signal(input_path)
    
    status = "PASSED"
    for e in events:
        if e.get("severity") == "CRITICAL" or e.get("type") == "audio_clipping":
            status = "REJECTED"
        elif e.get("type") == "audio_dropout":
            # Reject if silence > 2s
            dur = e.get("end_time", 0) - e.get("start_time", 0)
            if dur > 2.0:
                status = "REJECTED"
            elif status != "REJECTED":
                status = "WARNING"
        elif status != "REJECTED":
            status = "WARNING"

    report = {
        "module": "validate_audio_signal",
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