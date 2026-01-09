import argparse
import json
import subprocess
import sys
from pathlib import Path

from src.schema.qc_schema import validate_validator_output
from src.postprocess.generate_master_report import generate_master_report


# -------------------------
# Run QC for one segment
# -------------------------
def run_segment(segment, mode, outdir):
    segment_path = Path(segment["file"]).resolve()
    segment_name = segment_path.stem
    segment_outdir = Path(outdir) / segment_name
    segment_outdir.mkdir(parents=True, exist_ok=True)

    print(
        f"\n[RUN] Segment {segment['index']} "
        f"({segment['start_sec']}–{segment['end_sec']}s)"
    )

    # -------------------------
    # Run raw QC pipeline
    # -------------------------
    cmd = [
        sys.executable,
        "-m",
        "src.pipeline.run_qc_pipeline",
        "--input", str(segment_path),
        "--mode", mode,
        "--outdir", str(segment_outdir)
    ]

    result = subprocess.run(cmd)

    # HARD FAIL on execution error
    if result.returncode != 0:
        print(f"[ERROR] QC pipeline failed for segment {segment_name}")
        return False

    # -------------------------
    # Load + normalize + validate ONLY validator outputs
    # -------------------------
    validator_reports = []

    # IMPORTANT:
    # Only *_qc.json files are real validator outputs.
    for json_file in sorted(segment_outdir.glob("*_qc.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            report = json.load(f)

        # -------------------------
        # LEGACY NORMALIZATION
        # -------------------------
        if "video_file" not in report:
            report["video_file"] = str(segment_path)

        # HARD schema enforcement
        validate_validator_output(report)

        # Write back normalized report
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4)

        validator_reports.append(json_file)

    if not validator_reports:
        print(f"[ERROR] No validator reports produced for {segment_name}")
        return False

    # -------------------------
    # APPLY POLICY (MANDATORY – Phase 2.2)
    # -------------------------
    master_report_path = segment_outdir / "Master_Report.json"

    generate_master_report(
        input_reports=validator_reports,
        output_path=master_report_path,
        profile=mode
    )

    print(f"[OK] Segment master created: {master_report_path.name}")
    return True


# -------------------------
# CLI
# -------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Segment QC Runner (Phase 2.2 – Policy-Aware)"
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--mode", choices=["strict", "ott"], default="strict")
    parser.add_argument("--outdir", required=True)

    args = parser.parse_args()

    with open(args.manifest, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    segments = manifest.get("segments", [])
    if not segments:
        print("[FATAL] No segments found in manifest")
        sys.exit(1)

    print("\n>>> SEGMENT QC RUNNER")
    print(f"    Segments : {len(segments)}")
    print(f"    Mode     : {args.mode}")
    print(f"    Output   : {args.outdir}")

    failed = []

    for seg in segments:
        ok = run_segment(seg, args.mode, args.outdir)
        if not ok:
            failed.append(seg["file"])

    print("\n>>> SEGMENT QC SUMMARY")
    print(f"    Total    : {len(segments)}")
    print(f"    Failed   : {len(failed)}")

    if failed:
        print("Failed segments:")
        for f in failed:
            print(f" - {f}")
        sys.exit(1)

    print("[OK] Segment QC completed successfully")
    sys.exit(0)


if __name__ == "__main__":
    main()
