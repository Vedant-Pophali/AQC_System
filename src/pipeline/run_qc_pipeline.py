import argparse
import json
import sys
import subprocess
from pathlib import Path

from src.schema.qc_schema import validate_validator_output


# -----------------------------------
# VALIDATOR REGISTRY (ORDER MATTERS)
# -----------------------------------
VALIDATORS = [
    ("structure_qc", "src.validators.structure.validate_structure"),
    ("audio_qc", "src.validators.audio.validate_loudness"),
    ("audio_signal_qc", "src.validators.audio.validate_audio_signal"),
    ("signal_qc", "src.validators.signal.validate_signal"),
    ("qctools_qc", "src.validators.signal.validate_qctools"),
    ("artifact_qc", "src.validators.signal.validate_artifacts"),
    ("black_freeze_qc", "src.validators.video.validate_black_freeze"),
    ("frame_qc", "src.validators.video.validate_frames"),
    ("gop_qc", "src.validators.video.validate_gop"),
    ("interlace_qc", "src.validators.video.validate_interlace"),
    ("timestamp_qc", "src.validators.video.validate_timestamps"),
    ("avsync_qc", "src.validators.video.validate_avsync"),
]


# -----------------------------------
# EXECUTE SINGLE VALIDATOR
# -----------------------------------
def run_validator(module_name, module_path, input_path, outdir, mode):
    """
    Executes a single validator module.
    Enforces:
    - process success
    - report emission
    - schema compliance
    """
    output_path = Path(outdir) / f"{module_name}.json"

    cmd = [
        sys.executable,
        "-m", module_path,
        "--input", str(input_path),
        "--output", str(output_path)
    ]

    # Safely detect optional --mode support
    help_check = subprocess.run(
        [sys.executable, "-m", module_path, "--help"],
        capture_output=True,
        text=True
    )

    if "--mode" in help_check.stdout:
        cmd.extend(["--mode", mode])

    result = subprocess.run(cmd)

    if result.returncode != 0:
        raise RuntimeError(f"Validator crashed: {module_name}")

    if not output_path.exists():
        raise RuntimeError(f"Validator did not emit report: {module_name}")

    with open(output_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    # HARD CONTRACT ENFORCEMENT
    validate_validator_output(report)

    return report


# -----------------------------------
# MAIN PIPELINE (EXECUTION ONLY)
# -----------------------------------
def main():
    parser = argparse.ArgumentParser(description="Run Video QC Pipeline")
    parser.add_argument("--input", required=True)
    parser.add_argument("--outdir", default="qc_reports")
    parser.add_argument("--mode", choices=["strict", "ott"], default="strict")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    print("\n>>> QC PIPELINE (EXECUTION MODE)")
    print(f"    Input : {input_path}")
    print(f"    Mode  : {args.mode}")
    print(f"    Out   : {outdir}")

    try:
        for module_name, module_path in VALIDATORS:
            print(f"[RUN] {module_name}")
            run_validator(
                module_name=module_name,
                module_path=module_path,
                input_path=input_path,
                outdir=outdir,
                mode=args.mode
            )

    except Exception as e:
        # Pipeline failure = execution failure (NOT QC failure)
        print(f"[ERROR] Pipeline execution failed: {e}")
        sys.exit(3)

    print("[OK] All validators executed successfully")
    sys.exit(0)


if __name__ == "__main__":
    main()
