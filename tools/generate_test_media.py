import subprocess
import argparse
import os
from pathlib import Path

def run_ffmpeg(cmd):
    print(f" [CMD] {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

def generate_test_media(base_video, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(exist_ok=True, parents=True)

    # 1. Clean Reference
    # We assume base_video is a clean 10-20s clip.
    if not base_video:
        print("No base video provided. Generating synthetic reference...")
        ref_path = out_dir / "ref_clean.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=15:size=1280x720:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=15",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            str(ref_path)
        ]
        run_ffmpeg(cmd)
        base_video = ref_path
    else:
        base_video = Path(base_video)

    # 2. Defect: Black Frame / Dropout
    print("\nGenerating: Black Frame Defect...")
    cmd = [
        "ffmpeg", "-y", "-i", str(base_video),
        "-vf", "drawbox=enable='between(t,5,8)':color=black:t=fill",
        "-c:a", "copy",
        str(out_dir / "test_defect_blackframe.mp4")
    ]
    run_ffmpeg(cmd)

    # 3. Defect: Audio Loudness (Too Loud)
    print("\nGenerating: Loudness Defect...")
    cmd = [
        "ffmpeg", "-y", "-i", str(base_video),
        "-af", "volume=10dB",
        "-c:v", "copy",
        str(out_dir / "test_defect_loudness.mp4")
    ]
    run_ffmpeg(cmd)

    # 4. Defect: Audio Phase Cancellation
    # FIX: We map c0 (Input Ch1) to BOTH outputs, but invert the second.
    # pan=stereo|c0=c0|c1=-1*c0  <-- Uses c0 for Right channel too
    print("\nGenerating: Phase Defect...")
    cmd = [
        "ffmpeg", "-y", "-i", str(base_video),
        "-af", "pan=stereo|c0=c0|c1=-1*c0",
        "-c:v", "copy",
        str(out_dir / "test_defect_phase.mp4")
    ]
    run_ffmpeg(cmd)

    # 5. Defect: Freeze Frame
    print("\nGenerating: Freeze Defect...")
    cmd = [
        "ffmpeg", "-y", "-i", str(base_video),
        "-vf", "loop=120:1:150",
        "-c:a", "copy",
        str(out_dir / "test_defect_freeze.mp4")
    ]
    run_ffmpeg(cmd)

    print("\n[DONE] Test media generated in:", out_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", help="Path to a clean reference video (optional)")
    parser.add_argument("--out", default="test_media", help="Output folder")
    args = parser.parse_args()

    generate_test_media(args.base, args.out)