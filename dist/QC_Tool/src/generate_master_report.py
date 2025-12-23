import json
import argparse
import os
import sys

# Ensure proper encoding for Windows consoles
sys.stdout.reconfigure(encoding='utf-8')

def load_json(path):
    """Safely loads a JSON file, returns None on failure."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"   [WARN] Failed to load report: {path} ({e})")
        return None

def generate_master(inputs, output_file):
    print("   >>> Aggregating Reports...")

    master = {
        "metadata": {"filename": "Unknown", "duration": 0},
        "overall_status": "PASSED",
        "modules": {}
    }

    loaded_count = 0

    for path in inputs:
        data = load_json(path)
        if not data:
            continue

        # 1. Extract Module Name (e.g., "signal_qc")
        module = data.get("module", "unknown")
        status = data.get("status", "UNKNOWN")

        # 2. Add to Master Record
        master["modules"][module] = data
        loaded_count += 1

        # [Enhancement] Console Feedback
        print(f"      + Loaded [{module}]: {status}")

        # 3. Aggregation Logic (Priority: ERROR > REJECTED > WARNING > PASSED)
        if status == "ERROR":
            master["overall_status"] = "ERROR"
        elif status == "REJECTED" and master["overall_status"] != "ERROR":
            master["overall_status"] = "REJECTED"
        elif status == "WARNING" and master["overall_status"] == "PASSED":
            master["overall_status"] = "WARNING"

        # 4. Attempt to grab metadata from any module that has it
        if master["metadata"]["filename"] == "Unknown":
            vf = data.get("video_file")
            if vf:
                master["metadata"]["filename"] = os.path.basename(vf)

    # Fail-safe: If no modules loaded, something is wrong
    if loaded_count == 0:
        master["overall_status"] = "ERROR"
        print("   [ERROR] No valid module reports were loaded.")

    # 5. Save Master Report
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(master, f, indent=4)
        print(f"   [SUCCESS] Master Report saved: {output_file}")
    except Exception as e:
        print(f"   [CRITICAL] Failed to write Master Report: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # nargs='+' allows accepting multiple file paths dynamically
    parser.add_argument("--inputs", nargs="+", required=True, help="List of JSON report paths")
    parser.add_argument("--output", required=True, help="Output path for Master Report")
    args = parser.parse_args()

    generate_master(args.inputs, args.output)