import json
import subprocess
import sys
from pathlib import Path

def validate_signal(input_path, output_path, config=None):
    """
    Implements Archival Signal Diagnostics using FFmpeg 'signalstats' filter.
    Aligns with AQC Blueprint (Section 3.1 & 7):
    - Broadcast Legal: Checks if Y is within [16, 235].
    - Saturation: Checks if SATMAX <= 110 (safe limit approximation).
    - Signal Health: Tracks signal variance/stability.
    """
    
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

    # Blueprint Requirement: "Rigorous boundary conditions" (Section 7)
    # Broadcast Safe Range (8-bit)
    Y_MIN_SAFE = 16
    Y_MAX_SAFE = 235
    SAT_MAX_SAFE = 110  # Approx safe saturation limit (varies by standard, but good warning threshold)
    
    events = [] # For timeline visualization

    try:
        # Construct ffprobe command with signalstats
        # We process a subset of frames or full file depending on performance needs.
        # For full accuracy (Blueprint mandates frame-accurate), we run on the whole file.
        # Command: ffprobe -v error -f lavfi -i movie=input.mp4,signalstats -select_streams v:0 -show_entries frame_tags=YMIN,YMAX,SATMAX -of json
        
        # ROBUST FIX for Windows absolute paths in movie= filter:
        # Instead of fighting escaping, we change CWD to the file's directory
        # and use the relative filename.
        
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

        # Use Popen to stream output if file is large, but for simplicity/robustness we capture here.
        # WARNING: Large files can produce huge JSON. In a real 'distributed' layer (Blueprint Sec 6), this would be chunked.
        # For now, we assume reasonable clip sizes or accept memory usage.
        # CRITICAL: cwd must be work_dir for movie={file_name} to work
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(work_dir))
        
        if result.returncode != 0:
            raise Exception(f"FFprobe failed: {result.stderr}")

        data = json.loads(result.stdout)
        frames = data.get("frames", [])

        if not frames:
            report["status"] = "WARNING"
            report["details"]["issues"].append("No frame data extracted from signalstats.")
            with open(output_path, "w") as f:
                json.dump(report, f, indent=4)
            return

        illegal_count = 0
        sat_warn_count = 0
        min_y_found = 255
        max_y_found = 0

        # Event Coalescence State
        current_event = None
        
        for frame in frames:
            tags = frame.get("tags", {})
            ts = float(frame.get("pkt_pts_time", 0.0))
            
            try:
                ymin = int(tags.get("YMIN", 16)) # Default to safe if missing
                ymax = int(tags.get("YMAX", 235))
                satmax = int(tags.get("SATMAX", 0))

                min_y_found = min(min_y_found, ymin)
                max_y_found = max(max_y_found, ymax)

                # Check Broadcast Legal (Section 7 - Table 3)
                is_illegal = (ymin < Y_MIN_SAFE or ymax > Y_MAX_SAFE)
                is_saturated = (satmax > SAT_MAX_SAFE)
                
                # Update Stats
                if is_illegal: illegal_count += 1
                if is_saturated: sat_warn_count += 1

                # Timeline Event Logic (Focus on Broadcast Legal for now)
                # We start an event if illegal, and extend it if consecutive.
                if is_illegal:
                    if current_event and current_event["type"] == "broadcast_illegal":
                        # Extend existing event
                        current_event["end_time"] = ts
                        # Keep worst observed value in details
                        if ymin < 16: current_event["details"] = f"Luma Undershoot (Min: {ymin})"
                        if ymax > 235: current_event["details"] = f"Luma Overshoot (Max: {ymax})"
                    else:
                        # Close previous if different type (not handling mixed yet for simplicity)
                        if current_event: events.append(current_event)
                        
                        # Start new event
                        current_event = {
                            "type": "broadcast_illegal",
                            "start_time": ts,
                            "end_time": ts,
                            "severity": "WARNING", # escalate to REJECTED later if needed
                            "details": f"Broadcast Violation (Y: {ymin}-{ymax})"
                        }
                elif is_saturated:
                     # For saturation, we treat it similarly (can add mixed logic later)
                     if current_event and current_event["type"] == "saturation_warning":
                        current_event["end_time"] = ts
                     else:
                        if current_event: events.append(current_event)
                        current_event = {
                            "type": "saturation_warning",
                            "start_time": ts,
                            "end_time": ts,
                            "severity": "WARNING",
                            "details": f"High Saturation ({satmax})"
                        }
                else:
                    # Frame is fine, close any open event
                    if current_event:
                        events.append(current_event)
                        current_event = None

            except ValueError:
                continue
        
        # Close any trailing event
        if current_event:
            events.append(current_event)

        report["details"]["signal_min_y"] = min_y_found
        report["details"]["signal_max_y"] = max_y_found
        report["details"]["broadcast_illegal_frames"] = illegal_count
        report["details"]["saturation_warnings"] = sat_warn_count
        report["details"]["total_frames"] = len(frames)
        report["events"] = events

        # Determine Status based on Thresholds
        issues = []
        if illegal_count > 0:
            # Calculate percentage
            pct = (illegal_count / len(frames)) * 100
            if pct > 10.0: # If >10% of frames are illegal, it's a FAIL. Else Warning.
                report["status"] = "REJECTED"
                issues.append(f"Excessive Broadcast Level Violations: {pct:.2f}% frames outside [16-235].")
                # Escalate events to REJECTED
                for e in report["events"]: 
                    if e["type"] == "broadcast_illegal": e["severity"] = "REJECTED"
            else:
                if report["status"] != "REJECTED": report["status"] = "WARNING"
                issues.append(f"Minor Broadcast Level Violations: {pct:.2f}% frames.")

        if sat_warn_count > 0:
             pct = (sat_warn_count / len(frames)) * 100
             if pct > 5.0:
                 if report["status"] != "REJECTED": report["status"] = "WARNING"
                 issues.append(f"High Saturation Detected in {pct:.2f}% of frames.")

        report["details"]["issues"] = issues

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
    parser.add_argument("--mode", default="strict") # Not used yet but required by contract
    parser.add_argument("--hwaccel", default="none")
    args = parser.parse_args()
    
    validate_signal(args.input, args.output, args.mode)
