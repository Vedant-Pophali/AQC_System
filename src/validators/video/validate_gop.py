import subprocess
import json
import argparse
import os
import sys

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


def validate_gop(input_path, output_path, mode):
    # -----------------------------------
    # RESOLVE THRESHOLDS (PROFILE-DRIVEN)
    # -----------------------------------
    profile = PROFILES.get(mode, PROFILES[DEFAULT_PROFILE])
    limits = profile["gop"]

    max_gop_length = limits["max_gop_length"]
    require_idr = limits["require_idr"]

    duration = get_duration(input_path)

    report = {
        "module": "gop_qc",
        "video_file": input_path,
        "status": "PASSED",
        "metrics": {},
        "events": []
    }

    # -----------------------------------
    # FFprobe GOP inspection
    # -----------------------------------
    cmd = [
        "ffprobe",
        "-select_streams", "v",
        "-show_frames",
        "-show_entries", "frame=pict_type,pts_time",
        "-of", "json",
        input_path
    ]

    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        if r.returncode != 0:
            raise RuntimeError("ffprobe GOP inspection failed")

        data = json.loads(r.stdout)
        frames = data.get("frames", [])

        if not frames:
            report["status"] = "REJECTED"
            raise ValueError("No video frames found")

        gop_lengths = []
        current_gop = 0
        idr_found = False

        for f in frames:
            pict = f.get("pict_type")
            current_gop += 1

            if pict == "I":
                gop_lengths.append(current_gop)
                current_gop = 0
                idr_found = True

        if current_gop > 0:
            gop_lengths.append(current_gop)

        max_observed_gop = max(gop_lengths)
        report["metrics"]["max_gop_length"] = max_observed_gop
        report["metrics"]["gop_lengths"] = gop_lengths[:10]  # sample only

        if max_observed_gop > max_gop_length:
            report["status"] = "REJECTED"

        if require_idr and not idr_found:
            report["status"] = "REJECTED"

    except Exception as e:
        if report["status"] == "PASSED":
            report["status"] = "ERROR"
        report["events"].append({
            "type": "gop_analysis_error",
            "start_time": 0.0,
            "end_time": duration,
            "details": str(e)
        })

    # -----------------------------------
    # FALLBACK EVENT (CONTRACT ENFORCEMENT)
    # -----------------------------------
    if report["status"] != "PASSED" and not report["events"]:
        report["events"].append({
            "type": "gop_structure_violation",
            "start_time": 0.0,
            "end_time": duration,
            "details": (
                f"GOP violation "
                f"(max_allowed={max_gop_length}, "
                f"observed={report['metrics'].get('max_gop_length')}, "
                f"idr_required={require_idr})"
            )
        })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GOP Structure QC")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default=DEFAULT_PROFILE)
    args = parser.parse_args()

    validate_gop(
        input_path=args.input,
        output_path=args.output,
        mode=args.mode
    )
