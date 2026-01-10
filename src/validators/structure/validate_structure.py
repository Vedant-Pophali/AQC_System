import argparse
import json
import subprocess
import sys
import os
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
        "-count_frames",  # Required for exact frame counting
        str(file_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(result.stdout)
    except Exception as e:
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
        return False, f"Integrity Check Failed: {e.stderr.decode('utf-8')[:200]}"

def analyze_structure(input_path, output_path, mode="strict"):
    input_path = Path(input_path)
    
    report = {
        "module": "structure_qc",
        "video_file": str(input_path),
        "status": "PASSED",
        "metrics": {},
        "events": [],
        "effective_status": "PASSED"
    }

    # 1.1 Media Intake: File Existence
    if not input_path.exists():
        report["status"] = "CRASHED"
        report["events"].append({"type": "file_missing", "details": "File not found."})
        with open(output_path, "w") as f:
            json.dump(report, f, indent=4)
        return

    # 1.1 Media Intake: Corrupt Header / Readability
    probe = get_ffprobe_data(input_path)
    if not probe or "format" not in probe:
        report["status"] = "REJECTED"
        report["events"].append({"type": "corrupt_header", "details": "Could not parse container header."})
        with open(output_path, "w") as f:
            json.dump(report, f, indent=4)
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

    # 1.1 VFR & 1.2 Video Metadata Checks
    is_vfr = False
    if video_streams:
        v_main = video_streams[0]
        r_rate = v_main.get("r_frame_rate", "0/0")
        avg_rate = v_main.get("avg_frame_rate", "0/0")
        
        if r_rate != avg_rate:
            is_vfr = True
            
        report["metrics"].update({
            "video_codec": v_main.get("codec_name"),
            "resolution": f"{v_main.get('width')}x{v_main.get('height')}",
            "frame_rate_mode": "VFR" if is_vfr else "CFR",
            "frame_rate_avg": avg_rate,
            "timebase": v_main.get("time_base")
        })

        # [NEW] 1.2 Video Track Language Tag
        v_lang = v_main.get("tags", {}).get("language", "und")
        if v_lang == "und" and mode == "strict":
            report["events"].append({
                "type": "missing_metadata",
                "details": "Video track missing language tag."
            })

        # 1.2 Aspect Ratio Check
        sar = v_main.get("sample_aspect_ratio", "1:1")
        dar = v_main.get("display_aspect_ratio", "1:1")
        if sar != "1:1" and sar != "0:1":
             report["events"].append({
                "type": "anamorphic_video",
                "details": f"Non-square pixels detected. SAR: {sar}, DAR: {dar}."
            })

    # 1.2 Audio Metadata Checks
    if audio_streams:
        a_main = audio_streams[0]
        layout = a_main.get("channel_layout", "unknown")
        channels = a_main.get("channels", 0)
        
        report["metrics"]["audio_layout"] = layout
        report["metrics"]["audio_channels"] = channels
        
        # 1.2 Channel Layout Validation
        known_layouts = {"stereo": 2, "mono": 1, "5.1": 6, "7.1": 8}
        if layout in known_layouts and known_layouts[layout] != channels:
             report["events"].append({
                "type": "metadata_mismatch",
                "details": f"Audio layout '{layout}' implies {known_layouts[layout]} channels, but found {channels}."
            })

        # 1.2 Audio Language Tag
        a_lang = a_main.get("tags", {}).get("language", "und")
        if a_lang == "und" and mode == "strict":
            report["events"].append({
                "type": "missing_metadata",
                "details": "Audio track missing language tag."
            })

    # 1.2 Timecode Checks
    tc_start = fmt.get("tags", {}).get("timecode")
    if not tc_start and video_streams:
        tc_start = video_streams[0].get("tags", {}).get("timecode")
        
    if not tc_start:
        report["events"].append({
            "type": "missing_timecode", 
            "details": "No embedded Timecode found."
        })
    else:
        report["metrics"]["timecode_start"] = tc_start

    # 1.1 Early EOF / Integrity Check
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

    # Save
    with open(output_path, "w") as f:
        json.dump(report, f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default="strict")
    args = parser.parse_args()
    
    analyze_structure(args.input, args.output, args.mode)test_media