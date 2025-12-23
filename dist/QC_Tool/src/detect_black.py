import cv2
import numpy as np
import json
import argparse
import os
import sys
import traceback

try:
    sys.stdout.reconfigure(encoding="utf-8")
except:
    pass


def safe_fail(output_path, message):
    data = {
        "module": "visual_qc",
        "video_file": "unknown",
        "status": "ERROR",
        "events": [],
        "error_details": message
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def analyze(video_path, output_path):
    if not os.path.exists(video_path):
        safe_fail(output_path, "Video file not found")
        return

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        safe_fail(output_path, "OpenCV could not open video (codec issue)")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        fps = 30

    frame_count = 0
    black_frames = 0
    events = []

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            if frame is None:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            dark_ratio = float(np.mean(gray < 13))

            if dark_ratio >= 0.98:
                black_frames += 1
            else:
                if black_frames / fps >= 2:
                    end = frame_count / fps
                    start = end - (black_frames / fps)
                    events.append({
                        "type": "black_screen",
                        "start_time": round(start, 2),
                        "end_time": round(end, 2),
                        "confidence": 1.0,
                        "details": {"duration": round(black_frames / fps, 2)}
                    })
                black_frames = 0

        # 🔑 HANDLE BLACK SEGMENT AT EOF
        if black_frames / fps >= 2:
            end = frame_count / fps
            start = end - (black_frames / fps)
            events.append({
                "type": "black_screen",
                "start_time": round(start, 2),
                "end_time": round(end, 2),
                "confidence": 1.0,
                "details": {"duration": round(black_frames / fps, 2)}
            })

        cap.release()

        report = {
            "module": "visual_qc",
            "video_file": video_path,
            "status": "REJECTED" if events else "PASSED",
            "events": events
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4)

    except Exception:
        cap.release()
        safe_fail(output_path, traceback.format_exc())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    analyze(args.input, args.output)
    sys.exit(0)
