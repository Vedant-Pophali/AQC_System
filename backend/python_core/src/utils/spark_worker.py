import os
import sys
import subprocess
import json
from pathlib import Path

def analyze_segment(segment_data, validators, profile_mode):
    """
    Function to be executed by Spark workers for a specific video segment.
    """
    segment_path = Path(segment_data['path'])
    segment_id = segment_data['id']
    start_time = segment_data['start_time']
    
    # Create a temporary directory for segment reports
    report_dir = segment_path.parent / f"segment_{segment_id}_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    segment_results = {
        "segment_id": segment_id,
        "start_time": start_time,
        "duration": segment_data['duration'],
        "reports": []
    }
    
    # Run validators on the segment
    for category, module in validators:
        report_path = report_dir / f"report_{module}.json"
        module_path = f"src.validators.{category}.{module}"
        
        # Determine the python executable (absolute path to avoid issues on workers)
        python_exe = sys.executable
        
        cmd = [
            python_exe, "-m", module_path,
            "--input", str(segment_path),
            "--output", str(report_path),
            "--mode", profile_mode
        ]
        
        try:
            # We use a shorter timeout for segments
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            if report_path.exists():
                with open(report_path, "r", encoding="utf-8") as f:
                    report_data = json.load(f)
                    segment_results["reports"].append(report_data)
        except Exception as e:
            # Create a crash report for this module in this segment
            crash_report = {
                "module": module,
                "status": "CRASHED",
                "segment_id": segment_id,
                "error": str(e)
            }
            segment_results["reports"].append(crash_report)
            
    return segment_results
