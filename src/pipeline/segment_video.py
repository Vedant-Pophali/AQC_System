import argparse
import json
import subprocess
from pathlib import Path


def get_duration(input_path):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        input_path
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def segment_video(input_path, segment_sec, outdir):
    input_path = Path(input_path).resolve()
    outdir = Path(outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    duration = get_duration(input_path)

    segments = []
    index = 0
    start = 0.0

    while start < duration:
        end = min(start + segment_sec, duration)

        seg_name = f"seg_{index:03d}.mp4"
        seg_path = outdir / seg_name

        cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(start),
            "-i", str(input_path),
            "-t", str(end - start),
            "-c", "copy",
            str(seg_path)
        ]

        subprocess.run(cmd, check=True)

        segments.append({
            "index": index,
            "file": str(seg_path),
            "start_sec": round(start, 3),
            "end_sec": round(end, 3),
            "duration_sec": round(end - start, 3)
        })

        start = end
        index += 1

    manifest = {
        "source": str(input_path),
        "segment_sec": segment_sec,
        "total_duration": round(duration, 3),
        "segments": segments
    }

    with open(outdir / "segments.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)

    print(f"[OK] Created {len(segments)} segments")
    print(f"[OK] Manifest saved: {outdir / 'segments.json'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Temporal video segmentation utility")
    parser.add_argument("--input", required=True)
    parser.add_argument("--segment-sec", type=int, required=True)
    parser.add_argument("--outdir", default="segments")

    args = parser.parse_args()

    segment_video(args.input, args.segment_sec, args.outdir)
