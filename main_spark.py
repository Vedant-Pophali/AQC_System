import argparse
import os
import sys
import json
import time
from pathlib import Path
from pyspark.sql import SparkSession

from src.utils.video_segmenter import VideoSegmenter
from src.utils.spark_worker import analyze_segment
from src.postprocess.master_aggregator import MasterAggregator
from src.utils.logger import setup_logger
from src.config import threshold_registry

logger = setup_logger("aqc_spark")

VALIDATORS = [
    ("structure", "validate_structure"),
    ("video", "validate_frames"),
    ("video", "validate_analog"),
    ("video", "validate_black_freeze"),
    ("video", "validate_interlace"),
    ("video", "validate_artifacts"),
    ("video", "validate_geometry"),
    ("audio", "validate_loudness"),
    ("audio", "validate_audio_signal"),
    ("audio", "validate_phase"),
    ("video", "validate_avsync"),
]

# 1. Setup Spark Environment
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

def main():
    parser = argparse.ArgumentParser(description="AQC Distributed Spark Pipeline")
    parser.add_argument("--input", required=True, help="Path to input video file")
    parser.add_argument("--outdir", required=True, help="Base directory to save reports")
    parser.add_argument("--mode", default="strict", help="QC Profile")
    parser.add_argument("--segments", type=int, default=60, help="Segment duration in seconds")
    
    args = parser.parse_args()
    input_video = Path(args.input).resolve()
    base_outdir = Path(args.outdir).resolve()
    
    # 1. Setup Spark
    logger.info("Initializing Spark Session...")
    spark = SparkSession.builder \
        .appName("SpectraAQC-Distributed") \
        .master("local[*]") \
        .config("spark.python.worker.timeout", "600") \
        .config("spark.task.maxFailures", "4") \
        .config("spark.python.worker.faulthandler.enabled", "true") \
        .getOrCreate()
    
    # 2. Segment Video
    job_dir = base_outdir / f"{input_video.stem}_spark_qc"
    segments_dir = job_dir / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Segmenting video: {input_video.name}")
    segments = VideoSegmenter.segment_video(input_video, segments_dir, args.segments)
    
    if not segments:
        logger.error("Segmentation failed or video is empty.")
        spark.stop()
        return

    # 3. Create RDD and Map
    logger.info(f"Dispatching {len(segments)} segments to Spark cluster...")
    segments_rdd = spark.sparkContext.parallelize(segments, len(segments))
    
    # Closure-friendly variables
    validators = VALIDATORS
    mode = args.mode
    
    start_time = time.time()
    results = segments_rdd.map(lambda s: analyze_segment(s, validators, mode)).collect()
    total_duration = time.time() - start_time
    
    logger.info(f"Analysis completed in {total_duration:.2f} seconds.")

    # 4. Aggregate Results
    logger.info("Aggregating results...")
    aggregator = MasterAggregator(results, mode)
    master_report = aggregator.aggregate()
    
    # Add Governance Info
    gov_info = threshold_registry.get_governance_info(mode)
    master_report["governance"] = gov_info
    
    master_path = job_dir / "Master_Report.json"
    aggregator.save(master_path)
    
    # 5. Generate Dashboard (using existing visualizer)
    dashboard_path = job_dir / "dashboard.html"
    try:
        from src.visualization import visualize_report
        # We need to run it as a module or call it directly
        # Since we are already in the environment, we can import and call
        import subprocess
        subprocess.run([
            sys.executable, "-m", "src.visualization.visualize_report",
            "--input", str(master_path), "--output", str(dashboard_path)
        ])
        logger.info(f" [OK] Dashboard: {dashboard_path.name}")
    except Exception as e:
        logger.error(f"Failed to generate dashboard: {e}")

    logger.info(f"QC Job Finished. Results in: {job_dir}")
    spark.stop()

if __name__ == "__main__":
    main()
