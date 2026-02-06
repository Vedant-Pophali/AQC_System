import argparse
import subprocess
import json
import logging
from pathlib import Path
import sys

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("remediation_engine")

def run_ffmpeg(cmd, description):
    logger.info(f"Starting {description}: {' '.join(cmd)}")
    try:
        # Run FFmpeg
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.info(f"Successfully completed {description}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed {description}")
        logger.error(f"Error Output: {e.stderr}")
        return False

def fix_loudness(input_path, output_path):
    """
    Apply EBU R128 Loudness Normalization.
    Target: -23 LUFS, True Peak: -1.5 dBTP
    """
    # Two-pass loudnorm is better but one-pass is sufficient for "Quick Fix"
    # filter: loudnorm=I=-23:LRA=7:tp=-1.5
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-af", "loudnorm=I=-23:LRA=7:tp=-1.5",
        "-c:v", "copy", # Don't re-encode video to save quality/time
        "-c:a", "aac", "-b:a", "192k",
        output_path
    ]
    return run_ffmpeg(cmd, "Loudness Normalization")

def fix_transcode(input_path, output_path):
    """
    Re-encode video to remove compression artifacts / fix bitstream.
    Settings: H.264 High Profile, CRF 18 (Visually Lossless), Preset Slow
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-c:a", "copy", # Preserve audio
        output_path
    ]
    return run_ffmpeg(cmd, "High-Quality Transcode")

def main():
    parser = argparse.ArgumentParser(description="AQC Remediation Engine")
    parser.add_argument("--input", required=True, help="Input video file path")
    parser.add_argument("--output", required=True, help="Output fixed video path")
    parser.add_argument("--fix", required=True, choices=["loudness_norm", "transcode_lossless"], help="Type of fix to apply")
    
    args = parser.parse_args()
    
    input_path = str(Path(args.input).resolve())
    output_path = str(Path(args.output).resolve())
    
    success = False
    
    if args.fix == "loudness_norm":
        success = fix_loudness(input_path, output_path)
    elif args.fix == "transcode_lossless":
        success = fix_transcode(input_path, output_path)
        
    if success:
        print(json.dumps({"status": "SUCCESS", "output_file": output_path}))
        sys.exit(0)
    else:
        print(json.dumps({"status": "FAILED", "error": "FFmpeg process failed"}))
        sys.exit(1)

if __name__ == "__main__":
    main()
