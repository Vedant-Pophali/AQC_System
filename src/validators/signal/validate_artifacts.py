import cv2
import json
import argparse
import os
import sys
import numpy as np
from statistics import mean
from pathlib import Path

from src.config.threshold_registry import PROFILES, DEFAULT_PROFILE

# UTF-8 safety (Windows)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# -------------------------
# ML / DNN Utilities
# -------------------------
def load_artifact_model(model_dir="models"):
    """
    Attempts to load a pre-trained OpenCV DNN model for No-Reference IQA.
    Expects 'aqc_artifacts.onnx' in the models directory.
    """
    model_path = Path(model_dir) / "aqc_artifacts.onnx"
    if model_path.exists():
        try:
            net = cv2.dnn.readNet(str(model_path))
            print(f" [INFO] Loaded ML Model: {model_path}")
            return net
        except Exception as e:
            print(f" [WARN] Failed to load ML model: {e}")
            return None
    return None

def score_frame_ml(net, frame):
    """
    Runs inference on a single frame.
    Returns a float score (0.0 - 1.0) where 1.0 is severe artifacts.
    """
    blob = cv2.dnn.blobFromImage(frame, 1/255.0, (224, 224), swapRB=True, crop=True)
    net.setInput(blob)
    preds = net.forward()
    # Assuming output class 1 is "Artifacts Present"
    # Adjust index based on specific model architecture
    return float(preds[0][0])

# -------------------------
# Heuristic Utilities
# -------------------------
def get_duration(path):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
    cap.release()
    return frames / fps if fps > 0 else 0.0


def blockiness_score(gray):
    """
    Block-boundary energy ratio (Heuristic).
    """
    h, w = gray.shape
    h8 = (h // 8) * 8
    w8 = (w // 8) * 8
    if h8 < 16 or w8 < 16:
        return 0.0

    g = gray[:h8, :w8].astype(np.float32)

    # Vertical and Horizontal boundaries (8-pixel grid)
    v1 = g[:, 7:w8-1:8]
    v2 = g[:, 8:w8:8]
    h1 = g[7:h8-1:8, :]
    h2 = g[8:h8:8, :]

    v_diff = np.abs(v2 - v1)
    h_diff = np.abs(h2 - h1)

    boundary_energy = np.mean(v_diff) + np.mean(h_diff)

    # Intra-block energy (smoothness check)
    intra_energy = np.mean(np.abs(np.diff(g, axis=1))) + 1e-6

    return float(boundary_energy / intra_energy)


def ringing_score(gray):
    """
    Ringing detection using Edge-Masked Variance.
    High variance *near* edges (but not *on* edges) suggests ringing/Gibbs phenomenon.
    """
    # 1. Detect strong edges
    edges = cv2.Canny(gray, 100, 200)

    # 2. Dilate to find the "neighborhood" of edges
    kernel = np.ones((3,3), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=1)

    # 3. Exclude the edge itself (we want the noise *around* it)
    ring_zone = cv2.subtract(dilated, edges)

    # 4. Calculate variance within this ringing zone
    if cv2.countNonZero(ring_zone) == 0:
        return 0.0

    mean_val, std_dev = cv2.meanStdDev(gray, mask=ring_zone)
    return float(std_dev[0][0]) / 255.0  # Normalize


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

    # Attempt to load ML model
    ml_net = load_artifact_model()
    using_ml = ml_net is not None

    report = {
        "module": "artifact_qc",
        "video_file": input_path,
        "status": "PASSED",
        "metrics": {
            "method": "ML_CNN" if using_ml else "Heuristic_Signal_Processing"
        },
        "events": []
    }

    if duration <= 0:
        report["status"] = "ERROR"
        _write(report, output_path)
        return

    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_step = max(1, int(fps * sample_interval))

    scores = [] # Stores (time, block/ml_score, ring_score)

    idx = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if idx % frame_step == 0:
                t = idx / fps

                if using_ml:
                    # ML Path: Single score for general artifacts
                    b_score = score_frame_ml(ml_net, frame)
                    r_score = 0.0 # ML covers both usually
                else:
                    # Heuristic Path
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    b_score = blockiness_score(gray)
                    r_score = ringing_score(gray)

                scores.append((t, b_score, r_score))

            idx += 1
    except Exception as e:
        report["status"] = "ERROR"
        report["events"].append({"type": "processing_error", "details": str(e)})
        _write(report, output_path)
        return
    finally:
        cap.release()

    if not scores:
        report["status"] = "ERROR"
        _write(report, output_path)
        return

    # -------------------------
    # Analysis & Clustering
    # -------------------------
    times = [s[0] for s in scores]
    b_vals = [s[1] for s in scores]
    r_vals = [s[2] for s in scores]

    report["metrics"]["avg_blockiness"] = round(mean(b_vals), 4)
    report["metrics"]["max_blockiness"] = round(max(b_vals), 4)
    if not using_ml:
        report["metrics"]["avg_ringing"] = round(mean(r_vals), 4)
        report["metrics"]["max_ringing"] = round(max(r_vals), 4)

    # Cluster defects
    def check_thresholds(val_list, threshold, name):
        start_t = None
        peak = 0.0

        for i, val in enumerate(val_list):
            t = times[i]
            if val > threshold:
                if start_t is None:
                    start_t = t
                peak = max(peak, val)
            else:
                if start_t is not None:
                    dur = t - start_t
                    if dur >= min_event_dur:
                        report["events"].append({
                            "type": "visual_artifact",
                            "subtype": name,
                            "start_time": round(start_t, 2),
                            "end_time": round(t, 2),
                            "details": f"Peak {name}: {round(peak, 3)} (Limit: {threshold})"
                        })
                        report["status"] = "REJECTED"
                    start_t = None
                    peak = 0.0

    check_thresholds(b_vals, block_th, "ML_Artifacts" if using_ml else "Blockiness")
    if not using_ml:
        check_thresholds(r_vals, ring_th, "Ringing")

    _write(report, output_path)


def _write(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Artifact QC")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default=DEFAULT_PROFILE)
    args = parser.parse_args()

    validate_artifacts(
        input_path=args.input,
        output_path=args.output,
        mode=args.mode
    )