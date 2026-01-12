import argparse
import subprocess
import sys
import os
import webbrowser
from pathlib import Path
import json
import time
import shutil

# Import the new Governance layer
from src.config import threshold_registry

# -------------------------------------------------
# CONSTANTS & CONFIG
# -------------------------------------------------
MAX_RETRIES = 2
RETRY_DELAY_SEC = 1.0

VALIDATORS = [
    # 1. Hygiene & Metadata
    ("structure", "validate_structure"),
    # 2. Structural Integrity
    ("video", "validate_frames"),
    ("video", "validate_analog"),
    # 3. Visual Defects
    ("video", "validate_black_freeze"),
    ("video", "validate_interlace"),
    ("video", "validate_artifacts"),
    ("video", "validate_geometry"),
    # 4. Audio Quality
    ("audio", "validate_loudness"),
    ("audio", "validate_audio_signal"),
    # 5. Synchronization
    ("video", "validate_avsync"),
]

# -------------------------------------------------
# UTILS
# -------------------------------------------------
def check_dependencies():
    """Ensure ffmpeg is installed."""
    if not shutil.which("ffmpeg"):
        print(" [CRITICAL] FFmpeg not found in PATH. Please install FFmpeg.")
        sys.exit(1)
    if not shutil.which("ffprobe"):
        print(" [CRITICAL] FFprobe not found in PATH. Please install FFmpeg.")
        sys.exit(1)

def print_governance_header(mode):
    """
    Displays the Compliance & Governance info at startup.
    This fulfills 'CLI usage enforcement' by making parameters explicit.
    """
    gov = threshold_registry.get_governance_info(mode)
    cfg = threshold_registry.get_profile(mode)
    
    print("\n" + "="*60)
    print(f" AQC GOVERNANCE AUDIT")
    print("="*60)
    print(f" Profile Used      : {gov['active_profile'].upper()}")
    print(f" Description       : {gov['compliance_standard']}")
    print(f" Config Version ID : {gov['config_version_hash']} (Reproducibility Hash)")
    print("-" * 60)
    
    # Show key metrics for user confirmation
    audio_cfg = cfg.get('audio', {})
    sync_cfg = cfg.get('sync', {})
    
    print(f" [Audio] Target    : {audio_cfg.get('integrated_loudness_target', 'N/A')} LUFS")
    print(f" [Audio] True Peak : {audio_cfg.get('true_peak_max', 'N/A')} dBTP")
    print(f" [Sync]  Tolerance : +/- {sync_cfg.get('tolerance_ms', 'N/A')} ms")
    print("="*60 + "\n")
    return gov

def run_validator_with_retry(category, module, input_video, outdir, mode):
    report_path = outdir / f"report_{module}.json"
    module_path = f"src.validators.{category}.{module}"
    
    cmd = [
        sys.executable, "-m", module_path,
        "--input", str(input_video),
        "--output", str(report_path),
        "--mode", mode
    ]

    # Retry Loop
    for attempt in range(1, MAX_RETRIES + 2):
        start = time.time()
        status = "UNKNOWN"
        
        try:
            result = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            duration = round(time.time() - start, 2)
            
            # 1. Check Exit Code
            if result.returncode == 0 and report_path.exists():
                # 2. Check JSON validity
                try:
                    with open(report_path, "r", encoding="utf-8") as f:
                        d = json.load(f)
                        status = d.get("effective_status", d.get("status", "UNKNOWN"))
                    
                    # Success!
                    print(f" + {module:<30} | {status:<10} | {duration}s")
                    return {
                        "module": module,
                        "status": status,
                        "duration_sec": duration,
                        "report": str(report_path)
                    }
                except json.JSONDecodeError:
                    print(f" [WARN] {module} produced corrupt JSON on attempt {attempt}")
            
            else:
                # Print stderr if failed for debugging
                if attempt > MAX_RETRIES:
                    print(f" [FAIL] {module} error:\n{result.stderr[:200]}")
                else:
                    print(f" [WARN] {module} failed (Exit: {result.returncode}) on attempt {attempt}")

        except Exception as e:
            print(f" [ERR] Execution error on {module}: {e}")

        # If we are here, it failed. Wait before retry.
        if attempt <= MAX_RETRIES:
            time.sleep(RETRY_DELAY_SEC)
            # print(f" ... Retrying {module} ({attempt}/{MAX_RETRIES})...")

    # If all retries fail:
    print(f" ! {module:<30} | CRASHED    | 0.0s")
    
    # Generate a "Ghost" Report so the dashboard knows it crashed
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

def run_correction(input_video, outdir):
    print("\n--- AUTO-CORRECTION (Loudness) ---")
    output_video = outdir / f"fixed_{input_video.name}"
    cmd = [
        sys.executable, "-m", "src.postprocess.correct_loudness",
        "--input", str(input_video), "--output", str(output_video)
    ]
    try:
        subprocess.run(cmd, check=True)
        print(f" [SUCCESS] Corrected file saved to: {output_video}")
    except subprocess.CalledProcessError:
        print(" [FAILED] Correction workflow failed.")

# -------------------------------------------------
# MAIN
# -------------------------------------------------
def main():
    check_dependencies()

    parser = argparse.ArgumentParser(description="AQC Core QC Pipeline")
    parser.add_argument("--input", required=True, help="Path to input video file")
    parser.add_argument("--outdir", required=True, help="Base directory to save reports")
    # Updated choices to match Registry
    parser.add_argument("--mode", choices=["strict", "netflix_hd", "youtube", "ott"], default="strict", help="QC Profile")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix audio loudness errors")

    args = parser.parse_args()

    input_video = Path(args.input).resolve()
    base_outdir = Path(args.outdir).resolve()
    
    if not input_video.exists():
        print(f" [FATAL] Input file not found: {input_video}")
        sys.exit(1)

    # Output folder setup
    outdir = base_outdir / f"{input_video.stem}_qc_report"
    outdir.mkdir(parents=True, exist_ok=True)

    # 1. Print Governance / Compliance Header
    gov_info = print_governance_header(args.mode)

    results = []

    # 2. EXECUTE MODULES
    print("--- MODULE EXECUTION ---")
    for category, module in VALIDATORS:
        res = run_validator_with_retry(category, module, input_video, outdir, args.mode)
        results.append(res)

    # -------------------------------------------------
    # AGGREGATION & REPORTING
    # -------------------------------------------------
    reports = [r["report"] for r in results if Path(r["report"]).exists()]
    master_report_path = outdir / "Master_Report.json"
    dashboard_path = outdir / "dashboard.html"

    if reports:
        print("\n--- GENERATING REPORTS ---")
        
        # 3. Generate Master JSON
        subprocess.run([
            sys.executable, "-m", "src.postprocess.generate_master_report",
            "--inputs", *reports, "--output", str(master_report_path), "--profile", args.mode
        ])
        
        # 4. Inject Governance Info into Master Report (Traceability)
        if master_report_path.exists():
            try:
                with open(master_report_path, "r") as f:
                    data = json.load(f)
                
                # Inject the governance block
                data["governance"] = gov_info
                
                with open(master_report_path, "w") as f:
                    json.dump(data, f, indent=4)
                
                print(f" [OK] Master Report: {master_report_path.name} (Governance Signed)")
            except Exception as e:
                print(f" [WARN] Failed to sign Master Report with governance info: {e}")

            # 5. Generate Visualization Dashboard
            subprocess.run([
                sys.executable, "-m", "src.visualization.visualize_report",
                "--input", str(master_report_path), "--output", str(dashboard_path)
            ])
            print(f" [OK] Dashboard:      {dashboard_path.name}")

            # 6. Auto-Fix Logic
            if args.fix:
                try:
                    with open(master_report_path, "r", encoding="utf-8") as f:
                        master = json.load(f)
                    audio_module = master.get("modules", {}).get("validate_loudness", {})
                    audio_status = audio_module.get("effective_status", "PASSED")
                    if audio_status in ["REJECTED", "WARNING"]:
                        print(f"\n[!] Audio QC Status is {audio_status}. Initiating repair...")
                        run_correction(input_video, outdir)
                    else:
                        print("\n[i] Audio passed QC. No correction needed.")
                except Exception as e:
                    print(f"[WARN] Could not parse Master Report for correction check: {e}")

    print("\n[DONE] QC pipeline completed")

    if dashboard_path.exists():
        print("Opening Dashboard...")
        try:
            webbrowser.open(dashboard_path.absolute().as_uri())
        except:
            pass

if __name__ == "__main__":
    main()