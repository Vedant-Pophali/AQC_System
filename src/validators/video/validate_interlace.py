import subprocess
import json
import argparse
import os
import sys
import re

from src.config.threshold_registry import PROFILES, DEFAULT_PROFILE

# UTF-8 safety (Windows)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def get_duration(path):
    try:
        p = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                path
            ],
            capture_output=True,
            text=True
        )
        return float(json.loads(p.stdout)["format"]["duration"])
    except Exception:
        return 0.0


def validate_interlace(input_path, output_path, mode):
    # -----------------------------------
    # RESOLVE THRESHOLDS (PROFILE-DRIVEN)
    # -----------------------------------
    profile = PROFILES.get(mode, PROFILES[DEFAULT_PROFILE])
    limits = profile["interlace"]

    max_interlaced_ratio = limits.get("max_interlaced_ratio", 0.0)
    # Threshold for Field PSNR (in dB).
    # Research: "High difference (Low PSNR) suggests temporal discontinuity"
    # If PSNR < 25-30dB, fields are significantly different (likely interlaced motion)
    field_psnr_threshold = limits.get("min_field_psnr", 30.0)

    duration = get_duration(input_path)

    report = {
        "module": "interlace_qc",
        "video_file": input_path,
        "status": "PASSED",
        "metrics": {},
        "events": []
    }

    # -----------------------------------
    # 1. FFmpeg idet (Standard Detection)
    # -----------------------------------
    # We run 'idet' to classify frames (TFF/BFF/Progressive)
    cmd_idet = [
        "ffmpeg",
        "-v", "info",
        "-i", input_path,
        "-vf", "idet",
        "-frames:v", "500", # Sample first 500 frames for speed
        "-f", "null",
        "-"
    ]

    try:
        r = subprocess.run(
            cmd_idet,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        logs = r.stderr

        # Parse idet: "TFF: 120 BFF: 0 Progressive: 380"
        m = re.search(r"TFF:\s*(\d+)\s+BFF:\s*(\d+)\s+Progressive:\s*(\d+)", logs)

        if m:
            tff = int(m.group(1))
            bff = int(m.group(2))
            prog = int(m.group(3))

            total = tff + bff + prog
            interlaced_frames = tff + bff
            ratio = interlaced_frames / total if total > 0 else 0.0

            report["metrics"]["idet_interlaced_ratio"] = round(ratio, 4)

            if ratio > max_interlaced_ratio:
                report["status"] = "REJECTED"
                report["events"].append({
                    "type": "interlace_flagged",
                    "details": f"IDET detected {interlaced_frames} interlaced frames (Ratio: {ratio:.2f})"
                })
    except Exception as e:
        print(f"[WARN] IDET failed: {e}")

    # -----------------------------------
    # 2. Field Differencing (PSNR)
    # -----------------------------------
    # Research Requirement: "Compare the two fields (odd and even lines) ... using PSNR"
    # Filter Logic: Split input -> Extract Top Field -> Extract Bottom Field -> Calculate PSNR

    cmd_psnr = [
        "ffmpeg",
        "-v", "error",
        "-i", input_path,
        "-filter_complex",
        "[0:v]split[a][b];[a]field=type=top[t];[b]field=type=bottom[b];[t][b]psnr=stats_file=-",
        "-frames:v", "200", # Sample 200 frames for deep analysis
        "-f", "null",
        "-"
    ]

    try:
        r_psnr = subprocess.run(
            cmd_psnr,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        # Output format: n:1 mse_avg:500.2 psnr_avg:25.34 ...
        # We look for the final "psnr_avg:[value]" or parse line by line
        psnr_vals = re.findall(r"psnr_avg:([0-9\.]+)", r_psnr.stdout + r_psnr.stderr)

        if psnr_vals:
            # Taking the average of the frame PSNRs (or the final summary if present)
            # The filter usually outputs a summary line at the end, specifically captured in stderr or stats_file
            # If multiple values found, the last one is usually the average for the stream
            avg_field_psnr = float(psnr_vals[-1])

            report["metrics"]["field_psnr_avg"] = avg_field_psnr

            # QC Logic:
            # Progressive content = Fields are spatially similar = High PSNR
            # Interlaced content with motion = Fields are temporally different = Low PSNR
            if avg_field_psnr < field_psnr_threshold:
                report["status"] = "REJECTED"
                report["events"].append({
                    "type": "interlace_field_divergence",
                    "details": f"High Field Divergence detected. PSNR: {avg_field_psnr:.2f} dB (Threshold: {field_psnr_threshold} dB). Possible combing artifacts."
                })

    except Exception as e:
        print(f"[WARN] Field PSNR failed: {e}")


    # -----------------------------------
    # FALLBACK / FINAL CHECK
    # -----------------------------------
    if report["status"] != "PASSED" and not report["events"]:
        report["events"].append({
            "type": "interlace_violation",
            "start_time": 0.0,
            "end_time": duration,
            "details": "Interlace metrics exceeded defined thresholds."
        })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interlace Detection QC")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default=DEFAULT_PROFILE)
    args = parser.parse_args()

    validate_interlace(
        input_path=args.input,
        output_path=args.output,
        mode=args.mode
    )