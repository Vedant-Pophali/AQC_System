import subprocess
import os
import json
import shutil
import pytest
import sys
from pathlib import Path

# Config
TEST_VIDEO = "integration_test_video.mp4"
TEST_OUTDIR = "integration_test_output"

@pytest.fixture(scope="module", autouse=True)
def setup_teardown():
    """
    1. Create a synthetic test video using FFmpeg.
    2. Run the test.
    3. Cleanup files after.
    """
    # Create 5-second test video (synthetic patterns)
    # Using 'testsrc' for video and 'sine' for audio
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", 
        "-i", "testsrc=duration=5:size=1280x720:rate=30", 
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=5",
        "-c:v", "libx264", "-c:a", "aac", "-shortest",
        TEST_VIDEO
    ]
    
    # Generate video
    print(f"\n[Setup] Generating synthetic video: {TEST_VIDEO}")
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except subprocess.CalledProcessError:
        pytest.fail("FFmpeg failed to generate test video. Is FFmpeg installed?")
    
    yield # Run tests now
    
    # Cleanup
    print("\n[Teardown] Cleaning up test artifacts...")
    if os.path.exists(TEST_VIDEO):
        os.remove(TEST_VIDEO)
    if os.path.exists(TEST_OUTDIR):
        shutil.rmtree(TEST_OUTDIR)

def test_pipeline_execution():
    """
    Runs main.py against the generated video and verifies the report.
    """
    cmd = [
        sys.executable, "main.py",
        "--input", TEST_VIDEO,
        "--outdir", TEST_OUTDIR,
        "--mode", "strict"
    ]
    
    print("Running AQC Pipeline (this may take 10-20 seconds)...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # 1. Check Execution Status
    if result.returncode != 0:
        print(f"\nSTDOUT: {result.stdout}")
        print(f"\nSTDERR: {result.stderr}")
    
    assert result.returncode == 0, f"Pipeline crashed with exit code {result.returncode}"
    
    # 2. Check File Generation
    report_folder = Path(TEST_OUTDIR) / f"{Path(TEST_VIDEO).stem}_qc_report"
    master_json = report_folder / "Master_Report.json"
    dashboard_html = report_folder / "dashboard.html"
    
    assert report_folder.exists(), "Report folder was not created"
    assert master_json.exists(), "Master_Report.json was not generated"
    assert dashboard_html.exists(), "Dashboard.html was not generated"
    
    # 3. Check JSON Content
    with open(master_json, "r") as f:
        data = json.load(f)
        
    # Verify Governance
    assert "governance" in data, "Governance block missing"
    assert data["governance"]["active_profile"] == "strict"
    
    # Verify Artifact Module ran
    artifacts = data["modules"].get("validate_artifacts", {})
    assert artifacts["status"] in ["PASSED", "WARNING", "REJECTED"], "Artifact module status invalid"
    
    # Verify ML Model was used (if configured enabled)
    # Note: Metrics might be empty if the synthetic video is perfect, but the module key should exist
    assert "validate_artifacts" in data["modules"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])