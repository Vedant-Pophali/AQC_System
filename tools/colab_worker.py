# %% [markdown]
# # AQC Worker Setup
# Run this cell to install dependencies and setup the environment.
# %%
import os
import sys
import subprocess
from pathlib import Path

# 1. Install Dependencies
print("Installing dependencies...")
subprocess.run([sys.executable, "-m", "pip", "install", "pyspark", "opencv-contrib-python-headless", "numpy", "scipy", "librosa", "pandas", "plotly", "tqdm", "scikit-image", "Pillow", "requests"], check=True)

# 2. Clone Repository
# NOTE: If the repository is private, you may need to use a Personal Access Token (PAT)
# e.g., git clone https://<token>@github.com/Vedant-Pophali/AQC_System.git
REPO_URL = "https://github.com/Vedant-Pophali/AQC_System.git"
REPO_DIR = Path("AQC_System")

if not REPO_DIR.exists():
    print(f"Cloning {REPO_URL}...")
    subprocess.run(["git", "clone", REPO_URL], check=True)
else:
    print("Repository already exists. Updating...")
    # Force reset to match remote to avoid conflicts or corrupted states
    subprocess.run(["git", "-C", str(REPO_DIR), "fetch", "origin"], check=True)
    subprocess.run(["git", "-C", str(REPO_DIR), "reset", "--hard", "origin/main"], check=True)

# 3. Add Repository to Python Path
if str(REPO_DIR.resolve()) not in sys.path:
    sys.path.append(str(REPO_DIR.resolve()))

print("Setup Complete.")

# %% [markdown]
# # Configuration
# Set the backend URL and working directory.
# %%
import requests
import time
import json

# CONFIGURATION
# In Colab, the user will set this env var or we defaults to the production URL
BACKEND_URL = os.environ.get("AQC_BACKEND_URL", "https://aqc-system.onrender.com/")
WORK_DIR = Path("aqc_worker_workspace")
WORK_DIR.mkdir(exist_ok=True)

print(f"Worker configured for: {BACKEND_URL}")
print(f"Workspace: {WORK_DIR.resolve()}")

# %% [markdown]
# # Helper Functions
# Define necessary functions for job processing.
# %%
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

# %% [markdown]
# # Analysis Logic
# Core logic to run the analysis script.
# %%
def run_analysis(video_path, job_id, profile="strict"):
    # Output dir for this job
    out_dir = WORK_DIR / f"job_{job_id}_out"
    out_dir.mkdir(exist_ok=True)
    
    # Resolve paths relative to this script or current dir
    script_dir = Path(__file__).resolve().parent if "__file__" in locals() else Path.cwd()
    repo_root = script_dir.parent # If running from tools/
    
    # Colab specific: If we cloned AQC_System into cwd
    colab_repo_root = Path("AQC_System").resolve()

    # Path to main_spark.py
    # Try multiple common locations
    possible_paths = [
        colab_repo_root / "backend" / "python_core" / "main_spark.py", # Cloned in Colab
        repo_root / "backend" / "python_core" / "main_spark.py",       # Local tools/ execution
        repo_root / "python_core" / "main_spark.py",
        Path("/content/backend/python_core/main_spark.py"),            # Legacy/Fallback
    ]

    spark_script_path = None
    for p in possible_paths:
        if p.exists() and p.is_file():
            spark_script_path = p.resolve()
            break
            
    # If still not found, search recursively
    if not spark_script_path:
        search_roots = [colab_repo_root, repo_root, Path(".")]
        print(f"main_spark.py not found in standard locations. Searching in {search_roots}...")
        for root in search_roots:
            if root.exists():
                for p in root.rglob("main_spark.py"):
                    if p.is_file():
                        spark_script_path = p.resolve()
                        break
            if spark_script_path: break

    if not spark_script_path:
        # Debug: List what IS there
        print(f"CRITICAL: main_spark.py not found.")
        print(f"Current Directory: {Path.cwd()}")
        if colab_repo_root.exists():
             print(f"Contents of {colab_repo_root}:")
             try:
                 for item in colab_repo_root.iterdir(): print(f" - {item}")
             except: pass
        raise FileNotFoundError(f"Spark script not found. Please ensure AQC_System is cloned.")
        
    print(f"Resolved main_spark.py at: {spark_script_path}")

    # Verify we can actually read it
    try:
        with open(spark_script_path, 'r') as f:
            pass
    except Exception as e:
        raise Exception(f"Found script at {spark_script_path} but CANNOT READ IT: {e}")

    cmd = [
        sys.executable, str(spark_script_path),
        "--input", str(video_path),
        "--outdir", str(out_dir),
        "--mode", profile,
        "--spark_master", "local[*]" # In Colab, run local Spark
    ]
    
    print(f"Running analysis: {' '.join(cmd)}")
    
    # Ensure PYTHONPATH includes backend/python_core so imports work in subprocesses
    env = os.environ.copy()
    python_core_path = spark_script_path.parent
    
    # Add project root to PYTHONPATH as well (for src.utils imports)
    project_root = python_core_path.parent.parent # backend/python_core -> backend -> AQC_System
    
    # We construct PYTHONPATH to include: python_core dir, and the project root (AQC_System)
    # This allows imports like `from src.utils...` to work if `src` is in project root or backend
    
    # Check where `src` is
    src_path = None
    if (python_core_path / "src").exists():
        src_path = python_core_path
    elif (project_root / "backend" / "python_core" / "src").exists(): # redundancy check
        src_path = project_root / "backend" / "python_core"
    
    # Actually, main_spark.py uses `from src.utils...`. 
    # Usually `src` is in `backend/python_core/src` based on previous file view.
    # So PYTHONPATH should be `backend/python_core`.
    
    python_path_entries = [str(python_core_path)]
    if colab_repo_root.exists():
         python_path_entries.append(str(colab_repo_root))
    
    env["PYTHONPATH"] = os.pathsep.join(python_path_entries) + os.pathsep + env.get("PYTHONPATH", "")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if result.returncode != 0:
            print("STDERR:", result.stderr)
            raise Exception(f"Analysis process failed: {result.stderr}")
            
        # Find Master_Report.json
        for f in out_dir.rglob("Master_Report.json"):
            return f
            
        raise Exception("Master_Report.json not found in output")
        
    except Exception as e:
        raise e

# %% [markdown]
# # Remediation Logic
# Logic to run the remediation script.
# %%
def run_remediation(video_path, job_id, fix_type):
    # Output dir for this job
    out_dir = WORK_DIR / f"job_{job_id}_fix"
    out_dir.mkdir(exist_ok=True)
    
    # Resolve paths relative to this script or current dir
    script_dir = Path(__file__).resolve().parent if "__file__" in locals() else Path.cwd()
    repo_root = script_dir.parent # If running from tools/
    colab_repo_root = Path("AQC_System").resolve()

    # Path to fix_media.py
    # BE/python_core/src/remediation/fix_media.py
    possible_paths = [
        colab_repo_root / "backend" / "python_core" / "src" / "remediation" / "fix_media.py",
        repo_root / "backend" / "python_core" / "src" / "remediation" / "fix_media.py",
        repo_root / "python_core" / "src" / "remediation" / "fix_media.py",
    ]

    fix_script_path = None
    for p in possible_paths:
        if p.exists() and p.is_file():
            fix_script_path = p.resolve()
            break
            
    if not fix_script_path:
        raise FileNotFoundError(f"fix_media.py not found in standard locations.")
        
    print(f"Resolved fix_media.py at: {fix_script_path}")

    # Output file
    output_filename = f"fixed_{job_id}.mp4"
    output_path = out_dir / output_filename

    cmd = [
        sys.executable, str(fix_script_path),
        "--input", str(video_path),
        "--output", str(output_path),
        "--fix", fix_type
    ]
    
    print(f"Running remediation: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("STDERR:", result.stderr)
            raise Exception(f"Remediation process failed: {result.stderr}")
            
        if not output_path.exists():
             raise Exception("Fixed video file not created.")
             
        return output_path
        
    except Exception as e:
        raise e

def upload_remediation_result(job_id, file_path):
    url = f"{BACKEND_URL}/api/v1/queue/{job_id}/complete-remediation"
    print(f"Uploading fixed video to {url}...")
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f, 'video/mp4')}
            resp = requests.post(url, files=files)
            if resp.status_code != 200:
                raise Exception(f"Upload failed: {resp.status_code} - {resp.text}")
            print(f"Remediation upload complete for Job {job_id}")
    except Exception as e:
        print(f"Failed to upload fixed video: {e}")
        raise e

# %% [markdown]
# # Main Loop
# Start the worker loop.
# %%
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
                        
                        # Check if it is a Remediation Job
                        if profile.startswith("REMEDIATION:"):
                            fix_type = profile.split(":", 1)[1]
                            print(f"Job {job_id} is a REMEDIATION job. Type: {fix_type}")
                            fixed_path = run_remediation(local_video_path, job_id, fix_type)
                            upload_remediation_result(job_id, fixed_path)
                        else:
                            # Standard Analysis Job
                            report_path = run_analysis(local_video_path, job_id, profile)
                            report_success(job_id, report_path)
                        
                    except Exception as e:
                        print(f"Job {job_id} Failed: {e}")
                        # If remediation failed, we might want to report failure differently, 
                        # currently report_failure generally updates status to FAILED.
                        # For remediation, our backend service handles updates via upload,
                        # but we can try generic failure report if we want to update the fixStatus.
                        # However, report_failure updates 'status', not 'fixStatus'.
                        # Ideally failure reporting should also be split, but for now we log it.
                        # We can send a special error payload if needed.
                        print("Reporting generic failure...")
                        report_failure(job_id, f"Worker Error: {str(e)}")
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
