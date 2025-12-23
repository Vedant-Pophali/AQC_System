import cv2
import easyocr
import json
import argparse
import os
import sys
import traceback

try:
    sys.stdout.reconfigure(encoding="utf-8")
except: pass

def load_ocr_config():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "qc_config.json")
    defaults = {"sampling_interval_seconds": 5.0, "languages": ["en", "hi"]}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                return json.load(f).get("ocr_extraction", defaults)
        except: pass
    return defaults

OCR_CONFIG = load_ocr_config()

def run_ocr(video_path, output_path):
    if not os.path.exists(video_path):
        return

    try:
        langs = OCR_CONFIG.get("languages", ["en", "hi"])
        reader = easyocr.Reader(langs, gpu=False, verbose=False)
    except Exception as e:
        # Fail gracefully if model download fails
        with open(output_path, "w") as f:
            json.dump({"status": "ERROR", "error_details": str(e)}, f)
        return

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Logic: Sample every X seconds
    interval_sec = OCR_CONFIG.get("sampling_interval_seconds", 5.0)
    frame_interval = int(fps * interval_sec)

    events = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret: break

        # Process if interval matches OR if it's the very first frame
        if frame_idx % frame_interval == 0:
            timestamp = round(frame_idx / fps, 2)
            try:
                # Resize for speed if frame is huge
                h, w = frame.shape[:2]
                if w > 1280:
                    scale = 1280 / w
                    frame = cv2.resize(frame, (1280, int(h * scale)))

                results = reader.readtext(frame)
                for _, text, conf in results:
                    if conf >= 0.5: # threshold
                        events.append({
                            "type": "text_detected",
                            "start_time": timestamp,
                            "end_time": timestamp + interval_sec,
                            "confidence": float(conf),
                            "details": {"text": text.strip()}
                        })
            except: pass

        frame_idx += 1

    cap.release()

    report = {
        "module": "ocr_extraction",
        "video_file": video_path,
        "status": "PASSED",
        "events": events
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    run_ocr(args.input, args.output)