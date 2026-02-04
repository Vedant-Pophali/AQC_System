import argparse
import json
import subprocess
import sys
import shlex
from pathlib import Path
from src.utils.logger import setup_logger

logger = setup_logger("validate_analog")

def get_vrep_metrics(input_path: str):
    """
    Uses FFmpeg's 'signalstats' filter to calculate Vertical Repetition (VREP).
    Research Standard: VREP > 5.0 indicates analog TBC dropout / Head Clog.
    """
    # We use ffprobe to run the filter and dump frame tags to JSON
    # Filter syntax: movie=filename.mp4,signalstats
    # We must escape the path for the complex filter argument
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
        # This scans the whole file. For optimization in Sprint 4, we can segment this.
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        frames = data.get("frames", [])
        issues = []
        
        for f in frames:
            tags = f.get("tags", {})
            vrep = float(tags.get("lavfi.signalstats.VREP", 0.0))
            time = float(f.get("pkt_pts_time", 0.0))
            
            # RESEARCH THRESHOLD: > 5.0 implies TBC Correction Event
            if vrep > 5.0:
                issues.append({
                    "timestamp": time,
                    "metric": "VREP",
                    "value": vrep,
                    "threshold": 5.0,
                    "details": "Potential Analog Dropout / Head Clog"
                })
                
        return issues

    except Exception as e:
        logger.error(f"VREP Analysis Failed: {e}")
        return []

def run_validator(input_path, output_path, mode="strict"):
    report = {
        "module": "validate_analog",
        "status": "PASSED",
        "events": [],
        "metrics": {"vrep_spikes": 0}
    }
    
    # Run Analysis
    issues = get_vrep_metrics(input_path)
    
    # Aggregation
    report["events"] = issues
    report["metrics"]["vrep_spikes"] = len(issues)
    
    if len(issues) > 0:
        report["status"] = "WARNING"
        # If the tape is really chewed up (>20 drops), reject it.
        if len(issues) > 20:
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