import argparse
import json
import subprocess
import sys
from pathlib import Path

# Try to import config, fallback to defaults
try:
    from src.utils.logger import setup_logger
    logger = setup_logger("validate_analog")
except ImportError:
    import logging
    logger = logging.getLogger("validate_analog")

def load_profile(mode="strict"):
    default_profile = {
        "vrep_threshold": 5.0,
        "vrep_persistence_frames": 3
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
                    return profiles[key].get("validate_signal", default_profile) # Use signal profile for VREP
    except Exception:
        pass
    return default_profile

def get_vrep_metrics(input_path: str, profile: dict):
    """
    Uses FFmpeg's 'signalstats' filter to calculate Vertical Repetition (VREP).
    Research Standard: VREP > 5.0 indicates analog TBC dropout / Head Clog.
    """
    safe_path = Path(input_path).as_posix().replace(":", "\\:")
    
    cmd = [
        "ffprobe",
        "-v", "error",
        "-f", "lavfi",
        "-i", f"movie={safe_path},signalstats",
        "-show_entries", "frame=pkt_pts_time:frame_tags=lavfi.signalstats.VREP",
        "-of", "json"
    ]

    logger.info(f"Scanning for Analog Artifacts (VREP)...")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        frames = data.get("frames", [])
        issues = []
        
        # State detection
        TH_VREP = profile.get("vrep_threshold", 5.0)
        TH_PERSIST = profile.get("vrep_persistence_frames", 3)
        
        spike_sequence = []
        timeseries = [] # For Plotly Dashboard
        
        for f in frames:
            tags = f.get("tags", {})
            vrep = float(tags.get("lavfi.signalstats.VREP", 0.0))
            time = float(f.get("pkt_pts_time", 0.0))
            
            # Sub-sample timeseries to avoid huge JSON (e.g., store only if > 2.0 or every 10th frame)
            # OR store all for short clips. 
            if vrep > 2.0:
                 timeseries.append({"t": time, "val": vrep})
            
            if vrep > TH_VREP:
                spike_sequence.append((time, vrep))
            else:
                # Sequence ended, check if it was a dropout event
                if len(spike_sequence) >= TH_PERSIST:
                    # Log event
                    start = spike_sequence[0][0]
                    peak = max([x[1] for x in spike_sequence])
                    issues.append({
                        "timestamp": start,
                        "metric": "VREP",
                        "value": peak,
                        "duration_frames": len(spike_sequence),
                        "details": f"Analog Dropout / TBC Compensation (VREP Spikes: {len(spike_sequence)} frames)"
                    })
                spike_sequence = []
                
        # Trailing
        if len(spike_sequence) >= TH_PERSIST:
             start = spike_sequence[0][0]
             peak = max([x[1] for x in spike_sequence])
             issues.append({
                "timestamp": start,
                "metric": "VREP",
                "value": peak,
                "duration_frames": len(spike_sequence),
                "details": f"Analog Dropout / TBC Compensation (VREP Spikes: {len(spike_sequence)} frames)"
            })

        return issues, timeseries

    except Exception as e:
        logger.error(f"VREP Analysis Failed: {e}")
        return [], []

def run_validator(input_path, output_path, mode="strict"):
    profile = load_profile(mode)
    
    report = {
        "module": "validate_analog",
        "status": "PASSED",
        "events": [],
        "metrics": {"vrep_spikes": 0},
        "timeseries": []
    }
    
    # Run Analysis
    issues, timeseries = get_vrep_metrics(input_path, profile)
    
    # Aggregation
    report["events"] = issues
    report["metrics"]["vrep_spikes"] = len(issues)
    report["timeseries"] = timeseries
    
    if len(issues) > 0:
        report["status"] = "WARNING"
        if len(issues) > 10: # If tape is really chewed up
            report["status"] = "REJECTED"
            
    # Write Report
    with open(output_path, "w") as f:
        json.dump(report, f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default="strict")
    args = parser.parse_args()
    
    run_validator(args.input, args.output, args.mode)