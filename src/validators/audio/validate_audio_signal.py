import subprocess
import json
import argparse
import os
import sys
import re
from statistics import mean

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


def validate_audio_signal(input_path, output_path, mode):
    # -----------------------------------
    # RESOLVE THRESHOLDS (PROFILE-DRIVEN)
    # -----------------------------------
    profile = PROFILES.get(mode, PROFILES[DEFAULT_PROFILE])
    limits = profile["audio_signal"]

    max_dc_offset = limits.get("max_dc_offset", 0.005)

    # Research: "-1 indicates severe phase cancellation... a critical mixing error"
    min_phase_threshold = limits.get("min_phase_correlation", -0.8)

    report = {
        "module": "audio_signal_qc",
        "video_file": input_path,
        "status": "PASSED",
        "metrics": {},
        "events": []
    }

    duration = get_duration(input_path)

    # -----------------------------------
    # 1. DC OFFSET & PEAK (ASTATS)
    # -----------------------------------
    # We run astats separately to keep logs clean
    cmd_astats = [
        "ffmpeg",
        "-v", "error",
        "-i", input_path,
        "-af", "astats=metadata=1:reset=1",
        "-f", "null",
        "-"
    ]

    try:
        result = subprocess.run(cmd_astats, capture_output=True, text=True, encoding="utf-8", errors="replace")
        logs = result.stderr

        # DC OFFSET
        dc_offsets = re.findall(r"DC offset:\s+([0-9\.\-]+)", logs)
        if dc_offsets:
            try:
                dc_vals = [abs(float(x)) for x in dc_offsets if x.strip() not in ['-', '.']]
                if dc_vals:
                    max_dc = max(dc_vals)
                    report["metrics"]["max_dc_offset"] = max_dc
                    if max_dc > max_dc_offset:
                        report["status"] = "REJECTED"
                        report["events"].append({
                            "type": "audio_signal_defect",
                            "subtype": "dc_offset",
                            "details": f"DC Offset {max_dc} exceeds limit {max_dc_offset}"
                        })
            except Exception:
                pass

        # CLIPPING
        peak_levels = re.findall(r"Peak level dB:\s+([0-9\.\-]+)", logs)
        if peak_levels:
            try:
                peak_vals = [float(x) for x in peak_levels if x.strip() not in ['-', '.']]
                if peak_vals:
                    max_peak = max(peak_vals)
                    report["metrics"]["max_peak_db"] = max_peak
                    if max_peak >= 0.0:
                        report["status"] = "REJECTED"
                        report["events"].append({
                            "type": "audio_signal_defect",
                            "subtype": "clipping",
                            "details": f"Audio clipping detected. Peak: {max_peak} dB"
                        })
            except Exception:
                pass

    except Exception as e:
        print(f"[WARN] Astats failed: {e}")

    # -----------------------------------
    # 2. PHASE CORRELATION (APHASEMETER + AMETADATA)
    # -----------------------------------
    # We rely on 'ametadata' to print values to stdout.
    # Format: lavfi.aphasemeter.phase=0.123
    cmd_phase = [
        "ffmpeg",
        "-v", "error",
        "-i", input_path,
        "-af", "aphasemeter=video=0,ametadata=print:key=lavfi.aphasemeter.phase:file=-",
        "-f", "null",
        "-"
    ]

    try:
        # ametadata prints to stdout
        result_phase = subprocess.run(cmd_phase, capture_output=True, text=True, encoding="utf-8", errors="replace")
        phase_logs = result_phase.stdout

        # Parse: lavfi.aphasemeter.phase=-0.999812
        phase_vals = re.findall(r"lavfi\.aphasemeter\.phase=\s*([-+]?\d*\.?\d+)", phase_logs)

        if phase_vals:
            phase_floats = [float(x) for x in phase_vals]
            if phase_floats:
                min_phase = min(phase_floats)
                avg_phase = mean(phase_floats)

                report["metrics"]["min_phase"] = round(min_phase, 4)
                report["metrics"]["avg_phase"] = round(avg_phase, 4)

                if min_phase < min_phase_threshold:
                    report["status"] = "REJECTED"
                    report["events"].append({
                        "type": "audio_phase_error",
                        "start_time": 0.0,
                        "end_time": duration,
                        "details": f"Severe phase cancellation detected. Min Phase: {min_phase} (Limit: {min_phase_threshold})"
                    })
        else:
            # If still null, it might be mono or silent
            report["metrics"]["min_phase"] = None

    except Exception as e:
        report["status"] = "ERROR"
        report["events"].append({"type": "phase_analysis_error", "details": str(e)})

    # -----------------------------------
    # FINAL WRITE
    # -----------------------------------
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audio Signal QC")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default=DEFAULT_PROFILE)
    args = parser.parse_args()

    validate_audio_signal(
        input_path=args.input,
        output_path=args.output,
        mode=args.mode
    )