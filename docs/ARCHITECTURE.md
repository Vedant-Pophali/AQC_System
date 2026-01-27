# AQC System Architecture

## 1. System Overview
The Automated Quality Control (AQC) system is a modular, python-based pipeline designed to validate broadcast and streaming media against strict technical compliance standards (EBU R.128, Netflix Delivery Specs). It leverages Machine Learning (BRISQUE) for no-reference image quality assessment.


*Figure 1: High-level data flow from Input Video -> Validator Pool -> Aggregation -> Dashboard*

## 2. Component Breakdown

### 2.1 Validation Layer
The core logic resides in `src/validators/`. Each validator is an independent module responsible for a specific domain of quality control.

| Domain | Module | Key Checks | Implementation |
| :--- | :--- | :--- | :--- |
| **Video** | `validate_artifacts.py` | Compression artifacts (Macroblocking/Noise) | **ML: BRISQUE (OpenCV)** |
| | `validate_frames.py` | Freeze Frames, Digital Dropouts | FFmpeg `freezedetect` |
| | `validate_black_freeze.py` | Black Frames (Slates/Gaps) | FFmpeg `blackdetect` |
| | `validate_interlace.py` | Interlacing Artifacts (Combing) | FFmpeg `idet` |
| | `validate_geometry.py` | Resolution, Aspect Ratio, Padding | Bitstream analysis |
| | `validate_analog.py` | Analog Tape Noise, Signal drift | Signalstats |
| **Audio** | `validate_loudness.py` | Loudness Compliance (R.128) | EBU R.128 Filter |
| | `validate_audio_signal.py` | Silence, Phase, DC Offset | Librosa / SciPy |
| **Structure**| `validate_structure.py`| Container/Codec Integrity | FFprobe / MediaInfo |
| **Sync** | `validate_avsync.py` | Audio-Video Synchronization | Cross-correlation |

### 2.2 Machine Learning Pipeline (Research Section 4.2.3)
Located in `src/utils/artifact_scorer.py`, the ML engine provides human-like perceptual quality assessment.

* **Model:** BRISQUE (Blind/Referenceless Image Spatial Quality Evaluator).
* **Implementation:** C++ optimized OpenCV implementation via Python bindings.
* **Workflow:**
    1.  **Sampling:** `src/utils/frame_sampler.py` intelligently samples frames (default 1 FPS) to balance CPU load vs. accuracy.
    2.  **Scoring:** Each frame receives a score (0-100), where higher indicates more artifacts.
    3.  **Classification:** Scores are mapped to severity levels (Clean, Mild, Moderate, Severe) based on the active profile in `threshold_registry.py`.
* **Safety Mechanisms:** Includes variance checks to reject pure black frames which can cause model hallucination.

### 2.3 Reporting & Governance Layer
* **Aggregation:** `src/postprocess/generate_master_report.py` compiles individual validator JSON outputs into a single `Master_Report.json`.
* **Governance:** Every report includes a `config_version_hash` (SHA256) generated from the active profile settings. This ensures auditability—we can prove exactly what thresholds were used for any historical QC job.
* **Visualization:** `src/visualization/visualize_report.py` parses the Master Report to generate a standalone HTML dashboard using Plotly, featuring interactive error timelines and risk heatmaps.

## 3. Configuration & Profiles
Configuration is managed in `src/config/threshold_registry.py`. The system supports dynamic switching between compliance standards:

* **STRICT:** Broadcast TV standards (Narrow tolerances, High artifact sensitivity).
* **NETFLIX_HD:** Premium SVOD standards (Compliance with Netflix Delivery Spec).
* **YOUTUBE:** Web standards (Lenient bitrate and loudness tolerances).

## 4. Scalability
The system supports two modes of operation:
1.  **Single File:** Direct execution via `main.py` for immediate feedback.
2.  **Batch/Parallel:** Executed via `batch_runner.py`, utilizing Python's `ProcessPoolExecutor` to analyze multiple files concurrently, bounded by available CPU cores.