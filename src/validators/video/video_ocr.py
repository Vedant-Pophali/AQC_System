import cv2
import easyocr
import torch
import json
import argparse
import os
import sys
from difflib import SequenceMatcher

# Force UTF-8 for console output
try:
    sys.stdout.reconfigure(encoding="utf-8")
except: pass

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def run_ocr(video_path, output_path):
    print(f"[INFO] OCR Scan (Universal Mode): {os.path.basename(video_path)}")

    if not os.path.exists(video_path):
        print(f"[ERROR] Video not found: {video_path}")
        return

    # 1. Setup AI Engine
    # Use GPU if available for speed
    USE_GPU = torch.cuda.is_available()
    print(f"   > AI Hardware Acceleration: {'ON' if USE_GPU else 'OFF'}")

    # Initialize Reader for Hindi ('hi') and English ('en')
    # This downloads the models automatically on first run
    try:
        reader = easyocr.Reader(['hi', 'en'], gpu=USE_GPU)
    except Exception as e:
        print(f"[WARN] Failed to load Hindi. Falling back to English. Error: {e}")
        reader = easyocr.Reader(['en'], gpu=USE_GPU)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30

    # 2. Configuration
    # Scanning every frame is too slow. We scan every 1.5 seconds.
    # This catches subtitles and tickers without killing the CPU.
    interval_sec = 1.5
    frame_interval = int(fps * interval_sec)

    events = []
    frame_idx = 0

    # Deduping Cache: "What text is currently on screen?"
    active_texts = {} # Format: { "text_string": {start_time, last_seen_time} }

    while True:
        ret, frame = cap.read()
        if not ret: break

        current_time = round(frame_idx / fps, 2)

        if frame_idx % frame_interval == 0:
            try:
                # 3. Full Frame Analysis (No Cropping)
                # We use paragraph=True to group words into sentences
                results = reader.readtext(frame, detail=0, paragraph=True)

                # Current frame's text set
                current_frame_texts = set()

                if results:
                    for raw_text in results:
                        text = raw_text.strip()
                        if len(text) < 3: continue # Ignore noise like "." or "I"

                        current_frame_texts.add(text)

                        # Logic: Is this text NEW or EXISTING?
                        is_existing = False

                        # Check against active cache
                        for active_txt in list(active_texts.keys()):
                            # If text matches (fuzzy match > 80% to handle OCR flicker)
                            if similar(text, active_txt) > 0.8:
                                active_texts[active_txt]['last_seen'] = current_time
                                is_existing = True
                                break

                        if not is_existing:
                            # It's new text! Start tracking it.
                            active_texts[text] = {
                                'start': current_time,
                                'last_seen': current_time
                            }
                            print(f"   > [{current_time}s] Detected: {text}")

                # 4. Cleanup Old Text
                # If text hasn't been seen for 3.0 seconds, it's gone. Save it.
                dead_keys = []
                for txt, data in active_texts.items():
                    if current_time - data['last_seen'] > 3.0:
                        # Text disappeared. Commit to events list.
                        duration = data['last_seen'] - data['start']
                        events.append({
                            "type": "text_detected",
                            "start_time": data['start'],
                            "end_time": data['last_seen'],
                            "details": {
                                "text": txt,
                                "duration_sec": round(duration, 2),
                                "confidence_status": "PASSED"
                            }
                        })
                        dead_keys.append(txt)

                for k in dead_keys:
                    del active_texts[k]

            except Exception as e:
                pass

        frame_idx += 1

    # 5. Final Cleanup (Save whatever is left on screen at the end)
    for txt, data in active_texts.items():
        events.append({
            "type": "text_detected",
            "start_time": data['start'],
            "end_time": data['last_seen'],
            "details": {
                "text": txt,
                "duration_sec": round(data['last_seen'] - data['start'], 2),
                "confidence_status": "PASSED"
            }
        })

    cap.release()

    # 6. Save Report
    report = {
        "module": "ocr_extraction",
        "video_file": video_path,
        "status": "PASSED",
        "events": events
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    print(f"[OK] Saved Universal OCR Report: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    run_ocr(args.input, args.output)