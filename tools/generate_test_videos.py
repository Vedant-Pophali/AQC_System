#!/usr/bin/env python3
"""
Test Dataset Generator for AQC System
=====================================
Generates compressed video versions with known quality levels using FFmpeg.
Used to calibrate BRISQUE thresholds for different quality tiers.

Input: Source video file (ideally high quality, > 3 minutes long)
Output: 
  - test_data/videos/: 3 re-encoded video versions (High, Medium, Low)
  - test_data/frames/: Sample frames extracted from each version

Usage:
    python tools/generate_test_videos.py --input path/to/source.mp4
"""

import argparse
import os
import subprocess
import sys
import shutil

# Configuration
OUTPUT_BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_data")
VIDEO_DIR = os.path.join(OUTPUT_BASE, "videos")
FRAME_DIR = os.path.join(OUTPUT_BASE, "frames")

# FFmpeg Quality Presets (from Task 3 specifications)
QUALITY_PROFILES = {
    "HIGH": {
        "bitrate": "8M",
        "preset": "slow",
        "desc": "High Quality (8 Mbps)"
    },
    "MEDIUM": {
        "bitrate": "2M",
        "preset": "fast",
        "desc": "Medium Quality (2 Mbps)"
    },
    "LOW": {
        "bitrate": "500K",
        "preset": "ultrafast",
        "desc": "Low Quality (500 Kbps)"
    }
}

# Extraction timestamps (in seconds)
# We sample multiple points to get a good distribution
SAMPLE_TIMESTAMPS = [30, 60, 90, 120, 150]

def check_ffmpeg():
    """Verify FFmpeg is installed and accessible."""
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: FFmpeg not found in PATH. Please install FFmpeg.")
        sys.exit(1)

def ensure_directories():
    """Create necessary output directories."""
    for d in [VIDEO_DIR, FRAME_DIR]:
        if not os.path.exists(d):
            os.makedirs(d)
            print(f"📂 Created directory: {d}")

def get_video_duration(filepath):
    """
    Get video duration in seconds using ffprobe.
    Returns float duration or None if failed.
    """
    try:
        cmd = [
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            filepath
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return float(result.stdout.strip())
    except Exception:
        return None

def generate_video(source_path, quality_name, profile):
    """Re-encode video with specific settings."""
    output_filename = f"{quality_name.lower()}_quality.mp4"
    output_path = os.path.join(VIDEO_DIR, output_filename)
    
    print(f"\n🎬 Generating {quality_name} version ({profile['desc']})...")
    
    cmd = [
        "ffmpeg",
        "-y",               # Overwrite output
        "-i", source_path,
        "-c:v", "libx264",
        "-b:v", profile['bitrate'],
        "-preset", profile['preset'],
        output_path
    ]
    
    try:
        # Run ffmpeg (capture output to avoid clutter unless error)
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"   ✅ Saved to: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"   ❌ FFmpeg encoding failed: {e.stderr.decode()}")
        return None

def extract_frames(video_path, quality_name, duration):
    """Extract sample frames at specific timestamps."""
    print(f"   🖼️  Extracting frames for {quality_name}...")
    
    valid_timestamps = [t for t in SAMPLE_TIMESTAMPS if t < duration]
    
    if not valid_timestamps:
        print(f"      ⚠️ Video too short ({duration:.1f}s) for standard timestamps.")
        # Fallback: take one frame from the middle
        valid_timestamps = [duration / 2]
    
    count = 0
    for timestamp in valid_timestamps:
        output_filename = f"{quality_name.lower()}_frame_{int(timestamp)}s.jpg"
        output_path = os.path.join(FRAME_DIR, output_filename)
        
        cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(timestamp),
            "-i", video_path,
            "-frames:v", "1",
            "-q:v", "2",  # High quality jpeg extraction
            output_path
        ]
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            count += 1
        except subprocess.CalledProcessError:
            print(f"      ⚠️ Failed to extract frame at {timestamp}s")

    print(f"      ✅ Extracted {count} frames")

def main():
    parser = argparse.ArgumentParser(description="Generate compressed video dataset for AQC calibration.")
    parser.add_argument("--input", required=True, help="Path to source high-quality video")
    args = parser.parse_args()

    # 1. Checks
    if not os.path.exists(args.input):
        print(f"❌ Error: Source file not found: {args.input}")
        sys.exit(1)
        
    check_ffmpeg()
    ensure_directories()
    
    # 2. Analyze Source
    duration = get_video_duration(args.input)
    if duration:
        print(f"⏱️  Source Duration: {duration:.2f} seconds")
    else:
        print("⚠️  Could not determine duration, frame extraction might be partial.")
        duration = 999999 # Assume long enough if probe fails

    # 3. Process Loops
    for q_name, q_profile in QUALITY_PROFILES.items():
        generated_video = generate_video(args.input, q_name, q_profile)
        
        if generated_video:
            extract_frames(generated_video, q_name, duration)

    print("\n✅ Dataset Generation Complete!")
    print(f"   Videos: {VIDEO_DIR}")
    print(f"   Frames: {FRAME_DIR}")

if __name__ == "__main__":
    main()