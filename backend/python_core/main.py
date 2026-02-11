import argparse
import subprocess
import os
import json
import time
import sys
import shutil
import webbrowser
import traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any

# --- Core Modules ---
from src.config import threshold_registry
from src.postprocess import generate_master_report
from src.visualization import visualize_report
from src.utils.logger import setup_logger

# Initialize Logger
logger = setup_logger("aqc_main")

# -------------------------------------------------
# CONSTANTS & CONFIG
# -------------------------------------------------
MAX_RETRIES = 2
RETRY_DELAY_SEC = 1.0

# Define active validators
VALIDATORS = [
    # 1. Hygiene & Metadata
    ("structure", "validate_structure"),
    # 2. Structural Integrity
    ("video", "validate_frames"),
    ("video", "validate_analog"),
    # 3. Visual Defects
    ("video", "validate_black_freeze"),
    ("video", "validate_interlace"),
    ("video", "validate_artifacts"),  # ML Engine
    ("video", "validate_geometry"),
    ("archival", "validate_signal"),  # Blueprint Signal Diagnostics
    # 4. Audio Quality
    ("audio", "validate_loudness"),
    ("audio", "validate_audio_signal"),
    ("audio", "validate_phase"),
    # 5. Synchronization
    ("video", "validate_avsync"),
]

def check_dependencies() -> None:
    """Ensure ffmpeg dependencies are installed."""
    if not shutil.which("ffmpeg"):
        logger.critical("FFmpeg not found in PATH. Please install FFmpeg.")
        sys.exit(1)
    if not shutil.which("ffprobe"):
        logger.critical("FFprobe not found in PATH. Please install FFmpeg.")
        sys.exit(1)

def print_governance_header(mode: str) -> Dict[str, Any]:
    """
    Displays and returns Compliance & Governance info at startup.
    """
    gov = threshold_registry.get_governance_info(mode)
    cfg = threshold_registry.get_profile(mode)
    
    logger.info("="*60)
    logger.info(f" AQC GOVERNANCE AUDIT")
    logger.info("="*60)
    logger.info(f" Profile Used      : {gov['active_profile'].upper()}")
    logger.info(f" Description       : {gov['compliance_standard']}")
    logger.info(f" Config Version ID : {gov['config_version_hash']} (Reproducibility Hash)")
    logger.info("-" * 60)
    
    audio_cfg = cfg.get('audio', {})
    sync_cfg = cfg.get('sync', {})
    
    logger.info(f" [Audio] Target    : {audio_cfg.get('integrated_loudness_target', 'N/A')} LUFS")
    logger.info(f" [Audio] True Peak : {audio_cfg.get('true_peak_max', 'N/A')} dBTP")
    logger.info(f" [Sync]  Tolerance : +/- {sync_cfg.get('tolerance_ms', 'N/A')} ms")
    logger.info("="*60 + "\n")
    
    return gov

def run_validator_with_retry(category: str, module: str, input_video: Path, outdir: Path, mode: str, hwaccel: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes a single validator module as a subprocess with retry logic.
    """
    report_path = outdir / f"report_{module}.json"
    module_path = f"src.validators.{category}.{module}"
    
    cmd = [
        sys.executable, "-m", module_path,
        "--input", str(input_video),
        "--output", str(report_path),
        "--mode", mode
    ]
    
    if hwaccel and hwaccel != "none":
        cmd.extend(["--hwaccel", hwaccel])

    for attempt in range(1, MAX_RETRIES + 2):
        start = time.time()
        status = "UNKNOWN"
        
        try:
            result = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            duration = round(time.time() - start, 2)
            
            # 1. Check Exit Code & File Existence
            if result.returncode == 0 and report_path.exists():
                try:
                    with open(report_path, "r", encoding="utf-8") as f:
                        d = json.load(f)
                        status = d.get("effective_status", d.get("status", "UNKNOWN"))
                    
                    # Log successful execution
                    logger.info(f" + {module:<30} | {status:<10} | {duration}s")
                    return {
                        "module": module,
                        "status": status,
                        "duration_sec": duration,
                        "report": str(report_path)
                    }
                except json.JSONDecodeError:
                    logger.warning(f"{module} produced corrupt JSON on attempt {attempt}")
            else:
                # Log failure
                if attempt > MAX_RETRIES:
                    logger.error(f"{module} error:\n{result.stderr[:200]}")
                else:
                    logger.warning(f"{module} failed (Exit: {result.returncode}) on attempt {attempt}")

        except Exception as e:
            logger.error(f"Execution error on {module}: {e}")

        # Wait before retry
        if attempt <= MAX_RETRIES:
            time.sleep(RETRY_DELAY_SEC)

    # Fallback if all retries fail
    logger.error(f" ! {module:<30} | CRASHED    | 0.0s")
    
    # Create ghost report
    crash_data = {
        "module": module,
        "status": "CRASHED",
        "effective_status": "CRASHED",
        "details": {"error": "Module failed after retries", "log": "Subprocess error"}
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(crash_data, f, indent=4)

    return {
        "module": module,
        "status": "CRASHED",
        "duration_sec": 0.0,
        "report": str(report_path)
    }

def run_correction(input_video: Path, outdir: Path) -> None:
    """Attempts to auto-correct audio loudness."""
    logger.info("\n--- AUTO-CORRECTION (Loudness) ---")
    output_video = outdir / f"fixed_{input_video.name}"
    cmd = [
        sys.executable, "-m", "src.postprocess.correct_loudness",
        "--input", str(input_video), "--output", str(output_video)
    ]
    try:
        subprocess.run(cmd, check=True)
        logger.info(f" [SUCCESS] Corrected file saved to: {output_video}")
    except subprocess.CalledProcessError:
        logger.error(" [FAILED] Correction workflow failed.")

def main():
    check_dependencies()

    parser = argparse.ArgumentParser(description="AQC Core QC Pipeline")
    parser.add_argument("--input", required=True, help="Path to input video file")
    parser.add_argument("--outdir", required=True, help="Base directory to save reports")
    parser.add_argument("--mode", choices=["strict", "netflix_hd", "youtube", "ott"], default="strict", help="QC Profile")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix audio loudness errors")
    parser.add_argument("--hwaccel", default="none", help="Hardware acceleration device (e.g., cuda, vulkan, none)")

    args = parser.parse_args()

    input_video = Path(args.input).resolve()
    base_outdir = Path(args.outdir).resolve()
    
    if not input_video.exists():
        logger.critical(f"Input file not found: {input_video}")
        sys.exit(1)

    # Output folder setup
    outdir = base_outdir / f"{input_video.stem}_qc_report"
    outdir.mkdir(parents=True, exist_ok=True)

    # 1. Governance Info
    gov_info = print_governance_header(args.mode)
    
    if args.hwaccel != "none":
        logger.info(f" [ACCEL] Hardware Acceleration Requested: {args.hwaccel}")

    results = []

    # Define modules that support the --hwaccel flag
    HWACCEL_SUPPORTED = ["validate_structure", "validate_frames"]

    total_steps = len(VALIDATORS) + 1  # +1 for report generation
    
    for i, (category, module) in enumerate(VALIDATORS):
        # Calculate progress
        progress_pct = int(((i) / total_steps) * 100)
        print(f"[PROGRESS] {progress_pct} - Running {module}...")
        sys.stdout.flush()

        # Determine if we should pass the acceleration flag
        use_accel = args.hwaccel if (module in HWACCEL_SUPPORTED) else None
        
        res = run_validator_with_retry(category, module, input_video, outdir, args.mode, use_accel)
        results.append(res)

    # 3. AGGREGATION
    reports = [r["report"] for r in results if Path(r["report"]).exists()]
    master_report_path = outdir / "Master_Report.json"
    dashboard_path = outdir / "dashboard.html"

    if reports:
        print(f"[PROGRESS] 90 - Generating Master Report...")
        sys.stdout.flush()
        logger.info("\n--- GENERATING REPORTS ---")
        
        # Generate Master JSON
        subprocess.run([
            sys.executable, "-m", "src.postprocess.generate_master_report",
            "--inputs", *reports, "--output", str(master_report_path), "--profile", args.mode
        ])
        
        # Inject Governance Info
        if master_report_path.exists():
            try:
                with open(master_report_path, "r") as f:
                    data = json.load(f)
                
                data["governance"] = gov_info
                
                with open(master_report_path, "w") as f:
                    json.dump(data, f, indent=4)
                
                logger.info(f" [OK] Master Report: {master_report_path.name} (Governance Signed)")
            except Exception as e:
                logger.warning(f"Failed to sign Master Report: {e}")

            # Generate Dashboard
            subprocess.run([
                sys.executable, "-m", "src.visualization.visualize_report",
                "--input", str(master_report_path), "--output", str(dashboard_path)
            ])
            logger.info(f" [OK] Dashboard:      {dashboard_path.name}")

            # Auto-Correction Logic
            if args.fix:
                try:
                    with open(master_report_path, "r", encoding="utf-8") as f:
                        master = json.load(f)
                    audio_module = master.get("modules", {}).get("validate_loudness", {})
                    audio_status = audio_module.get("effective_status", "PASSED")
                    if audio_status in ["REJECTED", "WARNING"]:
                        logger.warning(f"Audio QC Status is {audio_status}. Initiating repair...")
                        run_correction(input_video, outdir)
                    else:
                        logger.info("Audio passed QC. No correction needed.")
                except Exception as e:
                    logger.warning(f"Could not parse Master Report for correction check: {e}")

    print(f"[PROGRESS] 100 - Analysis Complete")
    sys.stdout.flush()
    logger.info("\n[DONE] QC pipeline completed")

    if dashboard_path.exists():
        logger.info("Opening Dashboard...")
        try:
            webbrowser.open(dashboard_path.absolute().as_uri())
        except:
            pass

if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.stderr.write("CRITICAL ERROR IN MAIN.PY:\n")
        traceback.print_exc()
        sys.exit(1)