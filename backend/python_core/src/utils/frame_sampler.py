import cv2
import os
import numpy as np
import logging
from typing import List, Tuple, Optional
from tqdm import tqdm

# Configure logger
logger = logging.getLogger(__name__)

def sample_frames(video_path: str, sample_rate_fps: float = 1.0) -> List[Tuple[float, np.ndarray]]:
    """
    Extract frames from video at a specified sampling rate.
    
    Optimized for performance by skipping frames rather than decoding everything.
    
    Args:
        video_path: Path to the input video file.
        sample_rate_fps: Number of frames to extract per second of video.
                         Default is 1.0 (one frame every second).
                         
    Returns:
        List of tuples: (timestamp_in_seconds, frame_bgr_array)
        
    Raises:
        FileNotFoundError: If video_path does not exist.
        ValueError: If video cannot be opened.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Failed to open video: {video_path}")

    frames_data = []
    
    try:
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        if fps <= 0 or total_frames <= 0:
            logger.warning(f"Could not determine valid FPS or frame count for {video_path}")
            # Fallback: try to read normally without seeking optimizations
            fps = 24.0 # Assumption
            
        # Calculate step size (how many frames to skip)
        # If sample_rate is 1.0 and video is 30fps, we need every 30th frame.
        step = int(max(1, round(fps / sample_rate_fps)))
        
        logger.info(f"Sampling video: {os.path.basename(video_path)}")
        logger.info(f"Duration: {duration:.2f}s, Native FPS: {fps:.2f}, Sampling Step: {step} frames")

        # Initialize progress bar
        pbar = tqdm(total=int(total_frames / step), desc="Extracting frames", unit="frame")
        
        current_frame_idx = 0
        while cap.isOpened():
            # Efficient Seeking:
            # Instead of reading every frame, we calculate the next frame index
            target_frame_idx = current_frame_idx
            
            # Set the position
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_idx)
            
            ret, frame = cap.read()
            if not ret:
                break
                
            # Calculate timestamp
            timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            
            # Validation: Ensure frame is valid
            if frame is not None and frame.size > 0:
                frames_data.append((timestamp, frame))
            
            # Update progress
            pbar.update(1)
            
            # Move to next target
            current_frame_idx += step
            
            # Safety break for end of stream
            if current_frame_idx >= total_frames:
                break

        pbar.close()
        
    except Exception as e:
        logger.error(f"Error during frame sampling: {e}")
        raise
    finally:
        cap.release()

    logger.info(f"Extracted {len(frames_data)} frames from {video_path}")
    
    if len(frames_data) == 0:
        logger.warning("No frames were extracted. Check if video content is valid.")

    return frames_data

# Simple self-test if run directly
if __name__ == "__main__":
    # Create a dummy video file for testing if one doesn't exist
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python src/utils/frame_sampler.py <path_to_video>")
        sys.exit(1)
        
    vpath = sys.argv[1]
    logging.basicConfig(level=logging.INFO)
    
    try:
        samples = sample_frames(vpath, sample_rate_fps=0.5) # 1 frame every 2 seconds
        print(f"✅ Success: Retrieved {len(samples)} frames.")
        if len(samples) > 0:
            print(f"   First frame timestamp: {samples[0][0]:.2f}s")
            print(f"   Last frame timestamp:  {samples[-1][0]:.2f}s")
            print(f"   Frame shape: {samples[0][1].shape}")
    except Exception as e:
        print(f"❌ Failed: {e}")