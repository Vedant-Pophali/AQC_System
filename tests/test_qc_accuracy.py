import pytest
import subprocess
import sys
import json
import os
from pathlib import Path

# Config
MAIN_SCRIPT = "backend/python_core/main.py"
TEST_MEDIA_DIR = "test_media"
OUT_DIR = "headers_test_output"

# Define expected outcomes based on filename keywords
# (Filename Keyword, Expected Status)
TEST_CASES = [
    ("clean", "PASSED"),
    ("defect", "REJECTED"), # OR WARNING, depending on severity
    # ("defect", "WARNING") # Accept warning too if REJECT ED is too strict checks
]

def get_test_files():
    """Returns list of .mp4 files from test_media directory"""
    media_dir = Path(TEST_MEDIA_DIR)
    if not media_dir.exists():
        return []
    return [f for f in media_dir.glob("*.mp4") if "dummy" not in f.name]

@pytest.mark.parametrize("video_file", get_test_files())
def test_qc_accuracy(video_file):
    """
    Runs QC on a video and asserts the outcome matches the filename hint.
    ref_clean.mp4 -> Should PASS
    test_defect_*.mp4 -> Should FAIL (REJECTED/WARNING)
    """
    print(f"\n[Testing] {video_file.name}")
    
    # Determine expected result
    expected_status = "PASSED"
    if "defect" in video_file.name:
        expected_status = "REJECTED" 
        
    # Setup Output
    job_out = Path(OUT_DIR) / f"{video_file.stem}_out"
    
    # Construct Command
    # We must ensure PYTHONPATH includes backend/python_core so imports work
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{os.getcwd()}/backend/python_core" + os.pathsep + env.get("PYTHONPATH", "")

    cmd = [
        sys.executable, MAIN_SCRIPT,
        "--input", str(video_file),
        "--outdir", str(OUT_DIR),
        "--mode", "strict" # Use strict mode to ensure defects are caught
    ]
    
    # Run
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    
    # Check for crash
    if result.returncode != 0:
        print("STDERR:", result.stderr)
        pytest.fail(f"QC Pipeline crashed for {video_file.name}")
        
    # Find Report
    expected_report = job_out / "Master_Report.json"
    
    # Note: The output directory structure might vary slightly depending on how main.py names output folders
    # Let's search for it if exact path not found
    if not expected_report.exists():
        candidates = list(Path(OUT_DIR).rglob("Master_Report.json"))
        # Filter for the one related to this video (timestamped folder)
        # For now, just taking the most recent or checking if ANY exists might be tricky in parallel.
        # But for sequential tests, taking the latest created folder in OUTDIR is a safe bet.
        if not candidates:
             pytest.fail(f"No Master_Report.json generated for {video_file.name}")
        expected_report = max(candidates, key=os.path.getctime)

    # Parse Report
    with open(expected_report, "r") as f:
        report = json.load(f)
        
    final_disposition = report.get("final_disposition", "UNKNOWN")
    print(f"File: {video_file.name} | Expected: {expected_status} | Got: {final_disposition}")
    
    # Assertions
    if expected_status == "PASSED":
        assert final_disposition == "PASSED", f"Expected PASSED but got {final_disposition}. Report: {expected_report}"
    else:
        # For defects, we accept REJECTED or WARNING (depending on threshold)
        assert final_disposition in ["REJECTED", "WARNING"], f"Expected defect detection (REJECTED/WARNING) but got {final_disposition}. Report: {expected_report}"

if __name__ == "__main__":
    # If running directly, execute pytest
    sys.exit(pytest.main([__file__, "-v"]))
