import argparse
import subprocess
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path for internal imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from src.config import threshold_registry

def validate_audio_phase(input_video, output_report, mode="strict"):
    """
    Detects audio phase correlation issues using the FFmpeg aphasemeter filter.
    Measures the correlation between left and right channels (-1 to 1).
    """
    thresholds = threshold_registry.get_thresholds(mode)
    min_correlation = thresholds.get("audio", {}).get("min_phase_correlation", 0.0)

    # FFmpeg command to extract phase metadata per frame
    # We use ffprobe to read the lavfi metadata
    # On Windows, we need to escape the path for amovie
    escaped_path = str(input_video).replace("\\", "/").replace(":", "\\:")
    
    cmd = [
        "ffprobe", "-v", "quiet",
        "-f", "lavfi",
        "-i", f"amovie='{escaped_path}',aphasemeter=video=0",
        "-show_entries", "frame_tags=lavfi.aphasemeter.phase",
        "-of", "json"
    ]

    report = {
        "module": "validate_phase",
        "status": "PASSED",
        "effective_status": "PASSED",
        "details": {
            "mean_phase_correlation": 0.0,
            "min_phase_correlation": 1.0,
            "out_of_phase_segments": []
        }
    }

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        frames = data.get("frames", [])
        if not frames:
            report["status"] = "WARNING"
            report["effective_status"] = "WARNING"
            report["details"]["error"] = "No audio phase data extracted. Possibly mono source?"
            with open(output_report, "w") as f:
                json.dump(report, f, indent=4)
            return

        phases = []
        for frame in frames:
            phase_str = frame.get("tags", {}).get("lavfi.aphasemeter.phase")
            if phase_str is not None:
                phases.append(float(phase_str))

        if phases:
            mean_phase = sum(phases) / len(phases)
            min_phase = min(phases)
            
            report["details"]["mean_phase_correlation"] = round(mean_phase, 4)
            report["details"]["min_phase_correlation"] = round(min_phase, 4)

            # Compliance Logic
            if mean_phase < min_correlation:
                report["status"] = "REJECTED"
                report["effective_status"] = "REJECTED"
                report["details"]["issue"] = f"Mean phase correlation ({report['details']['mean_phase_correlation']}) is below threshold ({min_correlation})."
            elif min_phase < -0.5:
                # Moments of extreme phase inversion
                report["status"] = "WARNING"
                report["effective_status"] = "WARNING"
                report["details"]["issue"] = "Moments of extreme phase inversion detected."

    except Exception as e:
        report["status"] = "CRASHED"
        report["effective_status"] = "CRASHED"
        report["details"]["error"] = str(e)

    with open(output_report, "w") as f:
        json.dump(report, f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default="strict")
    args = parser.parse_args()

    validate_audio_phase(Path(args.input), Path(args.output), args.mode)
