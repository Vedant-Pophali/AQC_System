import cv2
import numpy as np
import argparse
import json
import os
import sys

def calculate_blur_score(image):
    # Laplacian Variance: The standard "Focus Measure"
    # High variance = Sharp edges (In Focus)
    # Low variance = Few edges (Blurry)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()

def calculate_blockiness(image):
    # Simplified Blockiness Metric
    # We look for strong edges specifically at 8x8 grid boundaries (MPEG artifacts)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Calculate absolute difference between pixels
    # We look at rows and columns
    row_diff = np.abs(gray[:-1, :] - gray[1:, :])
    col_diff = np.abs(gray[:, :-1] - gray[:, 1:])

    # Analyze edges that align with 8-pixel grid (typical compression block size)
    # This is a heuristic estimation
    h, w = gray.shape

    # Sum of edge strength at 8th pixel boundaries
    row_blocks = np.sum(row_diff[7:h:8, :])
    col_blocks = np.sum(col_diff[:, 7:w:8])

    # Sum of edge strength everywhere else (noise/content)
    # We normalize to avoid flagging high-detail scenes as "blocky"
    total_edge_energy = np.sum(row_diff) + np.sum(col_diff)

    if total_edge_energy == 0: return 0.0

    block_energy = row_blocks + col_blocks

    # Ratio of "Grid Energy" to "Total Energy"
    return block_energy / total_edge_energy

def check_artifacts(input_path, output_path, step=10):
    print(f"[INFO] Artifact QC: Scanning for Pixelation & Blur in {os.path.basename(input_path)}...")

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print("[ERROR] Could not open video.")
        return

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    report = {
        "module": "artifact_qc",
        "video_file": input_path,
        "status": "PASSED",
        "events": [],
        "metrics": {"avg_blur": 0, "avg_blockiness": 0}
    }

    blur_scores = []
    block_scores = []

    # We analyze every Nth frame to save time (Speed vs Accuracy trade-off)
    current_frame = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if current_frame % step == 0:
            # 1. Check Blur
            blur = calculate_blur_score(frame)
            blur_scores.append(blur)

            # 2. Check Blockiness
            block = calculate_blockiness(frame)
            block_scores.append(block)

            # Thresholds (These need tuning based on content, but here are safe defaults)
            # Blur < 100 is usually quite blurry
            if blur < 50:
                report["events"].append({
                    "type": "Blurry Segment",
                    "start_time": current_frame / fps,
                    "details": f"Focus Loss (Score: {int(blur)})"
                })

        current_frame += 1

    cap.release()

    if blur_scores:
        avg_blur = sum(blur_scores) / len(blur_scores)
        avg_block = sum(block_scores) / len(block_scores)

        report["metrics"]["avg_blur"] = round(avg_blur, 2)
        report["metrics"]["avg_blockiness"] = round(avg_block, 4)

        # Decision Logic
        # Blockiness > 0.15 suggests significant compression artifacts
        if avg_block > 0.15:
            report["status"] = "WARNING"
            report["events"].append({
                "type": "Macro-blocking",
                "start_time": 0,
                "details": f"High Pixelation Detected (Score: {avg_block:.3f})"
            })

        # Global Blur check
        if avg_blur < 60:
            report["status"] = "REJECTED"
            report["events"].append({
                "type": "Severe Blur",
                "start_time": 0,
                "details": "Video is consistently out of focus."
            })

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding='utf-8') as f:
        json.dump(report, f, indent=4)
    print(f"[OK] Saved: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    check_artifacts(args.input, args.output)