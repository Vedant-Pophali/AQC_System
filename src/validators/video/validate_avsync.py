import subprocess
import json
import argparse
import os
import sys
import bisect
import statistics

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


def probe_packets(input_path):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_packets",
        "-show_entries", "packet=pts_time,stream_index",
        "-of", "json",
        input_path
    ]

    r = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if r.returncode != 0:
        return None, r.stderr

    return json.loads(r.stdout).get("packets", []), None


def validate_avsync(input_path, output_path, mode):
    # -----------------------------------
    # RESOLVE THRESHOLDS (PROFILE-DRIVEN)
    # -----------------------------------
    profile = PROFILES.get(mode, PROFILES[DEFAULT_PROFILE])
    limits = profile["avsync"]

    max_offset = limits["max_offset_sec"]
    method = limits.get("method", "median")

    duration = get_duration(input_path)

    report = {
        "module": "avsync_qc",
        "video_file": input_path,
        "status": "PASSED",
        "metrics": {},
        "events": []
    }

    packets, err = probe_packets(input_path)
    if packets is None:
        report["status"] = "ERROR"
        report["events"].append({
            "type": "avsync_probe_failure",
            "start_time": 0.0,
            "end_time": duration,
            "details": err
        })
        _write(report, output_path)
        return

    # -----------------------------------
    # SEPARATE AUDIO / VIDEO PACKETS
    # -----------------------------------
    v_pts = []
    a_pts = []

    for pkt in packets:
        pts = pkt.get("pts_time")
        if pts is None:
            continue

        if pkt.get("stream_index") == 0:
            v_pts.append(float(pts))
        elif pkt.get("stream_index") == 1:
            a_pts.append(float(pts))

    report["metrics"]["video_packets"] = len(v_pts)
    report["metrics"]["audio_packets"] = len(a_pts)

    if len(v_pts) < 10 or len(a_pts) < 10:
        report["status"] = "ERROR"
        report["events"].append({
            "type": "avsync_insufficient_packets",
            "start_time": 0.0,
            "end_time": duration,
            "details": "Insufficient audio or video packets for AV sync analysis"
        })
        _write(report, output_path)
        return

    # -----------------------------------
    # OFFSET ESTIMATION (MEDIAN-BASED)
    # -----------------------------------
    a_pts.sort()
    offsets = []

    sample_step = max(1, len(v_pts) // 200)
    for v in v_pts[::sample_step]:
        idx = bisect.bisect_left(a_pts, v)
        candidates = []
        if idx > 0:
            candidates.append(a_pts[idx - 1])
        if idx < len(a_pts):
            candidates.append(a_pts[idx])

        if candidates:
            nearest_a = min(candidates, key=lambda x: abs(x - v))
            offsets.append(nearest_a - v)

    if offsets:
        if method == "median":
            offset_val = statistics.median(offsets)
        else:
            offset_val = statistics.mean(offsets)

        offset_val = round(offset_val, 3)
        report["metrics"]["av_offset_sec"] = offset_val
        report["metrics"]["method"] = method

        if abs(offset_val) > max_offset:
            report["status"] = "REJECTED"

    # -----------------------------------
    # FALLBACK EVENT (CONTRACT ENFORCEMENT)
    # -----------------------------------
    if report["status"] != "PASSED" and not report["events"]:
        report["events"].append({
            "type": "avsync_violation",
            "start_time": 0.0,
            "end_time": duration,
            "details": (
                f"A/V sync offset {report['metrics'].get('av_offset_sec')}s "
                f"exceeds limit ±{max_offset}s"
            )
        })

    _write(report, output_path)


def _write(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audio-Video Sync QC")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default=DEFAULT_PROFILE)
    args = parser.parse_args()

    validate_avsync(
        input_path=args.input,
        output_path=args.output,
        mode=args.mode
    )
