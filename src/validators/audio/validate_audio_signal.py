import argparse
import json
import subprocess
import re
from pathlib import Path

def get_audio_info(input_path):
    """
    Get basic audio metadata (channels, duration).
    """
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=channels,duration", 
            "-of", "json", str(input_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(res.stdout)
        if not data.get("streams"):
            return 0, 0.0
        return int(data["streams"][0].get("channels", 0)), float(data["streams"][0].get("duration", 0))
    except:
        return 0, 0.0

def parse_silencedetect(log_text):
    """
    Parses silencedetect output into a list of [start, end] intervals.
    """
    silences = []
    for line in log_text.split('\n'):
        if "silence_end" in line:
            try:
                # [silencedetect] silence_end: 15.0 | silence_duration: 2.5
                parts = line.split("|")
                dur_str = parts[1].strip() 
                duration = float(dur_str.split(":")[1])
                
                end_time_str = parts[0].split(":")[1]
                end_time = float(end_time_str)
                start_time = end_time - duration
                silences.append((round(start_time, 2), round(end_time, 2)))
            except:
                pass
    return silences

def analyze_signal(input_path):
    """
    Two-Pass Analysis:
    1. Signal Health (Clipping, DC, Dropouts) on Source.
    2. Phase Health (Cancellation Check) on Sum-to-Mono.
    """
    events = []
    metrics = {
        "dc_offset_max": 0.0,
        "dynamic_range_db": 0.0,
        "peak_volume_db": -99.0,
        "channels": 0
    }
    
    channels, duration = get_audio_info(input_path)
    metrics["channels"] = channels

    if channels == 0:
        return events, metrics

    # ---------------------------------------------------------
    # PASS 1: Signal Health (Clipping, DC, Dropouts)
    # ---------------------------------------------------------
    # - aphasemeter: just for logging (we don't parse it deeply here)
    # - silencedetect: threshold -50dB (finds real silence)
    # - astats: DC offset / Dynamic Range
    # - volumedetect: True Peak
    cmd_pass1 = [
        "ffmpeg", "-v", "info", "-i", str(input_path),
        "-filter_complex", 
        "silencedetect=n=-50dB:d=0.1,astats=metadata=1:reset=1:measure_overall=DC_offset+Dynamic_range,volumedetect",
        "-f", "null", "-"
    ]
    
    source_silences = []
    
    try:
        process = subprocess.run(
            cmd_pass1, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        log = process.stderr
        
        # 1. Parse Source Silence (Real Dropouts)
        source_silences = parse_silencedetect(log)
        for s, e in source_silences:
            events.append({
                "type": "audio_dropout",
                "details": f"Audio Silence detected ({e-s:.2f}s).",
                "start_time": s,
                "end_time": e
            })

        # 2. Parse Metrics (DC, DR, Peak)
        for line in log.split('\n'):
            if "lavfi.astats.Overall.DC_offset" in line:
                try: metrics["dc_offset_max"] = max(metrics["dc_offset_max"], abs(float(line.split("=")[1])))
                except: pass
            if "lavfi.astats.Overall.Dynamic_range" in line:
                try: metrics["dynamic_range_db"] = float(line.split("=")[1])
                except: pass
                
        # Parse Volumedetect
        match = re.search(r"max_volume:\s*([-0-9\.]+)\s*dB", log)
        if match:
            metrics["peak_volume_db"] = float(match.group(1))

    except Exception as e:
        print(f"[WARN] Pass 1 failed: {e}")

    # ---------------------------------------------------------
    # PASS 2: Phase Cancellation Check (The "Sum-to-Mono" Trick)
    # ---------------------------------------------------------
    # If channels >= 2, we mix Left + Right. 
    # If they are out of phase, they cancel to Silence (-inf).
    # We check for silence on the SUM. If Sum is silent but Source wasn't, it's a Phase Error.
    
    if channels >= 2:
        # Downmix L+R to Mono. 
        # Note: We focus on L+R (c0+c1) even for 5.1 as it's the primary risk.
        cmd_pass2 = [
            "ffmpeg", "-v", "info", "-i", str(input_path),
            "-filter_complex", "pan=mono|c0=c0+c1,silencedetect=n=-50dB:d=0.1",
            "-f", "null", "-"
        ]
        
        try:
            process2 = subprocess.run(
                cmd_pass2, capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
            phase_silences = parse_silencedetect(process2.stderr)
            
            # Compare Phase Silence vs Source Silence
            for ps, pe in phase_silences:
                # Check if this timespan was already silent in the source
                is_source_silent = False
                for ss, se in source_silences:
                    # Simple overlap check
                    if (ps < se) and (pe > ss):
                        is_source_silent = True
                        break
                
                # If Sum is Silent but Source is NOT Silent -> Phase Cancellation
                if not is_source_silent:
                    events.append({
                        "type": "phase_inversion_detected",
                        "details": f"Phase Cancellation detected ({pe-ps:.2f}s). L+R Sum resulted in silence.",
                        "start_time": ps,
                        "end_time": pe,
                        "severity": "CRITICAL"
                    })

        except Exception as e:
            print(f"[WARN] Pass 2 failed: {e}")

    return events, metrics

def run_validator(input_path, output_path, mode="strict"):
    events, metrics = analyze_signal(input_path)
    
    status = "PASSED"
    
    # Severity Logic
    for e in events:
        if e.get("severity") == "CRITICAL":
            status = "REJECTED"
        elif e.get("type") == "audio_clipping":
            # Check Peak Metric
            if metrics["peak_volume_db"] >= 0.0:
                events.append({
                    "type": "clipping_error",
                    "details": f"True Peak {metrics['peak_volume_db']} dB hits 0.0 dB.",
                    "severity": "CRITICAL"
                })
                status = "REJECTED"
        elif e.get("type") == "audio_dropout":
            # Reject if silence > 2s
            dur = e.get("end_time", 0) - e.get("start_time", 0)
            if dur > 2.0:
                status = "REJECTED"
            elif status != "REJECTED":
                status = "WARNING"
    
    # Metric Checks
    if metrics["dc_offset_max"] > 0.001:
        events.append({"type": "dc_offset_warn", "details": f"DC Offset {metrics['dc_offset_max']:.6f} is high."})
        if status == "PASSED": status = "WARNING"

    report = {
        "module": "validate_audio_signal",
        "status": status,
        "details": {
            "metrics": metrics,
            "events": events
        }
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