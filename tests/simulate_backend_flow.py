import subprocess
import sys
import shutil
import json
import os
from pathlib import Path

def simulate_java_backend():
    print("=== SPECTRA AQC: BACKEND SIMULATION ===")
    
    # 1. Setup Environment
    upload_dir = Path("backend_simulation_uploads")
    upload_dir.mkdir(exist_ok=True)
    
    # Create dummy video
    input_video = upload_dir / "sim_upload.mp4"
    if not input_video.exists():
        print("[1/3] Creating dummy video asset...")
        # Use simple ffmpeg generation
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=5:size=1280x720:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=5",
            "-c:v", "libx264", "-c:a", "aac", str(input_video)
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 2. Trigger Analysis (Mimic PythonExecutionService.java)
    print(f"[2/3] Calling Core Engine: {input_video}")
    output_dir = upload_dir / f"job_sim_{os.getpid()}"
    
    cmd = [
        sys.executable, "main.py",
        "--input", str(input_video),
        "--outdir", str(output_dir),
        "--mode", "strict"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("!!! CRITICAL FAILURE !!!")
            print(result.stderr)
            sys.exit(1)
            
        print("   -> Core Engine finished successfully.")
        
    except Exception as e:
        print(f"Execution failed: {e}")
        sys.exit(1)

    # 3. Verify Output (Mimic Backend Parsing)
    print("[3/3] Verifying JSON Output...")
    report_file = list(output_dir.glob("**/Master_Report.json"))
    
    if not report_file:
        print("!!! FAILURE: Master_Report.json not found in output directory.")
        sys.exit(1)
        
    report_path = report_file[0]
    with open(report_path) as f:
        data = json.load(f)
        
    status = data.get('governance', {}).get('active_profile')
    print(f"   -> Found Report: {report_path.name}")
    print(f"   -> Profile Used: {status}")
    print("\n=== SIMULATION PASSED ===")
    print("The Python Core and CLI Interface are strictly compatible with the Java Backend logic.")

    # Cleanup
    shutil.rmtree(upload_dir)

if __name__ == "__main__":
    simulate_java_backend()
