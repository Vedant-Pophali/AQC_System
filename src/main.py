import argparse
import subprocess
import sys
from pathlib import Path
import json
import time


# -------------------------------------------------
# CONSTANTS
# -------------------------------------------------
VALIDATORS = [
    ("structure", "validate_structure"),
    ("video", "detect_black"),
    ("video", "validate_interlace"),
    ("audio", "validate_loudness"),
    ("audio", "validate_audio_signal"),
    ("signal", "validate_qctools"),
    ("signal", "validate_signal"),
    ("signal", "validate_artifacts"),
]


# -------------------------------------------------
# RUNNER
# -------------------------------------------------
def run_validator(category, module, input_video, outdir, mode):
    report_path = outdir / f"report_{module}.json"

    cmd = [
        sys.executable,
        "-m",
        f"src.validators.{category}.{module}",
        "--input", str(input_video),
        "--output", str(report_path),
        "--mode", mode
    ]

    start = time.time()
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    duration = round(time.time() - start, 2)

    status = "PASSED" if result.returncode == 0 else "FAILED"

    print(f" + {module:<30} | {status:<6} | {duration}s")

    return {
        "module": module,
        "status": status,
        "duration_sec": duration,
        "report": str(report_path)
    }


# -------------------------------------------------
# MAIN
# -------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="AQC Core QC Pipeline")
    parser.add_argument("--input", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--mode", choices=["strict", "ott"], default="strict")
    parser.add_argument("--spark", action="store_true")

    args = parser.parse_args()

    input_video = Path(args.input).resolve()
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    print("\n=== AQC NORMAL PIPELINE MODE ===")
    print(f"Input   : {input_video}")
    print(f"Output  : {outdir}")
    print(f"Mode    : {args.mode}")
    print(f"Spark   : {'ON' if args.spark else 'OFF'}")
    print("=" * 31 + "\n")

    results = []

    print("--- MODULE RESULTS ---")
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
    # AGGREGATION
    # -------------------------------------------------
    reports = [r["report"] for r in results if Path(r["report"]).exists()]

    if reports:
        subprocess.run([
            sys.executable,
            "-m",
            "src.postprocess.generate_master_report",
            "--inputs", *reports,
            "--output", str(outdir / "Master_Report.json")
        ])

        subprocess.run([
            sys.executable,
            "-m",
            "src.visualization.visualize_report",
            "--input", str(outdir / "Master_Report.json"),
            "--output", str(outdir / "dashboard.html")
        ])

    print("\n[DONE] QC pipeline completed")


if __name__ == "__main__":
    main()
