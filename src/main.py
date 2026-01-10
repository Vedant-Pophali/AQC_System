import argparse
import subprocess
import sys
import os
import webbrowser  # Added to handle browser opening
from pathlib import Path
import json
import time

# -------------------------------------------------
# CONSTANTS & CONFIG
# -------------------------------------------------
# Registry of active validators
# Format: (category_folder, module_filename_without_extension)
VALIDATORS = [
    # 1. Hygiene & Metadata
    ("structure", "validate_structure"),       # File Integrity, Tracks, Timecode

    # 2. Structural Integrity
    ("video", "validate_frames"),              # Bitstream Continuity
    ("video", "validate_analog"),              # Analog Defects (VREP)

    # 3. Visual Defects (NOW COMPLETE)
    ("video", "validate_black_freeze"),        # Black/Freeze/Fade
    ("video", "validate_interlace"),           # Fields & Combing
    ("video", "validate_artifacts"),           # Compression/Bitrate
    ("video", "validate_geometry"),            # Crop/Letterbox Detection

    # 4. Audio Quality
    ("audio", "validate_loudness"),            # EBU R.128
    ("audio", "validate_audio_signal"),        # Phase, Distortion

    # 5. Synchronization
    ("video", "validate_avsync"),              # Timestamp Drift
]

# -------------------------------------------------
# RUNNER
# -------------------------------------------------
def run_validator(category, module, input_video, outdir, mode):
    report_path = outdir / f"report_{module}.json"
    
    # Construct module path (e.g., src.validators.video.validate_black_freeze)
    module_path = f"src.validators.{category}.{module}"

    cmd = [
        sys.executable,
        "-m",
        module_path,
        "--input", str(input_video),
        "--output", str(report_path),
        "--mode", mode
    ]

    start = time.time()
    try:
        # Run the module as a subprocess
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        duration = round(time.time() - start, 2)
        
        # Check execution status
        if not report_path.exists():
            status = "CRASHED"
        elif result.returncode != 0:
            status = "ERROR" 
        else:
            # Quick peek at status inside the generated JSON
            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    status = d.get("effective_status", d.get("status", "UNKNOWN"))
            except:
                status = "CORRUPT"
                
    except Exception as e:
        duration = 0.0
        status = f"EXEC_FAIL: {e}"

    # Print a nice table row
    print(f" + {module:<30} | {status:<10} | {duration}s")

    return {
        "module": module,
        "status": status,
        "duration_sec": duration,
        "report": str(report_path)
    }

def run_correction(input_video, outdir):
    """
    Triggers the Two-Pass Loudness Correction if needed.
    """
    print("\n--- AUTO-CORRECTION (Loudness) ---")
    
    # Define output filename
    output_video = outdir / f"fixed_{input_video.name}"
    
    cmd = [
        sys.executable,
        "-m",
        "src.postprocess.correct_loudness",
        "--input", str(input_video),
        "--output", str(output_video)
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
    parser = argparse.ArgumentParser(description="AQC Core QC Pipeline")
    parser.add_argument("--input", required=True, help="Path to input video file")
    parser.add_argument("--outdir", required=True, help="Directory to save reports")
    parser.add_argument("--mode", choices=["strict", "ott"], default="strict", help="QC Profile")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix audio loudness errors")

    args = parser.parse_args()

    input_video = Path(args.input).resolve()
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    print("\n=== AQC PIPELINE START ===")
    print(f"Input    : {input_video}")
    print(f"Output   : {outdir}")
    print(f"Mode     : {args.mode}")
    print(f"Auto-Fix : {'ON' if args.fix else 'OFF'}")
    print("=" * 40 + "\n")

    results = []

    # 1. EXECUTE MODULES
    print("--- MODULE EXECUTION ---")
    for category, module in VALIDATORS:
        res = run_validator(
            category=category,
            module=module,
            input_video=input_video,
            outdir=outdir,
            mode=args.mode
        )
        results.append(res)

    # -------------------------------------------------
    # AGGREGATION & REPORTING
    # -------------------------------------------------
    reports = [r["report"] for r in results if Path(r["report"]).exists()]
    master_report_path = outdir / "Master_Report.json"
    dashboard_path = outdir / "dashboard.html"

    if reports:
        print("\n--- GENERATING REPORTS ---")
        # 2. Generate Master JSON
        subprocess.run([
            sys.executable,
            "-m",
            "src.postprocess.generate_master_report",
            "--inputs", *reports,
            "--output", str(master_report_path),
            "--profile", args.mode
        ])
        print(f" [OK] Master Report: {master_report_path}")

        # 3. Generate Visualization Dashboard
        subprocess.run([
            sys.executable,
            "-m",
            "src.visualization.visualize_report",
            "--input", str(master_report_path),
            "--output", str(dashboard_path)
        ])
        print(f" [OK] Dashboard:      {dashboard_path}")

        # -------------------------------------------------
        # OPTIONAL CORRECTION
        # -------------------------------------------------
        if args.fix:
            # Check Master Report for Audio Failures
            try:
                with open(master_report_path, "r", encoding="utf-8") as f:
                    master = json.load(f)
                
                # Check if "validate_loudness" failed
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

    # -------------------------------------------------
    # AUTO-OPEN DASHBOARD
    # -------------------------------------------------
    if dashboard_path.exists():
        print("Opening Dashboard in Browser...")
        try:
            # Ensure path is absolute URI for browser compatibility
            webbrowser.open(dashboard_path.absolute().as_uri())
        except Exception as e:
            print(f"Could not auto-open browser: {e}")


if __name__ == "__main__":
    main()