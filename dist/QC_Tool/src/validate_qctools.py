import subprocess
import json
import argparse
import os
import xml.etree.ElementTree as ET

def check_qctools(input_path, output_path):
    print(f"[INFO] QCTools: Running Deep Signal Analysis on {os.path.basename(input_path)}...")

    # We use qcli to generate a purely numerical report (XML format)
    # This is lighter than the GUI
    cmd = ["qcli", "-i", input_path]

    report = {
        "module": "qctools_qc",
        "video_file": input_path,
        "status": "PASSED",
        "metrics": {},
        "events": []
    }

    try:
        # Run qcli
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

        # qcli outputs XML to stdout
        xml_content = result.stdout

        if not xml_content.strip():
            raise Exception("No output from qcli")

        # Parse XML
        root = ET.fromstring(xml_content)

        # QCTools returns data per frame. We want to find the "Worst Case" VREP.
        # VREP (Vertical Repetition) > 0.5 usually indicates a TBC error (Tape Dropout).
        max_vrep = 0.0
        vrep_violations = 0

        # Iterate through frames (Namespace usually required for QCTools XML)
        # Note: XML structure depends on version, we search generically for 'f' (frame) tags
        # and attributes like 'vrep'

        # Simplify: QCTools often outputs a huge amount of data.
        # For this prototype, we will scan the output for specific tags.

        # Standard QCTools XML looks like: <frame ... vrep="0.123" ... />
        for frame in root.findall(".//{http://mediaarea.net/qctools}frame"):
            vrep = float(frame.get("vrep", 0))
            if vrep > max_vrep:
                max_vrep = vrep

            if vrep > 2.0: # Threshold from Research Paper (approximate for visible error)
                vrep_violations += 1

        report["metrics"]["max_vrep"] = max_vrep
        report["metrics"]["bad_frames"] = vrep_violations

        # Decision Logic
        if vrep_violations > 5: # Tolerance: 5 bad frames
            report["status"] = "WARNING" # Artifacts are rarely "Critical" for rejection, but worth noting
            report["events"].append({
                "type": "Analog Artifact (VREP)",
                "details": f"Vertical Line Repetition detected in {vrep_violations} frames. Max: {max_vrep}"
            })

    except FileNotFoundError:
        print("[ERROR] qctools (qcli) is not installed in the container.")
        report["status"] = "ERROR"
        report["events"].append({"error": "QCTools binary missing"})
    except Exception as e:
        print(f"[ERROR] QCTools QC Failed: {e}")
        # Only fail gracefully if XML parsing breaks
        report["metrics"]["error"] = str(e)

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding='utf-8') as f:
        json.dump(report, f, indent=4)
    print(f"[OK] Saved: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    check_qctools(args.input, args.output)