import argparse
import subprocess
import sys
import csv
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Extensions to scan for
VIDEO_EXTS = {'.mp4', '.mov', '.mxf', '.mkv', '.avi', '.ts'}

def process_single_file(args):
    """
    Worker function to run main.py for one video.
    """
    video_path, output_dir, mode, script_path = args
    
    # Define expected report location
    report_folder = output_dir / f"{video_path.stem}_qc_report"
    master_json = report_folder / "Master_Report.json"
    
    # Construct command
    cmd = [
        sys.executable, str(script_path),
        "--input", str(video_path),
        "--outdir", str(output_dir),
        "--mode", mode
    ]

    start_time = time.time()
    try:
        # Run the existing main.py logic
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        duration = round(time.time() - start_time, 2)
        
        # Parse result if exists
        status = "CRASHED"
        defects = "N/A"
        
        if master_json.exists():
            try:
                with open(master_json, 'r') as f:
                    data = json.load(f)
                status = data.get("overall_status", "UNKNOWN")
                
                # Extract top defects for summary
                events = [e.get("type") for mod in data.get("modules", {}).values() for e in mod.get("events", [])]
                defects = ", ".join(list(set(events))[:3]) # First 3 unique defects
            except:
                status = "CORRUPT_JSON"
        
        return {
            "Filename": video_path.name,
            "Status": status,
            "Defects": defects,
            "Duration (s)": duration,
            "Report Path": str(report_folder.relative_to(output_dir))
        }

    except subprocess.CalledProcessError:
        return {
            "Filename": video_path.name,
            "Status": "SYSTEM_FAIL",
            "Defects": "Pipeline Error",
            "Duration (s)": 0,
            "Report Path": "N/A"
        }

def main():
    parser = argparse.ArgumentParser(description="Batch AQC Runner for Large Datasets")
    parser.add_argument("--input_dir", required=True, help="Folder containing video files")
    parser.add_argument("--output_dir", required=True, help="Folder to save all reports")
    parser.add_argument("--mode", default="strict", help="QC Profile (strict, youtube, netflix_hd)")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel files to process")
    
    args = parser.parse_args()
    
    in_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    main_script = Path(__file__).parent / "main.py"
    
    # 1. Scan for Files
    videos = [p for p in in_dir.rglob("*") if p.suffix.lower() in VIDEO_EXTS]
    print(f"\n[AQC BATCH] Found {len(videos)} videos in {in_dir}")
    print(f"[AQC BATCH] Profile: {args.mode.upper()} | Parallel Workers: {args.workers}")
    print("-" * 60)
    
    results = []
    
    # 2. Parallel Processing
    task_args = [(v, out_dir, args.mode, main_script) for v in videos]
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        # Use tqdm for a nice progress bar
        futures = {executor.submit(process_single_file, arg): arg[0].name for arg in task_args}
        
        for future in tqdm(as_completed(futures), total=len(videos), unit="vid"):
            res = future.result()
            results.append(res)
            
    # 3. Generate Executive Summary CSV
    csv_path = out_dir / "Executive_Summary.csv"
    keys = ["Filename", "Status", "Defects", "Duration (s)", "Report Path"]
    
    # Sort by Status (failures first)
    results.sort(key=lambda x: (x["Status"] == "PASSED", x["Filename"]))
    
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(results)
        
    print("-" * 60)
    print(f"\n[DONE] Processed {len(videos)} files.")
    print(f"Summary Report: {csv_path}")

if __name__ == "__main__":
    main()