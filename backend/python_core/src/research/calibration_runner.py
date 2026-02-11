import argparse
import json
import subprocess
import os
import time
import sys
import hashlib
from pathlib import Path
from typing import Dict, List, Any
import numpy as np
import cv2

# Ensure src modules can be imported
sys.path.append(str(Path(__file__).parent.parent.parent))

class CalibrationRunner:
    def __init__(self, input_dir: str, output_file: str, mode: str = "full"):
        self.input_dir = Path(input_dir)
        self.output_file = Path(output_file)
        self.mode = mode
        self.results = {
            "metadata": {
                "timestamp": time.time(),
                "mode": mode,
                "input_dir": str(input_dir)
            },
            "files": [],
            "benchmarks": {}
        }

    def _get_files(self) -> List[Path]:
        extensions = {".mp4", ".mov", ".mkv", ".avi", ".mxf"}
        files = []
        for root, _, filenames in os.walk(self.input_dir):
            for f in filenames:
                if Path(f).suffix.lower() in extensions:
                    files.append(Path(root) / f)
        return files

    def run_signalstats(self, file_path: Path) -> Dict[str, Any]:
        """
        Runs signalstats filter to get VREP, YMIN, YMAX, SATMAX.
        """
        cmd = [
            "ffprobe", "-v", "error", "-f", "lavfi",
            f"-i", f"movie={file_path.as_posix().replace(':', '\\:')},signalstats",
            "-show_entries", "frame=pkt_pts_time:frame_tags=YMIN,YMAX,SATMAX,lavfi.signalstats.VREP",
            "-of", "json"
        ]
        
        start_time = time.time()
        try:
            # For micro-batch benchmarking, we might limit frames, but for calibration we need full scan.
            # If mode is 'micro-batch', we limit to first 30 seconds.
            if self.mode == "micro-batch":
                cmd.extend(["-read_intervals", "%+30"])

            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration = time.time() - start_time
            
            data = json.loads(res.stdout)
            frames = data.get("frames", [])
            
            # Process VREP Spikes
            vrep_values = []
            ymin_values = []
            ymax_values = []
            
            for f in frames:
                tags = f.get("tags", {})
                vrep_values.append(float(tags.get("lavfi.signalstats.VREP", 0)))
                ymin_values.append(int(tags.get("YMIN", 16)))
                ymax_values.append(int(tags.get("YMAX", 235)))
                
            # Spike Detection Logic
            # A 'spike' is defined as VREP > 5.0
            # A 'dropout event' is multiple spikes in close succession.
            spikes = [v for v in vrep_values if v > 5.0]
            
            return {
                "status": "success",
                "duration_sec": duration,
                "frames_processed": len(frames),
                "fps": len(frames) / duration if duration > 0 else 0,
                "metrics": {
                    "vrep_max": max(vrep_values) if vrep_values else 0,
                    "vrep_mean": np.mean(vrep_values) if vrep_values else 0,
                    "vrep_spike_count": len(spikes),
                    "ymin_min": min(ymin_values) if ymin_values else 255,
                    "ymax_max": max(ymax_values) if ymax_values else 0
                }
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def run_ssim_interlace_check(self, file_path: Path) -> Dict[str, Any]:
        """
        Runs SSIM-based field divergence check.
        """
        # We need to reuse logic from validate_interlace.py, but since we are researching,
        # we will implement the core collector here to keep it independent.
        cap = cv2.VideoCapture(str(file_path))
        if not cap.isOpened():
            return {"status": "error", "error": "Could not open file"}
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Micro-batch limit
        max_frames = 30 * 25 if self.mode == "micro-batch" else frame_count
        
        psnr_vals = []
        ssim_vals = []
        temp_div_vals = []
        
        prev_odd = None
        
        start_time = time.time()
        read_frames = 0
        
        while read_frames < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
                
            if read_frames % 2 != 0: # Skip every other frame for speed
                read_frames += 1
                continue
                
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            
            even = gray[0::2, :]
            odd = gray[1::2, :]
            min_h = min(even.shape[0], odd.shape[0])
            even = even[:min_h, :]
            odd = odd[:min_h, :]
            
            # PSNR
            diff = even - odd
            rmse = np.sqrt(np.mean(diff**2))
            psnr = 20 * np.log10(255.0 / rmse) if rmse > 0 else 100.0
            psnr_vals.append(psnr)
            
            # SSIM Approx (Mean/Var)
            mu1, mu2 = np.mean(even), np.mean(odd)
            var1, var2 = np.var(even), np.var(odd)
            covar = np.mean((even - mu1) * (odd - mu2))
            c1, c2 = 6.5025, 58.5225
            ssim = ((2*mu1*mu2 + c1)*(2*covar + c2)) / ((mu1**2 + mu2**2 + c1)*(var1 + var2 + c2))
            ssim_vals.append(ssim)
            
            # Temp Div
            if prev_odd is not None:
                temp_div = np.mean(np.abs(odd - prev_odd))
                temp_div_vals.append(temp_div)
            prev_odd = odd.copy()
            
            read_frames += 1
            
        cap.release()
        duration = time.time() - start_time
        
        return {
            "status": "success",
            "duration_sec": duration,
            "fps": read_frames / duration if duration > 0 else 0,
            "metrics": {
                "avg_psnr": np.mean(psnr_vals) if psnr_vals else 0,
                "min_psnr": np.min(psnr_vals) if psnr_vals else 0,
                "avg_ssim": np.mean(ssim_vals) if ssim_vals else 0,
                "min_ssim": np.min(ssim_vals) if ssim_vals else 0,
                "avg_temp_div": np.mean(temp_div_vals) if temp_div_vals else 0
            }
        }

    def run_cropdetect(self, file_path: Path) -> Dict[str, Any]:
        """
        Runs cropdetect to find active area.
        """
        # Run on a few intervals: Start, Middle, End
        # We'll use start for now as per simple calibration
        cmd = [
            "ffmpeg", "-hide_banner", "-ss", "10", "-i", str(file_path),
            "-vf", "cropdetect=24:16:0", "-frames:v", "10", "-f", "null", "-"
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            # Parse stderr for crop=w:h:x:y
            # We look for the most frequent crop or the last one
            import re
            matches = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", res.stderr)
            if matches:
                last = matches[-1]
                return {
                    "status": "success",
                    "w": int(last[0]),
                    "h": int(last[1]),
                    "x": int(last[2]),
                    "y": int(last[3])
                }
            return {"status": "no_crop_detected"}
        except Exception as e:
             return {"status": "error", "error": str(e)}

    def execute(self):
        files = self._get_files()
        print(f"Found {len(files)} files to process in {self.input_dir}")
        
        for f in files:
            print(f"Processing {f.name}...")
            file_data = {
                "filename": f.name, 
                "path": str(f),
                "signals": {},
                "interlace": {},
                "geometry": {}
            }
            
            # 1. Signal Stats (VREP)
            print("  - Running SignalStats...")
            file_data["signals"] = self.run_signalstats(f)
            
            # 2. Interlace (SSIM)
            print("  - Running Interlace/SSIM analysis...")
            file_data["interlace"] = self.run_ssim_interlace_check(f)
            
            # 3. Geometry
            print("  - Running CropDetect...")
            file_data["geometry"] = self.run_cropdetect(f)
            
            self.results["files"].append(file_data)
            
        # Write Output
        with open(self.output_file, "w") as f:
            json.dump(self.results, f, indent=4)
        print(f"Calibration completed. Report saved to {self.output_file}")


def generate_mock_data(output_file: str):
    """
    Generates mock calibration data for testing/development.
    """
    print("Generating MOCK calibration data...")
    data = {
        "metadata": {"mode": "mock"},
        "files": []
    }
    
    # scenario 1: Clean file
    data["files"].append({
        "filename": "clean_progressive.mp4",
        "signals": {"status": "success", "metrics": {"vrep_max": 2.0, "vrep_spike_count": 0, "ymin_min": 16, "ymax_max": 235}},
        "interlace": {"status": "success", "metrics": {"avg_psnr": 45.0, "avg_ssim": 0.98, "avg_temp_div": 2.0}},
        "geometry": {"status": "success", "w": 1920, "h": 1080}
    })
    
    # scenario 2: Analog Dropout
    data["files"].append({
        "filename": "tape_glitch.mov",
        "signals": {"status": "success", "metrics": {"vrep_max": 55.0, "vrep_spike_count": 12, "ymin_min": 5, "ymax_max": 240}},
        "interlace": {"status": "success", "metrics": {"avg_psnr": 40.0, "avg_ssim": 0.95, "avg_temp_div": 1.5}},
        "geometry": {"status": "success", "w": 720, "h": 486}
    })
    
    # scenario 3: Interlaced Combing
    data["files"].append({
        "filename": "interlaced_content.mxf",
        "signals": {"status": "success", "metrics": {"vrep_max": 3.0, "vrep_spike_count": 0}},
        "interlace": {"status": "success", "metrics": {"avg_psnr": 28.0, "avg_ssim": 0.85, "avg_temp_div": 15.0}},
        "geometry": {"status": "success", "w": 1920, "h": 1080}
    })

    with open(output_file, "w") as f:
        json.dump(data, f, indent=4)
    print(f"Mock data saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=False, help="Input directory of samples")
    parser.add_argument("--output", required=True, help="Output JSON report")
    parser.add_argument("--mode", default="full", choices=["full", "micro-batch", "mock"])
    parser.add_argument("--gpu", action="store_true", help="Enable hardware acceleration")
    args = parser.parse_args()
    
    if args.mode == "mock":
        generate_mock_data(args.output)
    else:
        if not args.input:
            print("Error: --input required unless mode is mock")
            sys.exit(1)
        runner = CalibrationRunner(args.input, args.output, args.mode)
        # In a real impl, we would pass args.gpu to the runner
        # runner.use_gpu = args.gpu 
        runner.execute()
