# ===================================
# QC THRESHOLD REGISTRY
# ===================================
# This file is the SINGLE SOURCE OF TRUTH
# for all numeric and policy thresholds.
#
# - No logic
# - No imports
# - No side effects
# - Read-only by validators
# ===================================


# -----------------------------------
# DEFAULT PROFILE
# -----------------------------------
DEFAULT_PROFILE = "strict"


# -----------------------------------
# PROFILES
# -----------------------------------
PROFILES = {

    # ===================================
    # STRICT / BROADCAST PROFILE
    # ===================================
    "strict": {

        # -------- AUDIO --------
        "loudness": {
            "target_lufs": -23.0,
            "lufs_tolerance": 2.0,
            "true_peak_max": -1.0,
            "lra_max": 7.0
        },

        "audio_signal": {
            "max_dc_offset": 0.01,
            "max_clipping_ratio": 0.001
        },

        # -------- VIDEO SIGNAL --------
        "signal": {
            "luma_min": 16,
            "luma_max": 235,
            "chroma_min": 16,
            "chroma_max": 240
        },

        # -------- BLACK / FREEZE --------
        "black_freeze": {
            "black_pixel_threshold": 0.02,
            "min_black_duration_sec": 0.1,
            "min_freeze_duration_sec": 0.1,
            "max_total_black_ratio": 0.05,
            "max_total_freeze_ratio": 0.05
        },

        # -------- FRAME INTEGRITY --------
        "frames": {
            "max_duplicate_frames": 1,
            "max_dropped_frames": 1,
            "pts_gap_sec": 0.5
        },

        # -------- GOP STRUCTURE --------
        "gop": {
            "max_gop_length": 250,
            "require_idr": True
        },

        # -------- INTERLACE --------
        "interlace": {
            "max_interlaced_ratio": 0.0
        },

        # -------- TIMESTAMPS --------
        "timestamps": {
            "allow_non_monotonic": False
        },

        # -------- AV SYNC --------
        "avsync": {
            "max_offset_sec": 0.04,
            "method": "median"
        },

        # -------- ARTIFACTS --------
        "artifacts": {
            "blockiness_threshold": 0.3,
            "ringing_threshold": 0.3
        },

        # -------- QCTOOLS --------
        "qctools": {
            "allow_missing": False
        }
    },

    # ===================================
    # OTT / STREAMING PROFILE
    # ===================================
    "ott": {

        # -------- AUDIO --------
        "loudness": {
            "target_lufs": -16.0,
            "lufs_tolerance": 2.0,
            "true_peak_max": -1.0,
            "lra_max": 11.0
        },

        "audio_signal": {
            "max_dc_offset": 0.02,
            "max_clipping_ratio": 0.005
        },

        # -------- VIDEO SIGNAL --------
        "signal": {
            "luma_min": 16,
            "luma_max": 235,
            "chroma_min": 16,
            "chroma_max": 240
        },

        # -------- BLACK / FREEZE --------
        "black_freeze": {
            "black_pixel_threshold": 0.03,
            "min_black_duration_sec": 0.2,
            "min_freeze_duration_sec": 0.2,
            "max_total_black_ratio": 0.1,
            "max_total_freeze_ratio": 0.1
        },

        # -------- FRAME INTEGRITY --------
        "frames": {
            "max_duplicate_frames": 3,
            "max_dropped_frames": 3,
            "pts_gap_sec": 1.0
        },

        # -------- GOP STRUCTURE --------
        "gop": {
            "max_gop_length": 300,
            "require_idr": False
        },

        # -------- INTERLACE --------
        "interlace": {
            "max_interlaced_ratio": 0.05
        },

        # -------- TIMESTAMPS --------
        "timestamps": {
            "allow_non_monotonic": False
        },

        # -------- AV SYNC --------
        "avsync": {
            "max_offset_sec": 0.08,
            "method": "median"
        },

        # -------- ARTIFACTS --------
        "artifacts": {
            "blockiness_threshold": 0.5,
            "ringing_threshold": 0.5
        },

        # -------- QCTOOLS --------
        "qctools": {
            "allow_missing": True
        }
    }
}

