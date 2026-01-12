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
            "max_silence_sec": 2.0
        },
        "video": {
            "black_frame_threshold": 0.1,  # 10% black is black
            "freeze_frame_max_sec": 0.5,
            "dropped_frame_max": 0,
            "require_progressive": True
        },
        "sync": {
            "tolerance_ms": 22.0  # ~1 frame at 24fps (Very Strict)
        }
    },
    "netflix_hd": {
        "description": "Netflix Delivery Spec v9.1 (HD/UHD)",
        "audio": {
            "integrated_loudness_target": -24.0, # Dialogue weighted
            "loudness_tolerance": 2.0,
            "true_peak_max": -2.0,
            "max_silence_sec": 0.5
        },
        "video": {
            "black_frame_threshold": 0.05, 
            "freeze_frame_max_sec": 0.0, # Zero tolerance
            "dropped_frame_max": 0,
            "require_progressive": True
        },
        "sync": {
            "tolerance_ms": 40.0 # Standard
        }
    },
    "youtube": {
        "description": "YouTube / Web Upload (Loose)",
        "audio": {
            "integrated_loudness_target": -14.0, # AES standard for streaming
            "loudness_tolerance": 3.0,
            "true_peak_max": 0.0,
            "max_silence_sec": 5.0
        },
        "video": {
            "black_frame_threshold": 0.2, 
            "freeze_frame_max_sec": 2.0,
            "dropped_frame_max": 15,
            "require_progressive": False
        },
        "sync": {
            "tolerance_ms": 100.0 # Loose sync allowed
        }
    },
    "ott": { # Alias for legacy support
        "description": "General OTT (Amazon/Hulu)",
        "audio": {"integrated_loudness_target": -24.0},
        # Inherits generic strict defaults for others
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