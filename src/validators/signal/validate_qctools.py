import subprocess
import json
import argparse
import os
import sys
import xml.etree.ElementTree as ET
from statistics import mean

# -------------------------
# CONSTANTS & CONFIG
# -------------------------
# VREP (Vertical Repetition) suggests video line duplication (TBC errors).
# Source [306]: "detects the repetition of video lines."
VREP_THRESHOLD = 2.0  # Conservative threshold (lines per frame)
VREP_SPIKE_WINDOW = 5  # Number of consecutive frames to trigger an event

# SAT (Saturation) - Check for illegal broadcast levels (optional but recommended)
SATURATION_THRESHOLD = 130  # 8-bit scale approx

# -------------------------
# Utilities
# -------------------------
def get_duration(path):
    """Best-effort duration probe."""
    try:
        p = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path],
            capture_output=True, text=True
        )
        return float(json.loads(p.stdout)["format"]["duration"])
    except Exception:
        return 0.0

def parse_qctools_report(xml_content):
    """
    Parses QCTools XML output to extract frame-level metrics.
    Focuses on VREP (Vertical Repetitions) and SAT (Saturation).
    """
    try:
        root = ET.fromstring(xml_content)
        frames = []

        # QCTools QCLI XML structure usually puts frames under a specific namespace or simple tag
        # We look for 'frame' tags.
        for frame_elem in root.findall(".//frame"):
            metrics = {}

            # Extract Time
            pkt_pts_time = frame_elem.get("pkt_pts_time")
            if pkt_pts_time:
                metrics["time"] = float(pkt_pts_time)
            else:
                continue # Skip if no timestamp

            # Extract VREP (Vertical Line Repetitions)
            # Tag format often: <tag name="vrep" value="0.2" />
            # Or direct attributes depending on version. We assume QCLI XML format.
            for tag in frame_elem:
                key = tag.tag
                val = tag.text

                # Check for VREP (Vertical Repetition)
                if "vrep" in key.lower():
                    try:
                        metrics["vrep"] = float(val)
                    except (ValueError, TypeError):
                        metrics["vrep"] = 0.0

                # Check for Broadcast Illegal Saturation (Sat)
                if "sat" in key.lower() and "max" in key.lower():
                    try:
                        metrics["sat_max"] = float(val)
                    except (ValueError, TypeError):
                        metrics["sat_max"] = 0.0

            if "time" in metrics:
                frames.append(metrics)

        return frames
    except ET.ParseError:
        return []

# -------------------------
# Validator Logic
# -------------------------
def validate_qctools(input_path, output_path):
    """
    Executes QCTools (qcli) and parses signal metrics.

    Implements:
    1. VREP Analysis for TBC/Analog Errors
    2. Signal Integrity Checks [cite: 286]
    """
    duration = get_duration(input_path)

    report = {
        "module": "qctools_qc",
        "video_file": input_path,
        "status": "PASSED",
        "metrics": {},
        "events": []
    }

    # 1. Run QCLI
    # We output to a temporary XML file to parse
    temp_xml = output_path + ".temp.xml"

    cmd = ["qcli", "-i", input_path, "--output-format", "xml"]

    try:
        with open(temp_xml, "w", encoding="utf-8") as f_out:
            result = subprocess.run(cmd, stdout=f_out, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            report["status"] = "ERROR"
            report["events"].append({
                "type": "qctools_execution_error",
                "start_time": 0.0,
                "end_time": 0.0,
                "details": f"QCLI failed with exit code {result.returncode}"
            })
            _write(report, output_path)
            if os.path.exists(temp_xml): os.remove(temp_xml)
            return

    except FileNotFoundError:
        report["status"] = "ERROR"
        report["events"].append({
            "type": "qctools_unavailable",
            "start_time": 0.0,
            "end_time": 0.0,
            "details": "qcli executable not found in PATH"
        })
        _write(report, output_path)
        return
    except Exception as e:
        report["status"] = "ERROR"
        report["events"].append({
            "type": "qctools_runtime_error",
            "start_time": 0.0,
            "end_time": 0.0,
            "details": str(e)
        })
        _write(report, output_path)
        return

    # 2. Parse Results
    try:
        with open(temp_xml, "r", encoding="utf-8") as f_in:
            xml_content = f_in.read()

        frames = parse_qctools_report(xml_content)
    except Exception as e:
        frames = []
        report["events"].append({
            "type": "xml_parse_error",
            "details": str(e)
        })
    finally:
        if os.path.exists(temp_xml):
            os.remove(temp_xml)

    if not frames:
        report["status"] = "ERROR"
        report["events"].append({
            "type": "qctools_no_data",
            "details": "No frame data extracted from QCLI output"
        })
        _write(report, output_path)
        return

    # 3. Analyze Metrics (VREP & Saturation)
    vrep_values = [f.get("vrep", 0.0) for f in frames]
    sat_values = [f.get("sat_max", 0.0) for f in frames]

    avg_vrep = mean(vrep_values) if vrep_values else 0.0

    report["metrics"] = {
        "vrep_avg": round(avg_vrep, 4),
        "vrep_max": round(max(vrep_values), 4) if vrep_values else 0.0,
        "sat_max_peak": round(max(sat_values), 4) if sat_values else 0.0
    }

    # 4. Detect Defects

    # Event: TBC Error / VREP Spikes
    # "Significant peaks in VREP indicate periods of TBC activity" [cite: 390]
    consecutive_bad_frames = 0
    start_time = None

    for i, frame in enumerate(frames):
        vrep = frame.get("vrep", 0.0)
        t = frame.get("time", 0.0)

        if vrep > VREP_THRESHOLD:
            if start_time is None:
                start_time = t
            consecutive_bad_frames += 1
        else:
            if start_time is not None and consecutive_bad_frames >= VREP_SPIKE_WINDOW:
                report["events"].append({
                    "type": "analog_artifact_vrep",
                    "start_time": round(start_time, 3),
                    "end_time": round(t, 3),
                    "details": f"Vertical Line Repetition (TBC Error) detected. Peak VREP > {VREP_THRESHOLD}"
                })
                report["status"] = "REJECTED"

            # Reset
            start_time = None
            consecutive_bad_frames = 0

    _write(report, output_path)

def _write(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QCTools Signal Validator")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    validate_qctools(
        input_path=args.input,
        output_path=args.output
    )