import argparse
import json
import time
from pathlib import Path

def stitch_events(events, tolerance=0.1):
    """
    Merges overlapping or adjacent events of the same type.
    """
    if not events: return []
    
    # Sort by Type, then Start Time
    sorted_events = sorted(events, key=lambda x: (x.get("type", "unknown"), x.get("start_time", 0)))
    
    stitched = []
    if not sorted_events: return []
    
    current = sorted_events[0]
    
    for next_evt in sorted_events[1:]:
        # Check if same type
        if current.get("type") == next_evt.get("type"):
            # Check overlap or adjacency
            # If (Start_Next <= End_Curr + Tolerance)
            curr_end = current.get("end_time", 0)
            next_start = next_evt.get("start_time", 0)
            
            if next_start <= (curr_end + tolerance):
                # Merge: Extend current end time
                current["end_time"] = max(curr_end, next_evt.get("end_time", 0))
                # Append details if unique
                if next_evt.get("details") not in current.get("details", ""):
                    current["details"] += f" | {next_evt.get('details')}"
                continue
        
        # No merge, push current and move on
        stitched.append(current)
        current = next_evt
    
    stitched.append(current)
    
    # Final sort by time for the report
    return sorted(stitched, key=lambda x: x.get("start_time", 0))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="+", required=True, help="List of JSON report paths")
    parser.add_argument("--output", required=True, help="Path to save Master JSON")
    parser.add_argument("--profile", default="strict")
    args = parser.parse_args()

    master_data = {
        "timestamp": time.ctime(),
        "profile": args.profile,
        "overall_status": "PASSED",
        "modules": {},
        "aggregated_events": [] # New consolidated timeline
    }

    # Priorities for status bubbling
    status_priority = {
        "CRASHED": 4, "REJECTED": 3, "CORRUPT": 3, 
        "WARNING": 2, "PASSED": 1, "UNKNOWN": 0, "SKIPPED": 0
    }
    max_severity = 0
    
    all_raw_events = []

    print(f"Aggregating {len(args.inputs)} reports...")

    for report_path in args.inputs:
        path = Path(report_path)
        if not path.exists():
            continue
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            module_name = data.get("module", path.stem)
            status = data.get("effective_status", data.get("status", "UNKNOWN"))
            
            # 1. Module Aggregation
            master_data["modules"][module_name] = data
            
            # Update Status
            severity = status_priority.get(status, 0)
            if severity > max_severity:
                max_severity = severity
                master_data["overall_status"] = status
            
            # 2. Collect Events for Stitching
            # Handle potential segment offsets (for future scalability)
            segment_offset = data.get("segment_offset_sec", 0.0)
            
            raw_events = []
            if "events" in data and isinstance(data["events"], list):
                raw_events.extend(data["events"])
            
            if "details" in data and isinstance(data["details"], dict):
                if "events" in data["details"] and isinstance(data["details"]["events"], list):
                    raw_events.extend(data["details"]["events"])

            for e in raw_events:
                # Normalize timestamps
                if "start_time" in e: e["start_time"] += segment_offset
                if "end_time" in e: e["end_time"] += segment_offset
                
                e["source_module"] = module_name
                all_raw_events.append(e)
                
        except Exception as e:
            print(f"[WARN] Failed to parse {path}: {e}")

    # 3. Stitch and Deduplicate
    master_data["aggregated_events"] = stitch_events(all_raw_events)

    # Save Master Report
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(master_data, f, indent=4)
        
    print(f"Master Report generated: {args.output}")

if __name__ == "__main__":
    main()