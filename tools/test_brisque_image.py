#!/usr/bin/env python3
"""
Standalone BRISQUE Image Quality Tester
=======================================
Analyzes a single image for compression artifacts using OpenCV's implementation
of the BRISQUE (Blind/Referenceless Image Spatial Quality Evaluator) algorithm.

Usage:
    python tools/test_brisque_image.py --image path/to/image.jpg
"""

import argparse
import cv2
import os
import sys
import requests
import numpy as np

# Configuration for Model Files
# We store models in a persistent location so we don't download them every time
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "models", "brisque")
MODEL_URL_BASE = "https://raw.githubusercontent.com/opencv/opencv_contrib/master/modules/quality/samples"
MODEL_FILE = "brisque_model_live.yml"
RANGE_FILE = "brisque_range_live.yml"

def ensure_models_exist():
    """
    Checks if BRISQUE model files exist locally. Downloads them if missing.
    Returns tuple of (model_path, range_path).
    """
    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR)
        print(f"📂 Created model directory: {MODEL_DIR}")

    paths = {}
    for filename in [MODEL_FILE, RANGE_FILE]:
        filepath = os.path.join(MODEL_DIR, filename)
        paths[filename] = filepath
        
        if not os.path.exists(filepath):
            url = f"{MODEL_URL_BASE}/{filename}"
            print(f"⬇️  Downloading {filename}...")
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                with open(filepath, 'wb') as f:
                    f.write(response.content)
            except Exception as e:
                print(f"❌ Error downloading {filename}: {e}")
                sys.exit(1)
                
    return paths[MODEL_FILE], paths[RANGE_FILE]

def classify_severity(score):
    """
    Maps BRISQUE score to severity level based on calibrated ranges.
    Score 0 (Best) -> 100 (Worst)
    """
    if score < 30:
        return "CLEAN", "Excellent quality"
    elif score < 50:
        return "MILD", "Minor compression artifacts"
    elif score < 70:
        return "MODERATE", "Visible artifacts detected"
    else:
        return "SEVERE", "Heavy compression / distortion"

def main():
    parser = argparse.ArgumentParser(description="Calculate BRISQUE score for an image.")
    parser.add_argument("--image", required=True, help="Path to input image file")
    args = parser.parse_args()

    # 1. Validation & Setup
    if not os.path.exists(args.image):
        print(f"❌ Error: Image file not found at {args.image}")
        sys.exit(1)

    # Check for OpenCV Quality module
    if not hasattr(cv2, 'quality'):
        print("❌ Error: cv2.quality module missing.")
        print("   Run: pip install opencv-contrib-python-headless")
        sys.exit(1)

    # Ensure model files are ready
    print("🔄 Initializing BRISQUE models...")
    model_path, range_path = ensure_models_exist()

    # 2. Load Image
    try:
        img = cv2.imread(args.image)
        if img is None:
            print(f"❌ Error: Failed to load image. Is it a valid image file?")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading image: {e}")
        sys.exit(1)

    # 3. Calculate Score
    try:
        # Initialize BRISQUE algorithm
        brisque = cv2.quality.QualityBRISQUE_create(model_path, range_path)
        
        # Compute returns a scalar (vector), we need the first element
        # cv2.quality.compute returns cv::Scalar, in Python it's a tuple or list
        score_result = brisque.compute(img)
        score = score_result[0]
        
    except Exception as e:
        print(f"❌ Error during BRISQUE calculation: {e}")
        sys.exit(1)

    # 4. Display Results
    severity, assessment = classify_severity(score)
    
    print("-" * 40)
    print(f"📸 Image:      {os.path.basename(args.image)}")
    print(f"📊 Score:      {score:.2f} (0-100)")
    print(f"🏷️  Severity:   {severity}")
    print(f"📝 Assessment: {assessment}")
    print("-" * 40)

if __name__ == "__main__":
    main()