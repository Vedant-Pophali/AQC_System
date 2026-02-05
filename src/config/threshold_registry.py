import json
import hashlib

# ---------------------------------------------------------
# 1. PER-PLATFORM COMPLIANCE PROFILES
# ---------------------------------------------------------
PROFILES = {
    "strict": {
        "description": "Generic Broadcaster (EBU R128 / R37)",
        "audio": {
            "integrated_loudness_target": -23.0,
            "loudness_tolerance": 1.0,
            "true_peak_max": -1.0,
            "max_silence_sec": 2.0,
            "min_phase_correlation": 0.0  # Phase compliance (aphasemeter)
        },
        "video": {
            "black_frame_threshold": 0.1,  # 10% black is black
            "freeze_frame_max_sec": 0.5,
            "dropped_frame_max": 0,
            "require_progressive": True
        },
        "sync": {
            "tolerance_ms": 22.0  # ~1 frame at 24fps (Very Strict)
        },
        # NEW: ML Artifact Detection (BRISQUE)
        "ml_artifacts": {
            "enabled": True,
            "model": "BRISQUE",
            "sample_rate_fps": 1.0,
            "threshold_score": 55.0,  # Calibrated for Broadcast
            "severity_thresholds": {
                "mild": 35.0,
                "moderate": 55.0,
                "severe": 75.0
            },
            "min_duration_sec": 1.0
        }
    },
    "netflix_hd": {
        "description": "Netflix Delivery Spec v9.1 (HD/UHD)",
        "audio": {
            "integrated_loudness_target": -24.0, # Dialogue weighted
            "loudness_tolerance": 2.0,
            "true_peak_max": -2.0,
            "max_silence_sec": 0.5,
            "min_phase_correlation": 0.05  # Netflix usually requires very clean phase
        },
        "video": {
            "black_frame_threshold": 0.05, 
            "freeze_frame_max_sec": 0.0, # Zero tolerance
            "dropped_frame_max": 0,
            "require_progressive": True
        },
        "sync": {
            "tolerance_ms": 40.0 # Standard
        },
        # NEW: ML Artifact Detection
        "ml_artifacts": {
            "enabled": True,
            "model": "BRISQUE",
            "sample_rate_fps": 1.0,
            "threshold_score": 50.0,  # Stricter for Premium
            "severity_thresholds": {
                "mild": 30.0,
                "moderate": 50.0,
                "severe": 70.0
            },
            "min_duration_sec": 1.0
        }
    },
    "youtube": {
        "description": "YouTube / Web Upload (Loose)",
        "audio": {
            "integrated_loudness_target": -14.0, # AES standard for streaming
            "loudness_tolerance": 3.0,
            "true_peak_max": 0.0,
            "max_silence_sec": 5.0,
            "min_phase_correlation": -0.1  # YouTube is more lenient with phase issues
        },
        "video": {
            "black_frame_threshold": 0.2, 
            "freeze_frame_max_sec": 2.0,
            "dropped_frame_max": 15,
            "require_progressive": False
        },
        "sync": {
            "tolerance_ms": 100.0 # Loose sync allowed
        },
        # NEW: ML Artifact Detection
        "ml_artifacts": {
            "enabled": True,
            "model": "BRISQUE",
            "sample_rate_fps": 0.5,   # Lower sampling for speed
            "threshold_score": 65.0,  # More lenient
            "severity_thresholds": {
                "mild": 45.0,
                "moderate": 65.0,
                "severe": 85.0
            },
            "min_duration_sec": 2.0
        }
    },
    "ott": { # Alias for legacy support
        "description": "General OTT (Amazon/Hulu)",
        "audio": {"integrated_loudness_target": -24.0},
        # Inherits generic strict defaults for others
        "ml_artifacts": {
            "enabled": True,
            "model": "BRISQUE",
            "threshold_score": 55.0
        }
    }
}

# ---------------------------------------------------------
# 2. LICENSE COMPLIANCE DOCUMENTATION
# ---------------------------------------------------------
LICENSE_MANIFEST = {
    "AQC_System": "MIT License (Proprietary Logic)",
    "Dependencies": {
        "FFmpeg": "LGPL v2.1+ (Media Decoding)",
        "OpenCV": "Apache 2.0 (Computer Vision)",
        "Librosa": "ISC License (Audio Analysis)",
        "NumPy/SciPy": "BSD 3-Clause (Math)",
        "Plotly": "MIT License (Visualization)"
    },
    "Statement": "This tool uses open-source libraries. Ensure FFmpeg is built with non-free flags if checking specific proprietary codecs."
}

# ---------------------------------------------------------
# 3. LOGIC & VERSIONING
# ---------------------------------------------------------
def get_profile(profile_name):
    """
    Returns the requested profile configuration or defaults to 'strict'.
    """
    # Fallback to strict if unknown
    cfg = PROFILES.get(profile_name, PROFILES["strict"])
    return cfg

def get_thresholds(profile_name):
    """Alias for get_profile to maintain backward compatibility with new modules."""
    return get_profile(profile_name)

def get_config_hash(profile_name):
    """
    3. Versioned Configuration
    Generates a unique SHA256 short-hash for the specific configuration state.
    This guarantees Reproducibility: if the hash is the same, the pass/fail criteria were identical.
    """
    cfg = get_profile(profile_name)
    # Sort keys to ensure consistent hashing
    cfg_str = json.dumps(cfg, sort_keys=True)
    return hashlib.sha256(cfg_str.encode()).hexdigest()[:8]

def get_governance_info(profile_name):
    cfg = get_profile(profile_name)
    return {
        "active_profile": profile_name,
        "config_version_hash": get_config_hash(profile_name),
        "compliance_standard": cfg.get("description", "Custom"),
        "licenses": LICENSE_MANIFEST
    }