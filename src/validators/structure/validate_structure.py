import argparse
import json
import subprocess
from pathlib import Path

def get_ffprobe_data(file_path):
    """
    Extracts deep metadata using ffprobe JSON output.
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        "-show_error",
        "-count_frames",
        str(file_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(result.stdout)
    except Exception:
        return None

def check_eof_integrity(file_path):
    """
    1.1 Early EOF Detection
    Attempts to decode the stream logic to ensure it's not truncated.
    """
    try:
        cmd = [
            "ffmpeg",
            "-v", "error",
            "-i", str(file_path),
            "-f", "null",
            "-"
        ]
        # Quick scan of container structure
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        return True, "File structure is valid."
    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.decode('utf-8')[:200] if e.stderr else "Unknown Error"
        return False, f"Integrity Check Failed: {err_msg}"

def analyze_structure(input_path, output_path, mode="strict"):
    input_path = Path(input_path)
    
    report = {
        "module": "validate_structure",
        "status": "PASSED",
        "metrics": {},
        "events": [],
        "effective_status": "PASSED"
    }

    # 1. File Existence
    if not input_path.exists():
        report["status"] = "CRASHED"
        report["events"].append({"type": "file_missing", "details": "File not found."})
        _save(output_path, report)
        return

    # 2. Corrupt Header Check
    probe = get_ffprobe_data(input_path)
    if not probe or "format" not in probe:
        report["status"] = "REJECTED"
        report["events"].append({"type": "corrupt_header", "details": "Could not parse container header."})
        _save(output_path, report)
        return

    # --- METRICS EXTRACTION ---
    fmt = probe["format"]
    streams = probe.get("streams", [])
    
    video_streams = [s for s in streams if s["codec_type"] == "video"]
    audio_streams = [s for s in streams if s["codec_type"] == "audio"]
    sub_streams = [s for s in streams if s["codec_type"] == "subtitle"]

    report["metrics"] = {
        "container": fmt.get("format_name"),
        "duration_sec": float(fmt.get("duration", 0)),
        "bitrate_bps": int(fmt.get("bit_rate", 0)),
        "track_count_video": len(video_streams),
        "track_count_audio": len(audio_streams),
        "track_count_subs": len(sub_streams),
    }

    # 3. Video Metadata Checks
    if video_streams:
        v_main = video_streams[0]
        
        # Duration Consistency (Container vs Stream)
        fmt_dur = float(fmt.get("duration", 0))
        strm_dur = float(v_main.get("duration", 0))
        if fmt_dur > 0 and strm_dur > 0:
            if abs(fmt_dur - strm_dur) > 0.5: # 500ms tolerance
                report["events"].append({
                    "type": "metadata_mismatch",
                    "details": f"Container duration ({fmt_dur}s) mismatches stream ({strm_dur}s)."
                })

        # Language Tag
        v_lang = v_main.get("tags", {}).get("language", "und")
        if v_lang == "und" and mode == "strict":
            report["events"].append({
                "type": "missing_metadata",
                "details": "Video track missing language tag."
            })

    # 4. Audio Metadata Checks
    if audio_streams:
        a_main = audio_streams[0]
        a_lang = a_main.get("tags", {}).get("language", "und")
        if a_lang == "und" and mode == "strict":
            report["events"].append({
                "type": "missing_metadata",
                "details": "Audio track missing language tag."
            })

    # 5. Integrity Check (Deep Scan)
    valid_integrity, msg = check_eof_integrity(input_path)
    if not valid_integrity:
        report["status"] = "REJECTED"
        report["events"].append({
            "type": "integrity_failure",
            "details": msg
        })

    # Final Status Logic
    if any(e["type"] in ["integrity_failure", "corrupt_header"] for e in report["events"]):
        report["effective_status"] = "REJECTED"
    elif any(e["type"] == "metadata_mismatch" for e in report["events"]):
        report["effective_status"] = "WARNING"
    else:
        report["effective_status"] = "PASSED"

    _save(output_path, report)

def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default="strict")
    args = parser.parse_args()
    analyze_structure(args.input, args.output, args.mode)