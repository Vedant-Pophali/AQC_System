import subprocess
import sys
import json
import argparse
import time
import os

def check_structure(input_path, output_path, config_path):
    print(f"[INFO] Structure QC: Scanning {os.path.basename(input_path)}...")

    # 1. Load Config
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            strict_mode = config.get("structure_qc", {}).get("strict_mode", True)
    except:
        strict_mode = True

    # 2. THE PROBE (Quick Header Scan)
    probe_cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "format=duration,size,bit_rate:stream=codec_name,width,height",
        "-of", "json",
        input_path
    ]

    report = {
        "module": "structure_qc",
        "video_file": input_path,
        "status": "UNKNOWN",
        "events": [],
        "metrics": {}
    }

    try:
        # Run Quick Scan
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, encoding='utf-8')

        if probe_result.returncode != 0:
            report["status"] = "REJECTED"
            report["events"].append({
                "type": "Container Corruption",
                "start_time": 0,
                "error": "Header Read Failed",
                "details": probe_result.stderr.strip()
            })
            save_report(report, output_path)
            return

        # Parse Data
        data = json.loads(probe_result.stdout)
        format_info = data.get("format", {})

        # Metrics
        report["metrics"] = {
            "file_size_bytes": format_info.get("size"),
            "duration_sec": format_info.get("duration"),
            "bitrate": format_info.get("bit_rate")
        }

        # 3. THE DEEP SCAN (Stream Integrity)
        print("[INFO] Running Deep Stream Analysis (this may take time)...")
        deep_scan_cmd = [
            "ffmpeg",
            "-v", "error",
            "-i", input_path,
            "-f", "null",
            "-"
        ]

        scan_result = subprocess.run(deep_scan_cmd, capture_output=True, text=True, encoding='utf-8')

        if scan_result.returncode != 0 or len(scan_result.stderr) > 0:
            report["status"] = "REJECTED"
            errors = scan_result.stderr.strip().split('\n')
            unique_errors = list(set(errors))[:3]

            report["events"].append({
                "type": "Stream Corruption",
                "start_time": 0,
                "error": "Decode Errors Detected",
                "details": f"Found {len(errors)} packet errors. Samples: {'; '.join(unique_errors)}"
            })
        else:
            report["status"] = "PASSED"
            report["events"].append({
                "type": "Info",
                "start_time": 0,
                "details": "Container and Stream headers are healthy."
            })

    except Exception as e:
        print(f"[ERROR] QC Failed: {e}")
        report["status"] = "CRITICAL_FAIL"
        report["events"].append({"error": str(e)})

    save_report(report, output_path)

def save_report(data, output_path):
    # FIX: Ensure we create the DIRECTORY, not treat the file as a directory
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print(f"[OK] Saved: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    check_structure(args.input, args.output, args.config)