import subprocess
import json
import argparse
import os
import re

def check_interlace(input_path, output_path):
    print(f"[INFO] Interlace QC: Analyzing fields in {os.path.basename(input_path)}...")

    # We use the 'idet' filter to count Progressive vs Interlaced frames
    cmd = [
        "ffmpeg",
        "-v", "info",       # We need INFO to see the stats
        "-i", input_path,
        "-vf", "idet",      # The Interlace Detect Filter
        "-frames:v", "1000",# Analyze first 1000 frames (Speed optimization)
        "-f", "null",
        "-"
    ]

    report = {
        "module": "interlace_qc",
        "video_file": input_path,
        "status": "PASSED",
        "metrics": {},
        "events": []
    }

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        logs = result.stderr

        # Parse FFmpeg's idet output:
        # "Multi frame detection: TFF: 0 BFF: 0 Progressive: 352 Undetermined: 0"
        match = re.search(r"Multi frame detection: TFF:\s*(\d+)\s+BFF:\s*(\d+)\s+Progressive:\s*(\d+)", logs)

        if match:
            tff = int(match.group(1)) # Top Field First
            bff = int(match.group(2)) # Bottom Field First
            prog = int(match.group(3)) # Progressive
            total = tff + bff + prog

            # Avoid division by zero
            if total > 0:
                interlaced_count = tff + bff
                interlaced_ratio = interlaced_count / total

                report["metrics"] = {
                    "progressive_frames": prog,
                    "interlaced_frames": interlaced_count,
                    "total_analyzed": total,
                    "interlace_ratio": round(interlaced_ratio, 4)
                }

                # CRITERIA: If > 10% of frames are Interlaced, FAIL the video.
                # Modern web/app video should be 100% Progressive.
                if interlaced_ratio > 0.10:
                    report["status"] = "REJECTED"
                    report["events"].append({
                        "type": "Interlacing Artifacts",
                        "details": f"Video is {round(interlaced_ratio*100, 1)}% Interlaced. Should be Progressive."
                    })
        else:
            print("[WARN] Could not parse 'idet' output.")

    except Exception as e:
        print(f"[ERROR] Interlace QC Failed: {e}")
        report["status"] = "ERROR"
        report["events"].append({"error": str(e)})

    # Save Report
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding='utf-8') as f:
        json.dump(report, f, indent=4)
    print(f"[OK] Saved: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    check_interlace(args.input, args.output)