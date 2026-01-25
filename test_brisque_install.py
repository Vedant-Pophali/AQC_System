# Test if OpenCV BRISQUE is working
import sys
import os
import requests
import cv2
import numpy as np

def download_file(url, filename):
    """Download model files if they don't exist."""
    if os.path.exists(filename):
        print(f"   Using existing {filename}")
        return
    
    print(f"   Downloading {filename}...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(filename, 'wb') as f:
            f.write(response.content)
    except Exception as e:
        print(f"❌ Failed to download {filename}: {e}")
        sys.exit(1)

def test_brisque():
    print("Checking OpenCV Quality module...")
    
    # 1. Check if cv2.quality exists
    try:
        # Check for the quality module (available in opencv-contrib)
        # We don't import cv2.quality directly, we access it via cv2.quality
        if not hasattr(cv2, 'quality'):
             raise ImportError("cv2.quality module not found. Did you install opencv-contrib-python?")
        print("✅ OpenCV Quality module found")
    except Exception as e:
        print(f"❌ OpenCV Quality check failed: {e}")
        print("Tip: Uninstall 'opencv-python' and install 'opencv-contrib-python-headless'")
        sys.exit(1)

    # 2. Download Model Files (Required for BRISQUE)
    # These are the standard trained models from the original paper/OpenCV repo
    print("\nChecking BRISQUE model files...")
    base_url = "https://raw.githubusercontent.com/opencv/opencv_contrib/master/modules/quality/samples"
    model_file = "brisque_model_live.yml"
    range_file = "brisque_range_live.yml"
    
    download_file(f"{base_url}/{model_file}", model_file)
    download_file(f"{base_url}/{range_file}", range_file)
    print("✅ Model files ready")

    # 3. Functional Test
    print("\nRunning functional test...")
    try:
        # Create a test image (random noise = high score/bad quality)
        img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        # Initialize BRISQUE
        # Note: generic compute() returns a scalar (Scalar element 0 is the score)
        obj = cv2.quality.QualityBRISQUE_create(model_file, range_file)
        score_scalar = obj.compute(img)
        score = score_scalar[0]
        
        print(f"✅ BRISQUE scoring works")
        print(f"   Test Score: {score:.2f} (0=Best, 100=Worst)")
        print(f"   Implementation: OpenCV Native (C++)")
        
        # Cleanup
        if os.path.exists(model_file): os.remove(model_file)
        if os.path.exists(range_file): os.remove(range_file)
        print("   (Cleaned up temporary model files)")
        
    except Exception as e:
        print(f"❌ BRISQUE functional test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_brisque()