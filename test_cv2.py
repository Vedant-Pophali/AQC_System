import sys
print(f"Python: {sys.version}")
try:
    import cv2
    print(f"OpenCV: {cv2.__version__}")
    if hasattr(cv2, 'quality'):
        print("cv2.quality available")
    else:
        print("cv2.quality MISSING")
except Exception as e:
    print(f"Import Failed: {e}")
    sys.exit(1)
