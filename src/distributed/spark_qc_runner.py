import argparse
import subprocess
import sys
import os
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

# -------------------------------------------------
# WORKER LOGIC
# -------------------------------------------------
def process_video_task(args):
    """
    Executes the main AQC pipeline for a single file in a separate process.
    """
    input_path, base_out_dir, mode, fix, main_script_path = args
    
    file_name = Path(input_path).name
    file_stem = Path(input_path).stem
    
    # Create isolated output folder for this video
    file_out_dir = os.path.join(base_out_dir, file_stem)
    os.makedirs(file_out_dir, exist_ok=True)
    
    # Construct command
    cmd = [
        sys.executable, main_script_path,
        "--input", str(input_path),
        "--outdir", str(file_out_dir),
        "--mode", mode
    ]
    if fix:
        cmd.append("--fix")

    start_time = time.time()
    try:
        # Run subprocess
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        
        duration = time.time() - start_time
        status = "SUCCESS" if result.returncode == 0 else "FAILED"
        
        return {
            "file": file_name,
            "status": status,
            "duration": round(duration, 2),
            "output_dir": file_out_dir,
            "error_log": result.stderr if status == "FAILED" else ""
        }
        
    except Exception as e:
        return {
            "file": file_name,
            "status": "CRASHED",
            "duration": round(time.time() - start_time, 2),
            "output_dir": file_out_dir,
            "error_log": str(e)
        }

# -------------------------------------------------
# RUNNER LOGIC
# -------------------------------------------------
def run_parallel_qc(input_dir, output_dir, mode, fix):
    # resolve absolute paths to avoid issues in subprocesses
    abs_input_dir = Path(input_dir).resolve()
    abs_output_dir = Path(output_dir).resolve()
    
    # Locate src/main.py relative to this script
    # This script is in src/distributed/, so main is in ../main.py
    current_dir = Path(__file__).resolve().parent
    main_script = (current_dir.parent / "main.py").resolve()
    
    if not main_script.exists():
        print(f"[ERROR] Could not find orchestrator at {main_script}")
        return

    print(f"\n[PARALLEL] Initializing Multi-Core QC Runner...")
    print(f"   Input:  {abs_input_dir}")
    print(f"   Output: {abs_output_dir}")
    print(f"   Worker: {main_script}")
    
    # 1. Discovery
    extensions = {'.mp4', '.mov', '.mkv', '.avi', '.mxf'}
    video_files = [
        p for p in abs_input_dir.rglob("*") 
        if p.suffix.lower() in extensions
    ]
    
    if not video_files:
        print("[PARALLEL] No video files found.")
        return

    print(f"[PARALLEL] Found {len(video_files)} videos. Spinning up workers...")

    # 2. Prepare Tasks
    # Tuple: (path, out_dir, mode, fix, script_path)
    tasks = [
        (str(v), str(abs_output_dir), mode, fix, str(main_script)) 
        for v in video_files
    ]
    
    # 3. Execute in Parallel
    # uses all available CPU cores by default
    results = []
    
    # ProcessPoolExecutor replaces Spark for local parallelization
    with ProcessPoolExecutor() as executor:
        # Submit all tasks
        futures = {executor.submit(process_video_task, t): t for t in tasks}
        
        print("\n" + "="*60)
        print(f"{'STATUS':<10} | {'FILENAME':<40} | {'TIME':<10}")
        print("="*60)
        
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            
            icon = "✅" if res['status'] == "SUCCESS" else "❌"
            print(f"{icon} {res['status']:<7} | {res['file']:<40} | {res['duration']}s")

    # 4. Summary
    success_count = sum(1 for r in results if r['status'] == "SUCCESS")
    fail_count = len(results) - success_count
    
    print("-" * 60)
    print(f"TOTAL: {len(results)} | PASSED: {success_count} | FAILED: {fail_count}")
    print(f"Batch Reports: {abs_output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parallel AQC Runner")
    parser.add_argument("--input_dir", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--mode", default="strict")
    parser.add_argument("--fix", action="store_true")
    
    args = parser.parse_args()
    
    run_parallel_qc(args.input_dir, args.outdir, args.mode, args.fix)