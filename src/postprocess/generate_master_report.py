import argparse
import json
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# UTF-8 safety
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

def generate_report_hash(data):
    """Generates a unique hash for the report content."""
    s = json.dumps(data, sort_keys=True).encode("utf-8")
    return hashlib.sha256(s).hexdigest()

def aggregate_reports(input_paths, output_path, profile_name):
    master_data = {
        "metadata": {
            "generated_on": datetime.now(timezone.utc).isoformat(),
            "profile": profile_name,
            "tool": "AQC",
            "report_hash": ""
        },
        "overall_status": "PASSED",
        "ci_exit_code": 0,
        "modules": {},
        "known_deviations": []
    }

    # Priority logic: REJECTED > ERROR > WARNING > PASSED
    status_priority = {
        "ERROR": 4,
        "CRASHED": 4,
        "REJECTED": 3,
        "WARNING": 2,
        "PASSED": 1,
        "UNKNOWN": 0
    }
    
    highest_severity = 0

    for path_str in input_paths:
        path = Path(path_str)
        if not path.exists():
            continue
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                module_data = json.load(f)
                
            module_name = module_data.get("module", "unknown")
            module_status = module_data.get("status", "UNKNOWN")
            
            # Add to master
            master_data["modules"][module_name] = module_data
            
            # Add "effective_status" to module if missing
            if "effective_status" not in module_data:
                master_data["modules"][module_name]["effective_status"] = module_status

            # Calculate overall severity
            severity = status_priority.get(module_status, 0)
            if severity > highest_severity:
                highest_severity = severity
                master_data["overall_status"] = module_status

        except Exception as e:
            print(f"[WARN] Failed to merge report {path}: {e}")

    # Set Exit Code logic
    # 0 = OK/Warning
    # 1 = Rejected/Error
    if highest_severity >= 3: # REJECTED or ERROR
        master_data["ci_exit_code"] = 1
    
    # Hash the report
    master_data["metadata"]["report_hash"] = generate_report_hash(master_data["modules"])

    # Write Output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(master_data, f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="+", required=True, help="List of component JSON reports")
    parser.add_argument("--output", required=True, help="Path to Master JSON")
    parser.add_argument("--profile", default="strict")
    args = parser.parse_args()

    aggregate_reports(args.inputs, args.output, args.profile)