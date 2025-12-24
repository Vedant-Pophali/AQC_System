import argparse
import sys
import os
import subprocess
import json
import warnings
import shutil

# ---------------- BASIC SETUP ----------------
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

warnings.filterwarnings("ignore")
PYTHON_EXEC = sys.executable

# ---------------- SAFETY HELPERS ----------------
def check_dependencies():
    # 1. Check OpenCV
    try:
        import cv2
    except ImportError:
        print("[CRITICAL] OpenCV (cv2) not available. Run setup.bat.")
        sys.exit(1)

    # 2. Check FFmpeg
    if not shutil.which("ffmpeg"):
        print("[CRITICAL] FFmpeg is missing! Install FFmpeg and add it to System PATH.")
        sys.exit(1)

def create_error_report(output_path, script_name, reason):
    fallback = {
        "module": script_name.replace(".py", ""),
        "video_file": "unknown",
        "status": "ERROR",
        "events": [],
        "error_details": reason
    }
    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(fallback, f, indent=4, ensure_ascii=False)

def run_module(script_name, video_path, output_file, timeout=1200, extra_args=None):
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    print(f"   >>> Running {script_name}...")

    if not os.path.exists(script_path):
        print(f"   [ERROR] Script not found: {script_path}")
        create_error_report(output_file, script_name, "Script missing")
        return

    cmd = [PYTHON_EXEC, script_path, "--input", video_path, "--output", output_file]
    if extra_args:
        cmd.extend(extra_args)

    try:
        result = subprocess.run(
            cmd, timeout=timeout, check=False,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace'
        )
        if result.returncode != 0:
            print(f"   [WARN] {script_name} exited with code {result.returncode}")
            if result.stderr:
                print(f"   [STDERR] {result.stderr.strip()[:200]}...")
    except subprocess.TimeoutExpired:
        print(f"   [ERROR] {script_name} timed out!")
        create_error_report(output_file, script_name, "TIMEOUT")
        return

    if not os.path.exists(output_file):
        print(f"   [ERROR] {script_name} produced no report.")
        create_error_report(output_file, script_name, "NO_OUTPUT")

# ---------------- MAIN PIPELINE ----------------
def main():
    check_dependencies()

    parser = argparse.ArgumentParser(description="Automated QC Pipeline")
    parser.add_argument("--input", required=True, help="Input video file")
    parser.add_argument("--output", default="reports", help="Reports directory")
    args = parser.parse_args()

    video_path = os.path.abspath(args.input)
    if os.path.isabs(args.output):
        reports_dir = args.output
    else:
        reports_dir = os.path.abspath(args.output)

    if not os.path.exists(video_path):
        print(f"[CRITICAL] Input video not found: {video_path}")
        sys.exit(1)

    os.makedirs(reports_dir, exist_ok=True)
    print("--- STARTING QC PIPELINE ---")

    # Load config
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "qc_config.json")
    timeout = 1200
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                timeout = json.load(f).get("general", {}).get("worker_timeout_seconds", 1200)
        except: pass

    # 1. Structural QC (Fail Fast)
    run_module("validate_structure.py", video_path, os.path.join(reports_dir, "report_structure.json"), timeout=300, extra_args=["--config", config_path])

    # 2. Visual QC
    run_module("detect_black.py", video_path, os.path.join(reports_dir, "report_visual.json"), timeout)

    # 2.5 Interlace Detection (Phase 8)
    run_module("validate_interlace.py", video_path, os.path.join(reports_dir, "report_interlace.json"), timeout)

    # 3. Audio QC (Loudness)
    run_module("validate_loudness.py", video_path, os.path.join(reports_dir, "report_audio.json"), timeout)

    # 3.5 Audio Signal Integrity (Phase 7)
    run_module("validate_audio_signal.py", video_path, os.path.join(reports_dir, "report_audio_signal.json"), timeout)

    # 4. QCTools Analysis (Phase 9 - Research Pillar 3)
    run_module("validate_qctools.py", video_path, os.path.join(reports_dir, "report_qctools.json"), timeout)

    # 5. OCR Extraction
    run_module("video_ocr.py", video_path, os.path.join(reports_dir, "report_ocr.json"), timeout)

    # 6. Broadcast Signal Safety
    run_module("validate_signal.py", video_path, os.path.join(reports_dir, "report_signal.json"), timeout)

    # 7. Advanced Visual Artifacts (Blockiness/Blur)
    run_module("validate_artifacts.py", video_path, os.path.join(reports_dir, "report_artifacts.json"), timeout)
    # [NEW] Phase 6: Automated Self-Healing
    # Checks Audio Report. If REJECTED, it creates a fixed version.
    correction_script = os.path.join(os.path.dirname(__file__), "correct_loudness.py")
    if os.path.exists(correction_script):
        print(f"   >>> Checking for Automated Corrections...")
        subprocess.run([
            PYTHON_EXEC, correction_script,
            "--input", video_path,
            "--report", os.path.join(reports_dir, "report_audio.json"),
            "--config", config_path
        ], check=False)

    # ---- AGGREGATE ----
    print("   >>> Generating Master Report...")
    subprocess.run([
        PYTHON_EXEC, os.path.join(os.path.dirname(__file__), "generate_master_report.py"),
        "--inputs",
        os.path.join(reports_dir, "report_structure.json"),
        os.path.join(reports_dir, "report_visual.json"),
        os.path.join(reports_dir, "report_artifacts.json"),
        os.path.join(reports_dir, "report_interlace.json"),
        os.path.join(reports_dir, "report_audio.json"),
        os.path.join(reports_dir, "report_audio_signal.json"),
        os.path.join(reports_dir, "report_qctools.json"), # Added Correctly Here
        os.path.join(reports_dir, "report_ocr.json"),
        os.path.join(reports_dir, "report_signal.json"),
        "--output", os.path.join(reports_dir, "Master_Report.json")
    ], check=False)

    # ---- VISUALIZE ----
    print("   >>> Building Dashboard...")
    subprocess.run([
        PYTHON_EXEC, os.path.join(os.path.dirname(__file__), "visualize_report.py"),
        "--input", os.path.join(reports_dir, "Master_Report.json"),
        "--output", os.path.join(reports_dir, "dashboard.html")
    ], check=False)

    print("\n--- JOB COMPLETE ---")

if __name__ == "__main__":
    main()