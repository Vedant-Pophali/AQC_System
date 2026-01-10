import argparse
import subprocess
import sys
import os
import shutil
import json
import csv
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

def split_video(input_path, segment_dir, segment_time=300):
    """
    Splits video into chunks using stream copy (fast, no quality loss).
    Returns a list of (segment_filename, start_time_seconds).
    """
    input_path = Path(input_path).resolve()
    segment_dir = Path(segment_dir).resolve()
    segment_dir.mkdir(parents=True, exist_ok=True)
    
    # Output pattern
    seg_prefix = input_path.stem
    out_pattern = segment_dir / f"{seg_prefix}_%03d.mp4"
    list_file = segment_dir / "segments.csv"

    print(f"[SPLIT] Slicing {input_path.name} into {segment_time}s chunks...")
    
    # FFmpeg command to segment
    # -c copy: Instant split (snaps to nearest keyframe)
    # -segment_list_type csv: Generates a list with exact start/end times
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-c", "copy",
        "-map", "0",
        "-f", "segment",
        "-segment_time", str(segment_time),
        "-segment_list", str(list_file),
        "-segment_list_type", "csv",
        str(out_pattern)
    ]
    
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    
    # Parse the CSV to get exact start times (crucial for accurate reporting)
    segments = []
    if list_file.exists():
        with open(list_file, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                # CSV Format: filename, start_time, end_time
                if row:
                    seg_name = row[0]
                    start_time = float(row[1])
                    segments.append((segment_dir / seg_name, start_time))
    
    print(f"[SPLIT] Created {len(segments)} segments.")
    return segments

def process_segment(args):
    """
    Worker function to run QC on a single segment.
    """
    seg_path, seg_start_time, output_base, mode, main_script = args
    
    # Dedicated output folder for this segment
    seg_out_dir = output_base / seg_path.stem
    seg_out_dir.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        sys.executable, str(main_script),
        "--input", str(seg_path),
        "--outdir", str(seg_out_dir),
        "--mode", mode
    ]
    
    # Run QC (Silence output to prevent console chaos)
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    report_path = seg_out_dir / "Master_Report.json"
    return (seg_path.name, seg_start_time, report_path)

def merge_reports(original_path, segment_results, final_report_path):
    """
    Merges multiple JSON reports into one, shifting timestamps.
    """
    print("[MERGE] Aggregating results...")
    
    master_agg = {
        "metadata": {
            "source_file": str(original_path),
            "generated_on": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tool": "AQC_Distributed_Segmenter"
        },
        "overall_status": "PASSED",
        "modules": {},
        "events": [] # Flattened events list
    }
    
    worst_status = "PASSED"
    status_rank = {"PASSED": 1, "WARNING": 2, "REJECTED": 3, "ERROR": 4}
    
    for seg_name, offset, json_path in segment_results:
        if not json_path.exists():
            continue
            
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        # Update Status Logic
        seg_status = data.get("overall_status", "PASSED")
        if status_rank.get(seg_status, 0) > status_rank.get(worst_status, 0):
            worst_status = seg_status
            
        # Merge Module Metrics (Averaging is hard, we keep last or max logic? 
        # For simplicity, we skip merging raw metrics and focus on EVENTS)
        
        # Merge Events with Time Offset
        for module_name, module_data in data.get("modules", {}).items():
            for event in module_data.get("events", []):
                # Shift timestamps
                if "start_time" in event:
                    event["start_time"] = round(event["start_time"] + offset, 3)
                if "end_time" in event:
                    event["end_time"] = round(event["end_time"] + offset, 3)
                
                # Tag origin
                event["details"] = f"[{seg_name}] " + event.get("details", "")
                
                # Add to master list
                master_agg["events"].append(event)
                
                # Propagate failure to top level
                if "status" not in master_agg: 
                    master_agg["status"] = "PASSED"
                
    master_agg["overall_status"] = worst_status
    
    # Save Final Report
    with open(final_report_path, 'w') as f:
        json.dump(master_agg, f, indent=4)
        
    return worst_status

def run_segmented_qc(input_file, outdir, mode="strict"):
    input_path = Path(input_file).resolve()
    outdir = Path(outdir).resolve()
    temp_dir = outdir / "temp_segments"
    
    script_dir = Path(__file__).parent
    main_script = (script_dir.parent / "main.py").resolve()
    
    # 1. SPLIT
    try:
        segments = split_video(input_path, temp_dir, segment_time=300)
    except Exception as e:
        print(f"[ERROR] Split failed: {e}")
        return

    # 2. DISTRIBUTE
    tasks = []
    print(f"[PARALLEL] Spinning up workers for {len(segments)} segments...")
    
    for seg_path, start_time in segments:
        tasks.append((seg_path, start_time, temp_dir, mode, main_script))
        
    results = [] # Store (seg_name, start_time, report_path)
    
    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(process_segment, t): t for t in tasks}
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            print(f" + Finished segment: {res[0]}")

    # 3. MERGE
    final_report = outdir / "Segmented_Master_Report.json"
    final_status = merge_reports(input_path, results, final_report)
    
    print(f"\n[DONE] Final Status: {final_status}")
    print(f"Report: {final_report}")
    
    # Cleanup Temp
    # shutil.rmtree(temp_dir) # Uncomment to save space

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--mode", default="strict")
    args = parser.parse_args()
    
    run_segmented_qc(args.input, args.outdir, args.mode)