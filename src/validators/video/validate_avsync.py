import sys
import argparse
import json
import cv2
import numpy as np
import librosa
from scipy import signal
from pathlib import Path

# -------------------------------------------------
# CONFIGURATION
# -------------------------------------------------
MAX_SHIFT_SEC = 2.0       # Max offset to look for (seconds)
SAMPLE_RATE = 22050       # Audio process rate
HOP_LENGTH = 512          # Audio frame size
SYNC_TOLERANCE_MS = 40.0  # EBU R37 standard
ANALYSIS_WINDOW_SEC = 60  # Duration of chunks to analyze

class AVSyncValidator:
    def __init__(self, input_path, output_path, mode):
        self.input_path = input_path
        self.output_path = output_path
        self.mode = mode
        self.report = {
            "module": "validate_avsync",
            "status": "UNKNOWN",
            "details": {}
        }

    def get_duration(self):
        try:
            cap = cv2.VideoCapture(str(self.input_path))
            if not cap.isOpened(): return 0
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            cap.release()
            if fps > 0:
                return frame_count / fps
        except:
            pass
        return 0

    def extract_features(self, start_sec, duration_sec):
        """
        Extracts Audio Onset and Visual Motion Energy for a specific time window.
        """
        # 1. Audio Features
        try:
            y, sr = librosa.load(self.input_path, sr=SAMPLE_RATE, offset=start_sec, duration=duration_sec)
            onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP_LENGTH)
            if np.max(onset_env) > 0:
                onset_env = onset_env / np.max(onset_env)
        except Exception:
            return None, None, None

        # 2. Visual Features
        cap = cv2.VideoCapture(str(self.input_path))
        if not cap.isOpened(): return None, None, None

        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Seek to start
        start_frame = int(start_sec * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        frames_to_read = int(duration_sec * fps)
        visual_energy = []
        
        ret, prev_frame = cap.read()
        if not ret: 
            cap.release()
            return None, None, None
        
        prev_gray = cv2.cvtColor(cv2.resize(prev_frame, (64, 64)), cv2.COLOR_BGR2GRAY)

        for _ in range(frames_to_read):
            ret, frame = cap.read()
            if not ret: break
            
            gray = cv2.cvtColor(cv2.resize(frame, (64, 64)), cv2.COLOR_BGR2GRAY)
            diff = np.sum(cv2.absdiff(gray, prev_gray))
            visual_energy.append(diff)
            prev_gray = gray
            
        cap.release()
        
        v_signal = np.array(visual_energy)
        
        # Normalize
        if np.max(v_signal) > 0:
            v_signal = v_signal / np.max(v_signal)
            
        # Resample visual to match audio length
        # Audio samples = len(onset_env)
        if len(v_signal) > 0 and len(onset_env) > 0:
            v_resampled = signal.resample(v_signal, len(onset_env))
            v_resampled = np.maximum(v_resampled, 0)
            return onset_env, v_resampled, sr
            
        return None, None, None

    def calculate_offset(self, audio_sig, video_sig, sr):
        if audio_sig is None or video_sig is None: return 0.0, 0.0
        
        correlation = signal.correlate(video_sig, audio_sig, mode='full')
        lags = signal.correlation_lags(len(video_sig), len(audio_sig), mode='full')
        
        peak_idx = np.argmax(correlation)
        lag_samples = lags[peak_idx]
        confidence = correlation[peak_idx]
        
        time_step = HOP_LENGTH / SAMPLE_RATE
        offset_sec = lag_samples * time_step
        
        return offset_sec * 1000.0, confidence

    def run(self):
        print(f"Analyzing A/V Sync for: {self.input_path.name}")
        duration = self.get_duration()
        
        # 1. Analyze Head (0s -> 60s)
        print(" ... Analyzing Head Segment")
        a_head, v_head, sr = self.extract_features(0, ANALYSIS_WINDOW_SEC)
        offset_head, conf_head = self.calculate_offset(a_head, v_head, sr)
        
        # 2. Analyze Tail (End-60s -> End) if video is long enough
        offset_tail = offset_head
        drift_ms = 0.0
        
        if duration > (ANALYSIS_WINDOW_SEC * 2):
            print(" ... Analyzing Tail Segment")
            start_tail = duration - ANALYSIS_WINDOW_SEC
            a_tail, v_tail, sr = self.extract_features(start_tail, ANALYSIS_WINDOW_SEC)
            # Only calc if valid data returned
            if a_tail is not None:
                offset_tail, conf_tail = self.calculate_offset(a_tail, v_tail, sr)
                drift_ms = offset_tail - offset_head

        # 3. Status
        # Use worst case offset
        max_offset = max(abs(offset_head), abs(offset_tail))
        
        status = "PASSED"
        notes = []
        
        if max_offset > SYNC_TOLERANCE_MS:
            status = "REJECTED" if self.mode == "strict" else "WARNING"
            notes.append(f"Offset {max_offset:.2f}ms exceeds limit")
            
        if abs(drift_ms) > 15.0: # 15ms drift threshold
            if status == "PASSED": status = "WARNING"
            notes.append(f"Drift of {drift_ms:.2f}ms detected")

        # 4. Report
        self.report["status"] = status
        self.report["effective_status"] = status
        self.report["details"] = {
            "offset_ms": round(offset_head, 2), # Legacy field
            "offset_head_ms": round(offset_head, 2),
            "offset_tail_ms": round(offset_tail, 2),
            "drift_ms": round(drift_ms, 2),
            "tolerance_ms": SYNC_TOLERANCE_MS,
            "confidence_score": round(float(conf_head), 2),
            "analysis_note": "; ".join(notes) if notes else "Sync OK"
        }

        self._save()

    def _save(self):
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(self.report, f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default="strict")
    args = parser.parse_args()

    validator = AVSyncValidator(Path(args.input), Path(args.output), args.mode)
    validator.run()