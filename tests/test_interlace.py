import pytest
import sys
import os
from unittest.mock import MagicMock, patch
import numpy as np

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.validators.video.validate_interlace import analyze_fields

@pytest.fixture
def mock_cv2():
    with patch('src.validators.video.validate_interlace.cv2') as mock:
        yield mock

def test_interlace_optimization_logic(mock_cv2):
    # Setup Mock VideoCapture
    mock_cap = MagicMock()
    mock_cv2.VideoCapture.return_value = mock_cap
    
    # 25 FPS
    fps = 25.0
    mock_cap.get.return_value = fps
    mock_cap.isOpened.return_value = True
    
    # Simulate 2000 frames (80 seconds)
    # The optimization should stop at 30 seconds * 25 fps = 750 frames
    # And skip every 5th frame (frame_idx % 5 != 0)
    
    total_frames = 2000
    frames_iter = []
    
    for i in range(total_frames):
        # Return True (ret) and a dummy frame
        frames_iter.append((True, np.zeros((100, 100, 3), dtype=np.uint8)))
    
    # After frames run out, return (False, None)
    frames_iter.append((False, None))
    
    mock_cap.read.side_effect = frames_iter
    
    # Default Strict Profile
    profile = {
        "psnr_threshold": 32.0,
        "ssim_threshold": 0.90,
        "temporal_divergence_threshold": 5.0,
        "min_duration_sec": 0.2
    }
    
    events, metrics = analyze_fields("dummy.mp4", profile)
    
    # Assertions
    
    # 1. Verify we didn't process 2000 frames
    # Limit is 30s * 25fps = 750 frames.
    # The loop index increments regardless of processing or skipping.
    # So read count should be roughly 750 + 1 (break condition)
    
    # Let's count calls to read()
    read_count = mock_cap.read.call_count
    print(f"DEBUG: Read count: {read_count}")
    
    # We expect roughly 750 calls because of "if frame_idx > (fps * 30): break"
    # The check is at the END of the loop.
    # Frame 0: Processed
    # Frame 1: Skipped
    # ...
    # Frame 750: Processed/Skipped
    # Frame 751: Loop check breaks
    
    assert read_count <= 752, f"Optimization failed: Read {read_count} frames, expected <= 752 (30s limit)"
    
    # 2. Verify Scanned Frames
    # We expect to scan roughly 1/5th of the frames.
    # But wait, logic is: "if frame_idx % 5 != 0: continue" -> Scans only when % 5 == 0 (0, 5, 10...)
    # So 1 out of 5 frames are processed.
    # Total frames iterated ~750.
    # Processed ~ 750 / 5 = 150.
    
    scanned = metrics["scanned_frames"]
    assert 140 <= scanned <= 160, f"Frame skipping failed: Scanned {scanned} frames, expected ~150"

    print(f"\nOptimization Verified: Read {read_count} frames (limit 750), Scanned {scanned} frames (1/5th sampling).")

if __name__ == "__main__":
    # Manual execution without pytest
    print("Running manual test...")
    try:
        # Mocking cv2 manually since we are not using pytest fixture here
        with patch('src.validators.video.validate_interlace.cv2') as mock_cv2:
            test_interlace_optimization_logic(mock_cv2)
        print("TEST PASSED")
    except Exception as e:
        print(f"TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
