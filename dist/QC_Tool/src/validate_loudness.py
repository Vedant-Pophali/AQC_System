import subprocess
import json
import sys
import os
import argparse
import shutil

# --- LOAD CONFIGURATION ---
def load_audio_config():
    # Looks for qc_config.json in the Project Root (one level up from src)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "qc_config.json")

    defaults = {"target_lufs": -23.0, "lufs_tolerance": 2.0, "true_peak_max": -1.0}

    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                data = json.load(f)
                return data.get("audio_qc", defaults)
        except Exception as e:
            return defaults
    return defaults

AUDIO_CONFIG = load_audio_config()

def get_ffmpeg_loudness(video_path):
    if not shutil.which("ffmpeg"):
        return {"error": "FFmpeg binary not found. Please install FFmpeg."}

    cmd = [
        "ffmpeg", "-i", video_path, "-map", "0:a:0", "-vn",
        "-af", f"loudnorm=I={AUDIO_CONFIG['target_lufs']}:print_format=json",
        "-f", "null", "-"
    ]

    try:
        result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True, encoding='utf-8', errors='replace')
        output = result.stderr

        # Robust JSON extraction
        try:
            json_start = output.rfind('{')
            json_end = output.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found")
            json_str = output[json_start:json_end]
            return json.loads(json_str)
        except:
            return {"error": "Could not parse FFmpeg output. Audio track might be missing."}
    except Exception as e:
        return {"error": str(e)}

def analyze_compliance(video_path, output_path):
    raw_data = get_ffmpeg_loudness(video_path)
    events = []

    if "error" in raw_data:
        status = "ERROR"
        error_msg = raw_data['error']
    else:
        try:
            input_i = float(raw_data.get("input_i", -99.0))
            target = AUDIO_CONFIG["target_lufs"]
            tol = AUDIO_CONFIG["lufs_tolerance"]

            if (target - tol) <= input_i <= (target + tol):
                status = "PASSED"
            else:
                status = "REJECTED"
                events.append({
                    "type": "loudness_violation",
                    "start_time": 0.0,
                    "end_time": 0.0,
                    "confidence": 1.0,
                    "details": {
                        "measured_lufs": input_i,
                        "target_lufs": target,
                        "diff": round(input_i - target, 2)
                    }
                })
        except:
            status = "ERROR"
            error_msg = "Invalid data format"

    report = {
        "module": "audio_qc",
        "video_file": video_path,
        "status": status,
        "events": events
    }
    if status == "ERROR":
        report["error_details"] = error_msg if 'error_msg' in locals() else "Unknown error"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    analyze_compliance(args.input, args.output)