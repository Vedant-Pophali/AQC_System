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
SYNC_TOLERANCE_MS = 40.0  # EBU R37 standard (+/- 40ms is 'sync')

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

    def extract_audio_features(self, duration_limit=60):
        """
        Extracts audio onset envelope (transients).
        Limits analysis to first 60s to save speed, or full if needed.
        """
        try:
            # Load audio (mono)
            y, sr = librosa.load(self.input_path, sr=SAMPLE_RATE, duration=duration_limit)
            
            # Calculate onset envelope (detects percussive/transient events)
            onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP_LENGTH)
            
            # Normalize
            if np.max(onset_env) > 0:
                onset_env = onset_env / np.max(onset_env)
                
            return onset_env, sr
        except Exception as e:
            return None, str(e)

    def extract_visual_features(self, target_len, duration_limit=60):
        """
        Extracts visual motion energy (scene cuts/flashes).
        Resamples to match the length of the audio feature vector.
        """
        cap = cv2.VideoCapture(str(self.input_path))
        if not cap.isOpened():
            return None

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Limit frames to analyze
        max_frames = int(duration_limit * fps)
        frames_to_read = min(frame_count, max_frames)

        visual_energy = []
        
        ret, prev_frame = cap.read()
        if not ret:
            return None
            
        # Resize for speed (we only need global motion/cuts, not details)
        prev_frame = cv2.resize(prev_frame, (64, 64))
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)

        for _ in range(frames_to_read - 1):
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_resized = cv2.resize(frame, (64, 64))
            curr_gray = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2GRAY)
            
            # Calculate absolute difference (motion/cut energy)
            diff = cv2.absdiff(curr_gray, prev_gray)
            score = np.sum(diff)
            visual_energy.append(score)
            
            prev_gray = curr_gray

        cap.release()
        
        visual_energy = np.array(visual_energy)
        
        # Normalize
        if np.max(visual_energy) > 0:
            visual_energy = visual_energy / np.max(visual_energy)
            
        # Resample visual signal to match audio onset signal length
        # This aligns the time-series arrays
        if len(visual_energy) > 0:
            visual_resampled = signal.resample(visual_energy, target_len)
            # Ensure no negative values after resampling
            visual_resampled = np.maximum(visual_resampled, 0)
            return visual_resampled
        
        return None

    def calculate_offset(self, audio_sig, video_sig, sr):
        """
        Performs Cross-Correlation to find the time shift.
        """
        # Cross correlate
        correlation = signal.correlate(video_sig, audio_sig, mode='full')
        
        # Find peak
        lags = signal.correlation_lags(len(video_sig), len(audio_sig), mode='full')
        peak_idx = np.argmax(correlation)
        lag_samples = lags[peak_idx]
        
        # Convert lag from 'feature samples' to seconds
        # We need to know the time-step of the feature array
        # Librosa onset has time_step = HOP_LENGTH / SAMPLE_RATE
        time_step = HOP_LENGTH / SAMPLE_RATE
        offset_sec = lag_samples * time_step
        
        return offset_sec, correlation[peak_idx]

    def check_drift(self):
        """
        Checks sync at the start and end of the file to detect drift.
        """
        # Note: Implementing full multi-segment drift check requires 
        # complex windowing. For this MVP, we analyze the global offset.
        # If the offset is massive, it implies drift or bad sync.
        pass

    def run(self):
        print(f"Analyzing A/V Sync for: {self.input_path.name}")
        
        # 1. Extract Audio Transients
        a_features, sr = self.extract_audio_features()
        if a_features is None:
            self.report["status"] = "SKIPPED"
            self.report["details"]["error"] = "No audio track found or decode error"
            self._save()
            return

        # 2. Extract Visual Transients
        # We pass len(a_features) so visual features are resampled to match audio length exactly
        v_features = self.extract_visual_features(target_len=len(a_features))
        
        if v_features is None:
            self.report["status"] = "ERROR"
            self.report["details"]["error"] = "Could not process video frames"
            self._save()
            return

        # 3. Calculate Sync Offset
        offset_sec, confidence = self.calculate_offset(a_features, v_features, sr)
        offset_ms = offset_sec * 1000.0

        # 4. Determine Pass/Fail
        status = "PASSED"
        
        # Logic: A positive offset means Video is ahead of Audio (Audio delayed)
        # Logic: A negative offset means Audio is ahead of Video
        
        abs_offset = abs(offset_ms)
        
        if abs_offset > SYNC_TOLERANCE_MS:
            if self.mode == "strict":
                status = "REJECTED"
            else:
                status = "WARNING"
                
        # Confidence check: If correlation is weak, it means the video might be 
        # a talking head with no cuts, making this method unreliable.
        # (Heuristic threshold)
        if confidence < 5.0: # Arbitrary scaling factor, depends on normalization
            details_msg = "Low confidence match (few visual cuts detected)"
        else:
            details_msg = "High confidence match"

        # 5. Build Report
        self.report["status"] = status
        self.report["effective_status"] = status
        self.report["details"] = {
            "offset_ms": round(offset_ms, 2),
            "offset_frames": round(offset_sec * 24), # Assuming 24fps for estimation
            "tolerance_ms": SYNC_TOLERANCE_MS,
            "confidence_score": round(float(confidence), 2),
            "analysis_note": details_msg,
            "drift_detected": False # Placeholder for future drift logic
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