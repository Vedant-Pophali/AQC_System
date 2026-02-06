import unittest
import json
import sys
import os
import numpy as np
from pathlib import Path

# Mock modules if not running in full environment
sys.path.append(str(Path(__file__).parent.parent))

from src.validators.video import validate_interlace, validate_analog, validate_geometry
from src.validators.archival import validate_signal

class TestCalibrationLogic(unittest.TestCase):

    def test_ssim_calculation(self):
        # Create identical images
        img1 = np.ones((100, 100), dtype=np.uint8) * 128
        img2 = np.ones((100, 100), dtype=np.uint8) * 128
        ssim = validate_interlace.calculate_ssim_approx(img1, img2)
        self.assertAlmostEqual(ssim, 1.0, places=4)
        
        # Different images
        img3 = np.zeros((100, 100), dtype=np.uint8)
        ssim2 = validate_interlace.calculate_ssim_approx(img1, img3)
        self.assertTrue(ssim2 < 0.1)

    def test_confidence_score(self):
        # Limit 235
        # 235 -> 0.0
        c1 = validate_signal.calculate_confidence(235, 235, True)
        self.assertEqual(c1, 0.0)
        
        # 245 -> 10 over -> 0.5 -> 50.0
        c2 = validate_signal.calculate_confidence(245, 235, True) * 100.0
        self.assertEqual(c2, 50.0)
        
        # 255 -> 20 over -> 1.0 -> 100.0
        c3 = validate_signal.calculate_confidence(255, 235, True) * 100.0
        self.assertEqual(c3, 100.0)
        
    def test_interlace_profile_load(self):
        profile = validate_interlace.load_profile("strict")
        self.assertEqual(profile["psnr_threshold"], 32.0)
        
        profile_nf = validate_interlace.load_profile("netflix")
        self.assertEqual(profile_nf["psnr_threshold"], 30.0)

    def test_analog_profile_load(self):
        profile = validate_analog.load_profile("youtube")
        # YouTube uses signal profile mapping which defaulted analog logic uses?
        # Actually validate_analog loads 'validate_signal' profile from config
        self.assertEqual(profile["vrep_threshold"], 10.0)
        
    def test_geometry_profile_load(self):
        profile = validate_geometry.load_profile("STRICT")
        self.assertEqual(profile["blanking_tolerance_pct"], 0.5)

if __name__ == '__main__':
    unittest.main()
