import requests
import time
import os
import sys
import subprocess
import json
from pathlib import Path

# CONFIGURATION
# In Colab, the user will set this env var or we defaults to localhost for testing
BACKEND_URL = os.environ.get("AQC_BACKEND_URL", "http://localhost:8080")
WORK_DIR = Path("aqc_worker_workspace")
WORK_DIR.mkdir(exist_ok=True)

def get_pending_jobs():
    try:
        resp = requests.get(f"{BACKEND_URL}/api/v1/queue/pending")
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"Error polling backend: {e}")
    return []

def claim_job(job_id):
    try:
        resp = requests.post(f"{BACKEND_URL}/api/v1/queue/{job_id}/claim")
        return resp.status_code == 200
    except Exception as e:
        print(f"Error claiming job {job_id}: {e}")
        return False

def download_video(job_id, local_path):
    url = f"{BACKEND_URL}/api/v1/jobs/{job_id}/video"
    print(f"Downloading video from {url}...")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print(f"Downloaded to {local_path}")

def report_success(job_id, report_path):
    # Read the report JSON
    try:
        with open(report_path, 'r') as f:
            report_content = f.read()
        
        payload = {"reportJson": report_content}

        # Try to read HTML Dashboard
        dashboard_path = Path(report_path).parent / "dashboard.html"
        if dashboard_path.exists():
             with open(dashboard_path, 'r', encoding='utf-8') as f:
                payload["reportHtml"] = f.read()
             print(f"Found and attaching dashboard.html")
        
        requests.post(f"{BACKEND_URL}/api/v1/queue/{job_id}/complete", json=payload)
        print(f"Report uploaded for Job {job_id}")
    except Exception as e:
        print(f"Failed to upload report: {e}")

def report_failure(job_id, error_msg):
    try:
        payload = {"error": error_msg}
        requests.post(f"{BACKEND_URL}/api/v1/queue/{job_id}/complete", json=payload)
        print(f"Failure reported for Job {job_id}")
    except Exception as e:
        print(f"Failed to report failure: {e}")

def run_analysis(video_path, job_id, profile="strict"):
    # Output dir for this job
    out_dir = WORK_DIR / f"job_{job_id}_out"
    out_dir.mkdir(exist_ok=True)
    
    # Construct command
    # We assume we are in the root of the repo (where main_spark.py is)
    cmd = [
        sys.executable, "backend/python_core/main_spark.py",
        "--input", str(video_path),
        "--outdir", str(out_dir),
        "--mode", profile,
        "--spark_master", "local[*]" # In Colab, run local Spark
    ]
    
    print(f"Running analysis: {' '.join(cmd)}")
    
    # Ensure PYTHONPATH includes backend/python_core so imports work in subprocesses
    env = os.environ.copy()
    python_core_path = os.path.abspath("backend/python_core")
    env["PYTHONPATH"] = python_core_path + os.pathsep + env.get("PYTHONPATH", "")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if result.returncode != 0:
            print("STDERR:", result.stderr)
            raise Exception(f"Analysis process failed: {result.stderr}")
            
        # Find Master_Report.json
        # It's usually in out_dir / {video_name}_spark_qc / Master_Report.json
        # But let's search strictly
        for f in out_dir.rglob("Master_Report.json"):
            return f
            
        raise Exception("Master_Report.json not found in output")
        
    except Exception as e:
        raise e

def main_loop():
    print(f"Worker started. Polling {BACKEND_URL}...")
    while True:
        jobs = get_pending_jobs()
        if jobs:
            print(f"Found {len(jobs)} pending jobs.")
            for job in jobs:
                job_id = job['id']
                print(f"Attempting to claim Job {job_id}...")
                
                if claim_job(job_id):
                    print(f"Claimed Job {job_id}. Processing...")
                    
                    video_filename = job.get('originalFilename', 'input.mp4')
                    local_video_path = WORK_DIR / f"job_{job_id}_{video_filename}"
                    
                    try:
                        download_video(job_id, local_video_path)
                        profile = job.get('profile', 'strict')
                        
                        report_path = run_analysis(local_video_path, job_id, profile)
                        report_success(job_id, report_path)
                        
                    except Exception as e:
                        print(f"Job {job_id} Failed: {e}")
                        report_failure(job_id, str(e))
                    finally:
                        # Cleanup
                        if local_video_path.exists():
                            os.remove(local_video_path)
                else:
                    print(f"Failed to claim Job {job_id} (maybe taken).")
        else:
            print(".", end="", flush=True)
            time.sleep(5)

if __name__ == "__main__":
    main_loop()
