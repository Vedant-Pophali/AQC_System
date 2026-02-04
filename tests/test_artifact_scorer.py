import pytest
import numpy as np
import os
import sys

# Ensure we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.artifact_scorer import ArtifactScorer

class TestArtifactScorer:
    """
    Unit tests for the Machine Learning Artifact Detection logic.
    """
    
    @classmethod
    def setup_class(cls):
        """Initialize the scorer once for all tests."""
        cls.scorer = ArtifactScorer()

    def test_model_initialization(self):
        """Verify the BRISQUE model loads without crashing."""
        assert self.scorer._initialized is True, "BRISQUE model failed to initialize"

    def test_black_frame_rejection(self):
        """
        Verify that a pure black frame is REJECTED (returns -1.0).
        Black frames have 0 variance, which causes divide-by-zero in NSS models.
        """
        # Create a 720p black frame
        black_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        
        score = self.scorer.score_frame(black_frame)
        assert score == -1.0, f"Black frame should return -1.0, got {score}"

    def test_noise_frame_detection(self):
        """
        Verify that a frame full of random noise gets a HIGH score (Bad Quality).
        """
        # Create a frame of random noise
        np.random.seed(42) # Fixed seed for reproducibility
        noise_frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
        
        score = self.scorer.score_frame(noise_frame)
        
        # Noise usually scores > 80 on BRISQUE scale (0-100)
        assert score > 60.0, f"Noise frame should score > 60, got {score}"

    def test_severity_classification(self):
        """Verify the score-to-text mapping logic."""
        # Test Default Thresholds
        assert self.scorer.classify_severity(10.0) == "CLEAN"
        assert self.scorer.classify_severity(45.0) == "MILD"
        assert self.scorer.classify_severity(60.0) == "MODERATE"
        assert self.scorer.classify_severity(85.0) == "SEVERE"
        assert self.scorer.classify_severity(-1.0) == "UNKNOWN"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])