import json
import subprocess
import sys
import numpy as np
from pathlib import Path

# Try to import config, fallback to defaults if running standalone validation without full env
try:
    from src.utils.logger import setup_logger
    logger = setup_logger("validate_signal")
except ImportError:
    import logging
    logger = logging.getLogger("validate_signal")

def load_profile(mode="strict"):
    """
    Loads signal thresholds from signal_profiles.json
    """
    default_profile = {
        "vrep_threshold": 5.0,
        "ymin_safe": 16,
        "ymax_safe": 235,
        "sat_max": 110,
        "confidence_threshold": 0.8,
        "window_sec": 2.0
    }
    
    try:
        config_path = Path(__file__).parent.parent.parent / "config" / "signal_profiles.json"
        if config_path.exists():
            with open(config_path, "r") as f:
                data = json.load(f)
                profiles = data.get("profiles", {})
                
                # Map mode to profile key
                key = "STRICT"
                if mode.lower() == "netflix": key = "NETFLIX_HD"
                if mode.lower() == "youtube": key = "YOUTUBE"
                
                if key in profiles:
                    return profiles[key].get("validate_signal", default_profile)
    except Exception as e:
        logger.warning(f"Could not load signal_profiles.json: {e}. Using defaults.")
        
    return default_profile

def calculate_confidence(val, limit, is_max=True):
    """
    Calculates a confidence score (0.0 - 1.0) for a violation.
    Higher score = High confidence it's a real issue.
    """
    # Logic: If value exceeds limit by a certain margin, confidence increases.
    # Ex: Limit 235. Value 240 -> Low confidence (could be transient). Value 255 -> High.
    delta = abs(val - limit)
    if delta == 0: return 0.0
    
    # Sigmoid-like scaling
    # For Broadcast: Delta 20 (e.g. 255 vs 235) should be 1.0
    score = min(delta / 20.0, 1.0)
    return round(score, 2)

def validate_signal(input_path, output_path, config=None, mode="strict"):
    profile = load_profile(mode)
    
    report = {
        "status": "PASS",
        "details": {
            "broadcast_illegal_frames": 0,
            "saturation_warnings": 0,
            "signal_min_y": 255,
            "signal_max_y": 0,
            "issues": []
        }
    }

    Y_MIN_SAFE = profile.get("ymin_safe", 16)
    Y_MAX_SAFE = profile.get("ymax_safe", 235)
    SAT_MAX_SAFE = profile.get("sat_max", 110)
    CONF_TH = profile.get("confidence_threshold", 0.8)
    WINDOW_SEC = 2.0 # Fixed for now or load from config
    
    events = [] 

    try:
        input_p = Path(input_path).resolve()
        work_dir = input_p.parent
        file_name = input_p.name
        
        cmd = [
            "ffprobe", "-v", "error",
            "-f", "lavfi",
            "-i", f"movie={file_name},signalstats",
            "-select_streams", "v:0",
            "-show_entries", "frame=pkt_pts_time : frame_tags=YMIN,YMAX,SATMAX",
            "-of", "json"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(work_dir))
        
        if result.returncode != 0:
            raise Exception(f"FFprobe failed: {result.stderr}")

        data = json.loads(result.stdout)
        frames = data.get("frames", [])

        if not frames:
            report["status"] = "WARNING"
            report["details"]["issues"].append("No frame data extracted.")
            with open(output_path, "w") as f: json.dump(report, f, indent=4)
            return

        illegal_count = 0
        sat_warn_count = 0
        min_y_found = 255
        max_y_found = 0
        
        # Windowing State
        window_events = [] # list of (time, type, val)
        
        for frame in frames:
            tags = frame.get("tags", {})
            ts = float(frame.get("pkt_pts_time", 0.0))
            
            try:
                ymin = int(tags.get("YMIN", 16))
                ymax = int(tags.get("YMAX", 235))
                satmax = int(tags.get("SATMAX", 0))

                min_y_found = min(min_y_found, ymin)
                max_y_found = max(max_y_found, ymax)

                # Collect Raw Violations
                if ymin < Y_MIN_SAFE:
                    conf = calculate_confidence(ymin, Y_MIN_SAFE, False) * 100.0
                    window_events.append({"t": ts, "type": "min_under", "val": ymin, "conf": conf})
                    illegal_count += 1
                    
                if ymax > Y_MAX_SAFE:
                    conf = calculate_confidence(ymax, Y_MAX_SAFE, True) * 100.0
                    window_events.append({"t": ts, "type": "max_over", "val": ymax, "conf": conf})
                    illegal_count += 1
                    
                if satmax > SAT_MAX_SAFE:
                    conf = calculate_confidence(satmax, SAT_MAX_SAFE, True) * 100.0
                    window_events.append({"t": ts, "type": "sat_over", "val": satmax, "conf": conf})
                    sat_warn_count += 1

                # Clean old window events
                cutoff = ts - WINDOW_SEC
                window_events = [e for e in window_events if e["t"] > cutoff]
                
                # Check Density in Window
                # If we have > 10 illegal frames in last 2 seconds with High Confidence
                high_conf_errors = [e for e in window_events if e["conf"] >= (CONF_TH * 100.0) and e["type"] in ["min_under", "max_over"]]
                
                if len(high_conf_errors) > 10:
                    # Trigger an Event if not already in one
                    if not events or (events[-1]["end_time"] < ts - 0.5):
                        events.append({
                            "type": "broadcast_illegal_burst",
                            "start_time": window_events[0]["t"], # approx
                            "end_time": ts,
                            "severity": "REJECTED" if mode == "strict" else "WARNING",
                            "details": f"sustained broadcast violation (>10 frames/2s). Worst: {high_conf_errors[-1]['val']}",
                            "confidence": max([e["conf"] for e in high_conf_errors])
                        })
                    else:
                        # Extend
                        events[-1]["end_time"] = ts

            except ValueError:
                continue
        
        report["details"]["signal_min_y"] = min_y_found
        report["details"]["signal_max_y"] = max_y_found
        report["details"]["broadcast_illegal_frames"] = illegal_count
        report["details"]["saturation_warnings"] = sat_warn_count
        report["details"]["total_frames"] = len(frames)
        report["events"] = events

        # Final Status determination
        if events:
            # If any REJECTED event exists
            if any(e["severity"] == "REJECTED" for e in events):
                report["status"] = "REJECTED"
            else:
                report["status"] = "WARNING"
                
        # Issues for summary
        if illegal_count > 0:
             report["details"]["issues"].append(f"Found {illegal_count} frames outside broadcast range.")

    except Exception as e:
        report["status"] = "CRASHED"
        report["details"]["error"] = str(e)

    with open(output_path, "w") as f:
        json.dump(report, f, indent=4)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default="strict") # strict, netflix, youtube
    parser.add_argument("--hwaccel", default="none")
    args = parser.parse_args()
    
    validate_signal(args.input, args.output, None, args.mode)
