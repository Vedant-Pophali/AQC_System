import cv2
import os
import numpy as np
from typing import List, Dict, Optional, Any
from src.utils.frame_sampler import sample_frames
from src.utils.logger import setup_logger

# Initialize standardized logger
logger = setup_logger(__name__)

class ArtifactScorer:
    """
    ML-based video quality assessment using the BRISQUE algorithm.
    
    Implements No-Reference Image Quality Assessment (NR-IQA) to detect
    compression artifacts, blur, and noise without a reference video.
    
    Attributes:
        _brisque (cv2.quality.QualityBRISQUE): The loaded OpenCV model.
        _initialized (bool): Flag indicating if the model loaded successfully.
    """
    
    _BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _MODEL_DIR = os.path.join(_BASE_DIR, "models", "brisque")
    _MODEL_FILE = os.path.join(_MODEL_DIR, "brisque_model_live.yml")
    _RANGE_FILE = os.path.join(_MODEL_DIR, "brisque_range_live.yml")

    def __init__(self):
        """Initializes the ArtifactScorer and attempts to load model weights."""
        self._brisque = None
        self._initialized = False
        self._load_model()

    def _load_model(self) -> None:
        """
        Loads BRISQUE model files from the local filesystem.
        
        Logs an error if files are missing or the cv2.quality module is unavailable.
        """
        if not (os.path.exists(self._MODEL_FILE) and os.path.exists(self._RANGE_FILE)):
            logger.error(f"BRISQUE model files not found at {self._MODEL_DIR}")
            return

        try:
            if hasattr(cv2, 'quality'):
                self._brisque = cv2.quality.QualityBRISQUE_create(
                    self._MODEL_FILE, 
                    self._RANGE_FILE
                )
                self._initialized = True
                logger.info("BRISQUE model loaded successfully")
            else:
                logger.error("cv2.quality module missing. Install opencv-contrib-python-headless.")
        except Exception as e:
            logger.error(f"Failed to initialize BRISQUE model: {e}")

    def _is_valid_frame(self, frame: np.ndarray) -> bool:
        """
        Validates if a frame is suitable for NSS (Natural Scene Statistics) analysis.
        
        BRISQUE relies on spatial variance. Pure flat colors (black frames) 
        cause divide-by-zero errors or hallucinations in the model.

        Args:
            frame (np.ndarray): The image array (BGR).

        Returns:
            bool: True if frame is valid, False if it should be skipped.
        """
        if frame is None or frame.size == 0:
            return False
            
        h, w = frame.shape[:2]
        if h < 32 or w < 32:
            return False
            
        # Check for solid color (variance ~ 0)
        # We convert to grayscale for a quick check.
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        variance = np.var(gray)
        
        # If variance is near zero, it's a solid color (black, white, blue screen).
        # BRISQUE requires texture to calculate natural scene statistics.
        # Threshold 1.0 is conservative; usually black frames are exactly 0.0
        if variance < 1.0: 
            return False
            
        return True

    def score_frame(self, frame: np.ndarray) -> float:
        """
        Calculates the BRISQUE score for a single video frame.

        Args:
            frame (np.ndarray): The video frame to analyze.

        Returns:
            float: Score from 0.0 (Best) to 100.0 (Worst). Returns -1.0 on failure.
        """
        if not self._initialized:
            return -1.0
            
        try:
            # 1. Safety Check
            if not self._is_valid_frame(frame):
                return -1.0 # Skip invalid frames silently
            
            # 2. Compute Score
            # compute returns a tuple (score, details...), we want index 0
            score_vec = self._brisque.compute(frame)
            score = float(score_vec[0])
            
            # 3. Sanity Check Result
            # OpenCV implementation can sometimes return inf/nan on edge cases
            if np.isinf(score) or np.isnan(score):
                return -1.0
                
            return score
            
        except Exception as e:
            # Log debug only to avoid flooding logs during processing
            logger.debug(f"BRISQUE scoring skipped frame: {e}")
            return -1.0

    def classify_severity(self, score: float, thresholds: Optional[Dict[str, float]] = None) -> str:
        """
        Maps a numeric score to a semantic severity level.

        Args:
            score (float): The BRISQUE score (0-100).
            thresholds (Dict, optional): Custom thresholds. Defaults to standard calibration.

        Returns:
            str: "CLEAN", "MILD", "MODERATE", or "SEVERE".
        """
        if score < 0: return "UNKNOWN"
        
        t = thresholds or {"mild": 40.0, "moderate": 55.0, "severe": 70.0}
        
        if score >= t["severe"]: return "SEVERE"
        elif score >= t["moderate"]: return "MODERATE"
        elif score >= t["mild"]: return "MILD"
        else: return "CLEAN"

    def analyze_video(self, video_path: str, sample_rate: float = 1.0, thresholds: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """
        Performs temporal quality analysis on a video file.

        Args:
            video_path (str): Path to the video file.
            sample_rate (float): Frames to analyze per second of video.
            thresholds (Dict): Severity thresholds configuration.

        Returns:
            List[Dict]: A list of results containing timestamp, score, and severity.
        """
        results = []
        if not self._initialized:
            logger.error("BRISQUE uninitialized. Skipping analysis.")
            return results

        logger.info(f"Starting ML analysis on {os.path.basename(video_path)}")
        
        try:
            # frame_sampler returns iterator of (timestamp, frame)
            samples = sample_frames(video_path, sample_rate_fps=sample_rate)
            
            for timestamp, frame in samples:
                score = self.score_frame(frame)
                
                # Only include valid scores
                if score >= 0:
                    results.append({
                        "timestamp": timestamp,
                        "score": round(score, 2),
                        "severity": self.classify_severity(score, thresholds),
                        "confidence": 1.0
                    })
                    
        except Exception as e:
            logger.error(f"Critical error in video analysis: {e}")
            
        return results

# Self-test mechanism
if __name__ == "__main__":
    import sys
    # Use standard logging for simple CLI test
    logging.basicConfig(level=logging.INFO)
    
    scorer = ArtifactScorer()
    
    # 1. Test Black Frame (Should be ignored/return -1.0)
    print("TEST 1: Black Frame Robustness")
    black_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    s_black = scorer.score_frame(black_frame)
    if s_black == -1.0:
        print("✅ Correctly rejected black frame")
    else:
        print(f"❌ Failed: Scored black frame as {s_black}")

    # 2. Test Noise Frame (Should be scored high)
    print("\nTEST 2: Noise Frame Scoring")
    noise_frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
    s_noise = scorer.score_frame(noise_frame)
    if s_noise > 70:
        print(f"✅ Correctly detected noise/artifacts (Score: {s_noise:.2f})")
    else:
        print(f"❌ Failed: Noise score too low ({s_noise:.2f})")