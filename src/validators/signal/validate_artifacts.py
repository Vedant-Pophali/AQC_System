import cv2
import json
import argparse
import os
import sys
import numpy as np
from statistics import mean

from src.config.threshold_registry import PROFILES, DEFAULT_PROFILE

# UTF-8 safety (Windows)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# -------------------------
# Utilities
# -------------------------

def get_duration(path):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
    cap.release()
    return frames / fps if fps > 0 else 0.0


def blockiness_score(gray):
    """
    Block-boundary energy ratio.
    Broadcast-safe, 8x8 aligned.
    """
    h, w = gray.shape

    h8 = (h // 8) * 8
    w8 = (w // 8) * 8
    if h8 < 16 or w8 < 16:
        return 0.0

    g = gray[:h8, :w8].astype(np.float32)

    # Trim to matching boundaries
    v1 = g[:, 7:w8-1:8]
    v2 = g[:, 8:w8:8]

    h1 = g[7:h8-1:8, :]
    h2 = g[8:h8:8, :]

    v_edges = np.abs(v2 - v1)
    h_edges = np.abs(h2 - h1)

    boundary_energy = np.mean(v_edges) + np.mean(h_edges)
    intra_energy = np.mean(np.abs(np.diff(g, axis=1))) + 1e-6

    return float(boundary_energy / intra_energy)


def ringing_score(gray):
    """
    Ringing detection temporarily disabled.
    Returns 0.0 to indicate no ringing measured.
    """
    return 0.0

# -------------------------
# Main Validator
# -------------------------

def validate_artifacts(input_path, output_path, mode):
    profile = PROFILES.get(mode, PROFILES[DEFAULT_PROFILE])
    limits = profile["artifacts"]

    block_th = limits["blockiness_threshold"]
    ring_th = limits["ringing_threshold"]
    sample_interval = limits.get("sample_interval_sec", 1.0)
    min_event_dur = limits.get("min_artifact_duration_sec", 1.0)

    duration = get_duration(input_path)

    report = {
        "module": "artifact_qc",
        "video_file": input_path,
        "status": "PASSED",
        "metrics": {},
        "events": []
    }

    # Hard fail if duration invalid
    if duration <= 0:
        report["status"] = "ERROR"
        report["events"].append({
            "type": "artifact_analysis_error",
            "start_time": 0.0,
            "end_time": 0.0,
            "details": "Invalid video duration"
        })
        _write(report, output_path)
        return

    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_step = max(1, int(fps * sample_interval))

    b_scores = []
    r_scores = []
    times = []

    idx = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if idx % frame_step == 0:
                t = idx / fps
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                b = blockiness_score(gray)
                r = ringing_score(gray)

                # HARD numeric guarantee
                b_scores.append(float(b))
                r_scores.append(float(r))
                times.append(t)

            idx += 1

    except Exception as e:
        cap.release()
        report["status"] = "ERROR"
        report["events"].append({
            "type": "artifact_processing_error",
            "start_time": 0.0,
            "end_time": duration,
            "details": str(e)
        })
        _write(report, output_path)
        return

    cap.release()

    # Defensive: no samples collected
    if not b_scores or not r_scores:
        report["status"] = "ERROR"
        report["events"].append({
            "type": "artifact_analysis_error",
            "start_time": 0.0,
            "end_time": duration,
            "details": "No valid artifact samples collected"
        })
        _write(report, output_path)
        return

    report["metrics"] = {
        "blockiness": {
            "mean": round(mean(b_scores), 4),
            "max": round(max(b_scores), 4),
            "threshold": block_th
        },
        "ringing": {
            "mean": round(mean(r_scores), 4),
            "max": round(max(r_scores), 4),
            "threshold": ring_th
        },
        "sampled_frames": len(times),
        "profile": mode
    }

    # -------------------------
    # Temporal clustering
    # -------------------------

    def cluster(scores, threshold, label):
        nonlocal report
        start = None
        peak = 0.0

        for t, s in zip(times, scores):
            if s > threshold:
                if start is None:
                    start = t
                    peak = s
                else:
                    peak = max(peak, s)
            else:
                if start is not None and (t - start) >= min_event_dur:
                    report["events"].append({
                        "type": "compression_artifact",
                        "artifact": label,
                        "start_time": round(start, 2),
                        "end_time": round(t, 2),
                        "severity": "HIGH" if peak > threshold * 1.5 else "MEDIUM",
                        "details": {
                            "peak_score": round(peak, 4),
                            "threshold": threshold
                        }
                    })
                    report["status"] = "REJECTED"
                start = None
                peak = 0.0

    cluster(b_scores, block_th, "blockiness")
    cluster(r_scores, ring_th, "ringing")

    # Contract fallback (should never trigger, but enforced)
    if report["status"] != "PASSED" and not report["events"]:
        report["events"].append({
            "type": "artifact_violation",
            "start_time": 0.0,
            "end_time": duration,
            "details": "Artifact threshold exceeded"
        })

    _write(report, output_path)


def _write(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compression Artifact QC")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default=DEFAULT_PROFILE)
    args = parser.parse_args()

    validate_artifacts(
        input_path=args.input,
        output_path=args.output,
        mode=args.mode
    )