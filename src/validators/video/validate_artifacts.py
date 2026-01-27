import argparse
import json
import subprocess
import os
import logging
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional

# --- Import Core Modules ---
from src.config import threshold_registry
from src.utils.logger import setup_logger

# Initialize Standard Logger
logger = setup_logger("validate_artifacts")

# Lazy import for Scorer to avoid crashing if dependencies are strictly missing during setup
try:
    from src.utils.artifact_scorer import ArtifactScorer
except ImportError:
    ArtifactScorer = None
    logger.warning("Could not import ArtifactScorer. ML features disabled.")

def get_bitrate_metrics(input_path: Path) -> Optional[Dict[str, float]]:
    """
    Calculates Bits-Per-Pixel (BPP) as a heuristic fallback.
    
    Low BPP (< 0.05) strongly suggests compression artifacts regardless of content.
    
    Args:
        input_path (Path): Path to video file.
        
    Returns:
        Optional[Dict]: Dictionary with 'bpp', 'bitrate', 'width', 'height', or None on failure.
    """
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,bit_rate", 
            "-of", "json", str(input_path)
        ]
        # Use full path for subprocess safety
        res = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(res.stdout)
        if not data.get("streams"): return None
        
        stream = data["streams"][0]
        w = int(stream.get("width", 0))
        h = int(stream.get("height", 0))
        br = int(stream.get("bit_rate", 0))
        
        if w > 0 and h > 0:
            pixel_count = w * h
            bpp = br / pixel_count if pixel_count > 0 else 0
            return {"width": w, "height": h, "bitrate": br, "bpp": bpp}
            
    except Exception as e:
        logger.warning(f"Bitrate probe failed: {e}")
    
    return None

def stitch_ml_events(raw_results: List[Dict[str, Any]], min_duration: float = 1.0) -> List[Dict[str, Any]]:
    """
    Aggregates individual bad frames into continuous error events to avoid log spam.
    
    Args:
        raw_results: List of frame scores from ArtifactScorer.
        min_duration: Minimum duration (seconds) to create an event.
        
    Returns:
        List[Dict]: Stitched error events.
    """
    events = []
    if not raw_results:
        return events

    # Filter only non-clean frames
    bad_frames = [r for r in raw_results if r['severity'] != "CLEAN"]
    
    if not bad_frames:
        return events

    # Grouping Logic
    current_event = None
    
    for frame in bad_frames:
        ts = frame['timestamp']
        score = frame['score']
        severity = frame['severity']
        
        # Start new event
        if current_event is None:
            current_event = {
                "type": "compression_artifact_ml",
                "start_time": ts,
                "end_time": ts,
                "severity": severity,
                "scores": [score],
                "details": f"ML detected {severity} artifacts"
            }
            continue
            
        # Check continuity (within 1.5 seconds)
        # We use 1.5s to bridge small gaps if sampling is 1.0s
        if (ts - current_event['end_time']) <= 1.5:
            # Extend current event
            current_event['end_time'] = ts
            current_event['scores'].append(score)
            
            # Upgrade severity if we hit a worse patch
            if severity == "SEVERE" and current_event['severity'] != "SEVERE":
                current_event['severity'] = "SEVERE"
                current_event['details'] = "ML detected SEVERE artifacts"
        else:
            # Close old event and start new one
            events.append(current_event)
            current_event = {
                "type": "compression_artifact_ml",
                "start_time": ts,
                "end_time": ts,
                "severity": severity,
                "scores": [score],
                "details": f"ML detected {severity} artifacts"
            }

    # Append final event
    if current_event:
        events.append(current_event)

    # Post-process: Calculate averages and filter short glitches
    final_events = []
    for evt in events:
        duration = evt['end_time'] - evt['start_time']
        
        # Filter purely isolated spikes unless they are SEVERE
        if duration < min_duration and evt['severity'] != "SEVERE":
            continue
            
        avg_score = sum(evt['scores']) / len(evt['scores'])
        peak_score = max(evt['scores'])
        
        # Clean up internal list
        del evt['scores']
        
        # Add stats to details
        evt['details'] += f" (Avg Score: {avg_score:.1f})"
        
        final_events.append(evt)
        
    return final_events

def run_validator(input_path: str, output_path: str, mode: str = "strict") -> None:
    """
    Main entry point for Artifact Validation Module.
    Combines Heuristic checks (Bitrate) with ML checks (BRISQUE).
    """
    path_obj = Path(input_path)
    report = {
        "module": "validate_artifacts",
        "status": "PASSED",
        "effective_status": "PASSED",
        "metrics": {},
        "events": []
    }
    
    # 1. Load Configuration
    profile = threshold_registry.get_thresholds(mode)
    ml_config = profile.get("ml_artifacts", {})
    
    # 2. Heuristic Check (Bitrate Starvation)
    # Fast pass: if bitrate is extremely low, flag it immediately
    meta = get_bitrate_metrics(path_obj)
    if meta:
        report["metrics"].update(meta)
        if meta["bpp"] < 0.02: # Critical starvation
            report["events"].append({
                "type": "bitrate_starvation",
                "details": f"Critical Bitrate Starvation ({meta['bpp']:.4f} bpp).",
                "severity": "CRITICAL",
                "start_time": 0.0,
                "end_time": 0.0
            })
    
    # 3. ML Analysis (The New Stuff)
    if ml_config.get("enabled", False) and ArtifactScorer:
        logger.info(f"Starting ML Analysis [{mode}]: thresh={ml_config['threshold_score']}")
        
        try:
            scorer = ArtifactScorer()
            raw_results = scorer.analyze_video(
                str(path_obj),
                sample_rate=ml_config.get("sample_rate_fps", 1.0),
                thresholds=ml_config.get("severity_thresholds")
            )
            
            # Record basic metrics
            if raw_results:
                all_scores = [r['score'] for r in raw_results]
                report["metrics"]["ml_model"] = "BRISQUE"
                report["metrics"]["frames_analyzed"] = len(raw_results)
                report["metrics"]["avg_quality_score"] = round(sum(all_scores)/len(all_scores), 2)
                report["metrics"]["worst_score"] = round(max(all_scores), 2)
            
            # Stitch events
            ml_events = stitch_ml_events(
                raw_results, 
                min_duration=ml_config.get("min_duration_sec", 1.0)
            )
            report["events"].extend(ml_events)
            
        except Exception as e:
            logger.error(f"ML Analysis failed: {e}")
            report["events"].append({
                "type": "ml_engine_error",
                "details": f"Artifact detection crashed: {str(e)}",
                "severity": "WARNING"
            })
    else:
        logger.warning("ML Analysis skipped. Check config or dependencies.")

    # 4. Determine Final Status
    severities = [e.get("severity", "INFO") for e in report["events"]]
    
    if "CRITICAL" in severities or "SEVERE" in severities:
        report["status"] = "REJECTED"
        report["effective_status"] = "REJECTED"
    elif "WARNING" in severities or "MODERATE" in severities:
        report["status"] = "WARNING"
        report["effective_status"] = "WARNING"

    # Save Report
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
        
    logger.info(f"Artifact QC Complete. Status: {report['status']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default="strict")
    args = parser.parse_args()
    
    run_validator(args.input, args.output, args.mode)