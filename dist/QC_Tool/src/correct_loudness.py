import subprocess
import json
import argparse
import os
import sys

def correct_loudness(input_path, report_path, config_path):
    print(f"[INFO] Healer: Checking if audio needs correction...")

    # 1. Check the Audio Report
    # We only run if the Audio QC module said "REJECTED"
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            audio_data = json.load(f)
            status = audio_data.get("status", "UNKNOWN")
    except Exception as e:
        print(f"[WARN] Could not read audio report: {e}")
        return

    if status != "REJECTED":
        print("[INFO] Audio is valid. No correction needed.")
        return

    # 2. Prepare Output Path (e.g., video_corrected.mp4)
    dirname, filename = os.path.split(input_path)
    name, ext = os.path.splitext(filename)
    output_filename = f"{name}_corrected{ext}"
    output_path = os.path.join(dirname, output_filename)

    print(f"[ACTION] Fixing Loudness for: {filename}")
    print(f"         Target: EBU R.128 (-23 LUFS)")
    print(f"         Output: {output_filename}")

    # 3. The "Magic" FFmpeg Command (Loudnorm)
    # This filter measures and adjusts audio in one go to hit -23 LUFS
    cmd = [
        "ffmpeg",
        "-y",                   # Overwrite output
        "-v", "error",          # Quiet mode
        "-i", input_path,       # Input file
        "-af", "loudnorm=I=-23:LRA=7:TP=-2.0", # The Normalization Filter
        "-c:v", "copy",         # Don't touch the video (faster)
        "-c:a", "aac",          # Re-encode audio to apply changes
        "-b:a", "192k",         # Good bitrate
        output_path
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"[SUCCESS] Corrected file created: {output_path}")

        # 4. Update the Report to say we fixed it
        # We re-open the file in Read/Write mode
        with open(report_path, 'r+', encoding='utf-8') as f:
            data = json.load(f)
            data["correction"] = {
                "status": "FIXED",
                "new_file": output_path,
                "note": "Loudness normalized to -23 LUFS via EBU R.128 filter."
            }
            # Go back to start of file to overwrite
            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Correction failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    correct_loudness(args.input, args.report, args.config)