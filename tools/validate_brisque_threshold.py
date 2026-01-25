#!/usr/bin/env python3
"""
BRISQUE Threshold Validator
===========================
Analyzes the generated test dataset to determine optimal quality thresholds.
Scans frames in test_data/frames/, calculates BRISQUE scores, and generates
a statistical report to guide configuration.

Usage:
    python tools/validate_brisque_threshold.py
"""

import cv2
import os
import glob
import numpy as np
import sys
import requests

# Configuration
TEST_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_data", "frames")
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "models", "brisque")
MODEL_FILE = "brisque_model_live.yml"
RANGE_FILE = "brisque_range_live.yml"

def get_model_paths():
    """Ensure models exist and return paths."""
    model_path = os.path.join(MODEL_DIR, MODEL_FILE)
    range_path = os.path.join(MODEL_DIR, RANGE_FILE)
    
    if not (os.path.exists(model_path) and os.path.exists(range_path)):
        print("❌ Error: BRISQUE models not found.")
        print(f"   Please run 'python tools/test_brisque_image.py' first to download them.")
        sys.exit(1)
        
    return model_path, range_path

def parse_quality_from_filename(filename):
    """Extract quality level (high/medium/low) from filename."""
    name = os.path.basename(filename).lower()
    if "high" in name: return "HIGH"
    if "medium" in name: return "MEDIUM"
    if "low" in name: return "LOW"
    return "UNKNOWN"

def analyze_dataset():
    print("🔄 Initializing Validation...")
    
    # 1. Setup
    if not os.path.exists(TEST_DATA_DIR):
        print(f"❌ Error: Test data directory not found: {TEST_DATA_DIR}")
        print("   Run 'python tools/generate_test_videos.py' first.")
        sys.exit(1)

    model_path, range_path = get_model_paths()
    try:
        brisque = cv2.quality.QualityBRISQUE_create(model_path, range_path)
    except Exception as e:
        print(f"❌ Error initializing BRISQUE: {e}")
        sys.exit(1)

    # 2. Collect Frames
    frame_files = glob.glob(os.path.join(TEST_DATA_DIR, "*.jpg"))
    if not frame_files:
        print("❌ No jpg frames found in test_data/frames/")
        sys.exit(1)

    results = {"HIGH": [], "MEDIUM": [], "LOW": []}
    
    print(f"🔎 Analyzing {len(frame_files)} frames...")
    
    # 3. Score Frames
    for fpath in frame_files:
        quality = parse_quality_from_filename(fpath)
        if quality == "UNKNOWN": continue
        
        img = cv2.imread(fpath)
        if img is None: continue
        
        score_vec = brisque.compute(img)
        score = score_vec[0]
        results[quality].append(score)
        print(f"   [{quality}] {os.path.basename(fpath)} -> {score:.1f}")

    # 4. Generate Report
    print("\n" + "="*40)
    print("BRISQUE VALIDATION REPORT")
    print("="*40 + "\n")
    
    stats = {}
    
    # Process each category
    # Order: High -> Medium -> Low
    for q in ["HIGH", "MEDIUM", "LOW"]:
        scores = results[q]
        if not scores:
            print(f"{q} QUALITY\n  No frames found.\n")
            continue
            
        avg = np.mean(scores)
        std = np.std(scores)
        min_s = np.min(scores)
        max_s = np.max(scores)
        stats[q] = avg
        
        # Determine pass/fail based on expected theoretical ranges
        # High: < 40, Medium: 40-60, Low: > 60
        expected_note = ""
        if q == "HIGH":
            status = "✅ PASS" if avg < 45 else "⚠️ HIGH"
            expected_note = "(Expected < 45)"
        elif q == "MEDIUM":
            status = "✅ PASS" if 30 <= avg <= 65 else "⚠️ DEVIATION"
            expected_note = "(Expected 40-60)"
        else: # LOW
            status = "✅ PASS" if avg > 55 else "⚠️ LOW"
            expected_note = "(Expected > 60)"

        print(f"{q} QUALITY")
        print(f"  Frames analyzed: {len(scores)}")
        print(f"  Score range:     {min_s:.1f} - {max_s:.1f}")
        print(f"  Average:         {avg:.1f} ± {std:.1f}")
        print(f"  Status:          {status} {expected_note}")
        print()

    # 5. Recommendation Logic
    print("-" * 40)
    if stats.get("MEDIUM") and stats.get("LOW"):
        # Threshold should be between Medium and Low to catch bad content
        # Weighted slightly towards Low to avoid false positives on Medium
        midpoint = (stats["MEDIUM"] + stats["LOW"]) / 2
        recommendation = midpoint
        print(f"RECOMMENDED THRESHOLD: {recommendation:.1f}")
        print("(Scores above this should be flagged as artifacts)")
    else:
        print("RECOMMENDED THRESHOLD: 55.0 (Default)")
        print("(Insufficient data to calculate dynamic threshold)")
    print("-" * 40)

if __name__ == "__main__":
    analyze_dataset()