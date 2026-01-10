# Registry of QC Thresholds / Boundary Conditions
# Reference: Research Section 7 (Source 203-205)

DEFAULT_PROFILE = "strict"

PROFILES = {
    "strict": {
        "description": "Broadcast/OTT delivery standards (Netflix/Hulu spec)",

        "structure": {
            "expected_container": "mp4",
            "min_audio_channels": 2,
            "sample_rate": "48000",
            "display_aspect_ratio": 1.778  # 16:9
        },

        "visual_qc": {
            # Black Frame: >98% black pixels, <0.03 brightness, >2.0s duration
            "black_pixel_coverage": 0.98,
            "black_frame_threshold": 0.03,
            "min_black_duration": 2.0
        },

        "freeze_qc": {
            "noise_tolerance": -60, # dB
            "min_freeze_duration": 2.0 # seconds
        },

        "audio_signal": {
            "max_dc_offset": 0.005,
            "max_clipping_ratio": 0.0, # Zero tolerance for clipping
            "min_phase_correlation": -0.8 # Avoid phase cancellation
        },

        "loudness": {
            "target_lufs": -23.0,
            "lufs_tolerance": 2.0, # +/- 2 LU
            "true_peak_max": -1.0, # dBTP
            "lra_max": 20.0
        },

        "interlace": {
            "max_interlaced_ratio": 0.0, # Progressive only
            "min_field_psnr": 30.0 # High PSNR = Progressive
        },

        "artifacts": {
            "blockiness_threshold": 0.05, # Heuristic ratio
            "ringing_threshold": 0.02,
            "sample_interval_sec": 1.0,
            "min_artifact_duration_sec": 0.5
        },

        "avsync": {
            "max_offset_sec": 0.040, # +/- 40ms (1 frame at 25fps)
            "method": "median"
        }
    },

    "ott": {
        "description": "Relaxed Web/Social standards",
        # Inherits structure but relaxes strictness
        "structure": {
            "expected_container": "mp4",
            "min_audio_channels": 2,
            "sample_rate": "44100", # Allow 44.1k
            "display_aspect_ratio": 1.778
        },
        "visual_qc": {
            "black_pixel_coverage": 0.95,
            "black_frame_threshold": 0.05,
            "min_black_duration": 3.0
        },
        "freeze_qc": {
            "noise_tolerance": -50,
            "min_freeze_duration": 3.0
        },
        "audio_signal": {
            "max_dc_offset": 0.01,
            "max_clipping_ratio": 0.001,
            "min_phase_correlation": -0.9
        },
        "loudness": {
            "target_lufs": -16.0, # Web standard often -16
            "lufs_tolerance": 3.0,
            "true_peak_max": -1.0,
            "lra_max": 25.0
        },
        "interlace": {
            "max_interlaced_ratio": 0.05,
            "min_field_psnr": 25.0
        },
        "artifacts": {
            "blockiness_threshold": 0.10,
            "ringing_threshold": 0.05,
            "sample_interval_sec": 2.0,
            "min_artifact_duration_sec": 1.0
        },
        "avsync": {
            "max_offset_sec": 0.100, # 100ms
            "method": "median"
        }
    }
}