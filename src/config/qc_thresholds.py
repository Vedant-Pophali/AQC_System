"""
Central QC threshold registry.

Design goals:
- No validator hardcodes limits
- Strict vs OTT separation
- Calibration-ready (data-driven later)
- Backward compatible with current pipeline
"""

# -----------------------------------
# SUPPORTED QC MODES
# -----------------------------------
QC_MODES = {"strict", "ott"}


# -----------------------------------
# DEFAULT POLICY THRESHOLDS
# (Used when no calibration data exists)
# -----------------------------------
DEFAULT_THRESHOLDS = {
    "strict": {
        # A/V Sync
        "avsync_warn_ms": 40,
        "avsync_fail_ms": 100,

        # GOP
        "gop_max_sec": 2.0,

        # Frame timing
        "frame_drop_multiplier": 2.5,

        # Black / Freeze (minimum meaningful duration)
        "black_min_sec": 0.30,
        "freeze_min_sec": 0.40,
    },
    "ott": {
        # A/V Sync
        "avsync_warn_ms": 80,
        "avsync_fail_ms": 200,

        # GOP
        "gop_max_sec": 4.0,

        # Frame timing
        "frame_drop_multiplier": 3.5,

        # Black / Freeze
        "black_min_sec": 0.50,
        "freeze_min_sec": 0.60,
    }
}


# -----------------------------------
# CALIBRATION REGISTRY (v1: EMPTY)
# -----------------------------------
# This will later be populated from:
# - historical QC runs
# - content class (news/sports/animation)
# - percentile analysis (P95 / P99)
#
# Example future shape:
#
# CALIBRATED_THRESHOLDS = {
#     "strict": {
#         "avsync_fail_ms": 92,
#         "gop_max_sec": 1.8
#     }
# }
#
CALIBRATED_THRESHOLDS = {}


# -----------------------------------
# PUBLIC API
# -----------------------------------
def get_thresholds(mode: str) -> dict:
    """
    Returns effective thresholds for a mode.
    Calibration overrides defaults when present.
    """

    if mode not in QC_MODES:
        raise ValueError(f"Unsupported QC mode: {mode}")

    # Start with defaults
    effective = dict(DEFAULT_THRESHOLDS[mode])

    # Overlay calibrated values (if any)
    calibrated = CALIBRATED_THRESHOLDS.get(mode, {})
    effective.update(calibrated)

    return effective


# -----------------------------------
# BACKWARD COMPATIBILITY
# -----------------------------------
# Existing validators import THRESHOLDS directly.
# We preserve that contract.
THRESHOLDS = {
    mode: get_thresholds(mode)
    for mode in QC_MODES
}
