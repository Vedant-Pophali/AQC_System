import argparse
import json
import subprocess
import os
from pathlib import Path

def check_loudness(input_path):
    """
    4.1 Loudness Compliance (EBU R.128)
    Measures Integrated Loudness (I), Range (LRA), and True Peak (TP).
    """
    # We use the 'ebur128' filter with 'peak=true' to get True Peak
    cmd = [
        "ffmpeg", "-nostats",
        "-i", str(input_path),
        "-filter_complex", "ebur128=peak=true",
        "-f", "null", "-"
    ]
    
    report_data = {
        "integrated_lufs": -99.0,
        "lra": 0.0,
        "true_peak_db": -99.0,
        "events": []
    }

    try:
        # EBU R.128 analysis writes to stderr
        process = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        log = process.stderr
        
        # Parse the summary at the end of the log
        # Look for:
        #   I:         -23.1 LUFS
        #   LRA:         5.2 LU
        #   True peak:  -1.5 dBTP
        
        lines = log.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith("I:") and "LUFS" in line:
                val = line.split("I:")[1].split("LUFS")[0].strip()
                report_data["integrated_lufs"] = float(val)
            if line.startswith("LRA:") and "LU" in line:
                val = line.split("LRA:")[1].split("LU")[0].strip()
                report_data["lra"] = float(val)
            if line.startswith("True peak:") and "dBTP" in line:
                # Sometimes it shows multiple values for multi-channel; take the max (peak)
                parts = line.split("True peak:")[1].split("dBTP")[0].strip().split()
                # If multiple channels, find the max peak
                try:
                    peaks = [float(p) for p in parts if p]
                    report_data["true_peak_db"] = max(peaks)
                except:
                    pass

    except Exception as e:
        report_data["events"].append({"type": "execution_error", "details": str(e)})

    return report_data

def run_validator(input_path, output_path, mode="strict"):
    # Compliance Targets
    # Strict (Broadcast): -23 LUFS (+/- 1.0), True Peak < -1.0
    # OTT (Web): -16 LUFS (+/- 2.0), True Peak < -1.0
    
    target_i = -23.0 if mode == "strict" else -16.0
    tolerance = 1.0 if mode == "strict" else 2.0
    max_tp = -1.0
    
    data = check_loudness(input_path)
    events = data["events"]
    status = "PASSED"
    
    i_val = data["integrated_lufs"]
    tp_val = data["true_peak_db"]
    
    # 1. Check Integrated Loudness
    if abs(i_val - target_i) > tolerance:
        status = "REJECTED"
        events.append({
            "type": "loudness_violation",
            "details": f"Integrated Loudness {i_val} LUFS is outside target {target_i} +/- {tolerance}.",
            "severity": "high"
        })
        
    # 2. Check True Peak
    if tp_val > max_tp:
        status = "REJECTED"
        events.append({
            "type": "true_peak_violation",
            "details": f"True Peak {tp_val} dBTP exceeds limit {max_tp} dBTP.",
            "severity": "high"
        })

    report = {
        "module": "validate_loudness",
        "status": status,
        "metrics": {
            "integrated_lufs": i_val,
            "lra": data["lra"],
            "true_peak": tp_val
        },
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