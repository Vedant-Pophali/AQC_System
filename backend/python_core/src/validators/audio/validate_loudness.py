import argparse
import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# --- Internal Imports ---
from src.config import threshold_registry
from src.utils.logger import setup_logger

# Initialize Standard Logger
logger = setup_logger("validate_loudness")

def check_loudness(file_path: Path, target_lufs: float = -23.0, true_peak_max: float = -1.0, tolerance: float = 1.0) -> Dict[str, Any]:
    """
    Analyzes audio loudness using FFmpeg's ebur128 filter (ITU-R BS.1770).
    
    Args:
        file_path (Path): Path to the media file.
        target_lufs (float): Target Integrated Loudness (e.g., -23.0).
        true_peak_max (float): Maximum permitted True Peak (dBTP).
        tolerance (float): Allowed deviation (+/-) from target LUFS.

    Returns:
        Dict: Metrics (integrated_lufs, true_peak, lra) and status.
    """
    metrics = {
        "integrated_lufs": -99.0, # Default invalid value
        "true_peak": -99.0,
        "lra": 0.0,
        "status": "PASSED",
        "events": []
    }

    # FFmpeg command to run the EBU R.128 filter
    # We output to null and capture stderr where the stats are printed
    cmd = [
        "ffmpeg", "-nostats",
        "-i", str(file_path),
        "-filter_complex", "ebur128=peak=true",
        "-f", "null", "-"
    ]

    try:
        logger.info(f"Running EBU R.128 analysis on: {file_path.name}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stderr

        # Parse FFmpeg Output
        # Look for the summary block at the end
        # Example output lines:
        #   I:         -23.1 LUFS
        #   LRA:         5.2 LU
        #   True peak:  -1.5 dBTP
        
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("I:") and "LUFS" in line:
                val = line.split("I:")[1].split("LUFS")[0].strip()
                metrics["integrated_lufs"] = float(val)
            elif line.startswith("LRA:") and "LU" in line:
                val = line.split("LRA:")[1].split("LU")[0].strip()
                metrics["lra"] = float(val)
            elif line.startswith("True peak:") and "dBTP" in line:
                # Handle multi-channel peak lines (e.g. "-1.2 -1.5 dBTP")
                parts = line.split("True peak:")[1].split("dBTP")[0].strip().split()
                try:
                    # Filter valid float strings and take max
                    peaks = []
                    for p in parts:
                        try:
                            peaks.append(float(p))
                        except ValueError:
                            continue
                    if peaks:
                        metrics["true_peak"] = max(peaks)
                except Exception:
                    pass

        # Logic Check
        lufs = metrics["integrated_lufs"]
        peak = metrics["true_peak"]

        if lufs == -99.0:
            metrics["status"] = "WARNING"
            metrics["events"].append({
                "type": "missing_audio",
                "details": "Audio analysis returned no data (Possible silent track or no audio stream).",
                "severity": "medium"
            })
        else:
            # Check Integrated Loudness
            if not (target_lufs - tolerance <= lufs <= target_lufs + tolerance):
                metrics["status"] = "REJECTED"
                metrics["events"].append({
                    "type": "loudness_violation",
                    "details": f"Integrated Loudness {lufs} LUFS is outside target {target_lufs} +/- {tolerance}.",
                    "severity": "high"
                })

            # Check True Peak
            if peak > true_peak_max:
                metrics["status"] = "REJECTED"
                metrics["events"].append({
                    "type": "true_peak_violation",
                    "details": f"True Peak {peak} dBTP exceeds limit {true_peak_max} dBTP.",
                    "severity": "high"
                })

    except Exception as e:
        logger.error(f"Loudness analysis failed: {e}")
        metrics["status"] = "ERROR"
        metrics["error"] = str(e)

    return metrics

def run_validator(input_path: str, output_path: str, mode: str = "strict") -> None:
    """
    Main execution point for the module.
    
    Args:
        input_path (str): Path to input video.
        output_path (str): Path to save JSON report.
        mode (str): QC Profile (strict, netflix_hd, etc.)
    """
    input_path_obj = Path(input_path)
    
    # Load thresholds from configuration
    thresholds = threshold_registry.get_thresholds(mode)
    audio_cfg = thresholds.get("audio", {})
    
    target = audio_cfg.get("integrated_loudness_target", -23.0)
    peak = audio_cfg.get("true_peak_max", -1.0)
    tol = audio_cfg.get("loudness_tolerance", 1.0)

    # Run Check
    result = check_loudness(input_path_obj, target, peak, tol)

    # Format Report
    report = {
        "module": "validate_loudness",
        "status": result["status"],
        "details": {
            "metrics": {
                "integrated_lufs": result["integrated_lufs"],
                "lra": result["lra"],
                "true_peak": result["true_peak"]
            },
            "events": result["events"]
        }
    }
    
    # Calculate effective status (PASSED/WARNING/REJECTED)
    if result["status"] == "REJECTED":
        report["effective_status"] = "REJECTED"
    else:
        report["effective_status"] = "PASSED"

    # Save
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
    
    logger.info(f"Loudness Check Complete. Status: {report['status']} (I: {result['integrated_lufs']} LUFS)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default="strict")
    args = parser.parse_args()
    run_validator(args.input, args.output, args.mode)