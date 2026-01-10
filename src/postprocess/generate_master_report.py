import argparse
import json
import time
from pathlib import Path

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
        "modules": {}
    }

    # Priorities for status bubbling (REJECTED overrides everything)
    # Higher number = Higher severity
    status_priority = {
        "CRASHED": 4, 
        "REJECTED": 3, 
        "CORRUPT": 3, 
        "WARNING": 2, 
        "PASSED": 1, 
        "UNKNOWN": 0,
        "SKIPPED": 0
    }
    max_severity = 0

    print(f"Aggregating {len(args.inputs)} reports...")

    for report_path in args.inputs:
        path = Path(report_path)
        if not path.exists():
            continue
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Use the module name from inside the JSON, or fallback to filename
            module_name = data.get("module", path.stem)
            status = data.get("effective_status", data.get("status", "UNKNOWN"))
            
            # Add to master dict
            master_data["modules"][module_name] = data
            
            # Update Global Status
            severity = status_priority.get(status, 0)
            if severity > max_severity:
                max_severity = severity
                master_data["overall_status"] = status
                
        except Exception as e:
            print(f"[WARN] Failed to parse {path}: {e}")

    # Save Master Report
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(master_data, f, indent=4)
        
    print(f"Master Report generated: {args.output}")

if __name__ == "__main__":
    main()