import subprocess
import os
import json
from pathlib import Path
from src.utils.logger import setup_logger

logger = setup_logger("video_segmenter")

class VideoSegmenter:
    """
    Utility to split video files into smaller micro-batches using FFmpeg stream copying.
    This is extremely fast as it avoids re-encoding.
    """
    @staticmethod
    def get_duration(input_path):
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(input_path)
        ]
        try:
            output = subprocess.check_output(cmd).decode("utf-8").strip()
            return float(output)
        except Exception as e:
            logger.error(f"Failed to get duration for {input_path}: {e}")
            return 0

    @staticmethod
    def segment_video(input_path, output_dir, segment_duration_sec=300):
        """
        Splits the video into segments of segment_duration_sec.
        Returns a list of Segment objects (dictionaries).
        """
        input_path = Path(input_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        total_duration = VideoSegmenter.get_duration(input_path)
        if total_duration <= 0:
            return []

        segments = []
        num_segments = int(total_duration // segment_duration_sec) + (1 if total_duration % segment_duration_sec > 0 else 0)

        logger.info(f"Splitting {input_path.name} into {num_segments} segments of ~{segment_duration_sec}s")

        for i in range(num_segments):
            start_time = i * segment_duration_sec
            segment_filename = f"segment_{i:04d}.mp4"
            segment_path = output_dir / segment_filename

            # FFmpeg Command for fast segmenting
            # -ss before -i for fast seeking
            # -t for duration
            # -c copy to avoid re-encoding
            cmd = [
                "ffmpeg", "-y", "-ss", str(start_time), "-t", str(segment_duration_sec),
                "-i", str(input_path), "-c", "copy", "-map", "0",
                "-avoid_negative_ts", "make_zero", str(segment_path)
            ]

            try:
                subprocess.run(cmd, check=True, capture_output=True)
                segments.append({
                    "id": i,
                    "path": str(segment_path),
                    "start_time": start_time,
                    "duration": min(segment_duration_sec, total_duration - start_time)
                })
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to create segment {i}: {e.stderr.decode()}")

        return segments
