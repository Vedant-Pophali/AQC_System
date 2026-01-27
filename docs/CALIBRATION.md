# ML Threshold Calibration Guide

## 1. The Core Concept
The AQC system uses the **BRISQUE** (Blind/Referenceless Image Spatial Quality Evaluator) algorithm.
* **Scale:** 0 to 100.
* **0 = Perfect Quality** (Prinstine, sharp, noiseless).
* **100 = Terrible Quality** (Heavy blocking, blurring, noise).

Unlike simple bitrate checks, BRISQUE measures the "naturalness" of the image statistics.

## 2. Default Thresholds
These defaults are defined in `src/config/threshold_registry.py`.

| Profile | Threshold | Sensitivity | Use Case |
| :--- | :--- | :--- | :--- |
| **NETFLIX_HD** | **50.0** | Very High | Premium SVOD content. Rejects almost any visible noise. |
| **STRICT** | **55.0** | High | Broadcast TV (EBU). Standard for cable delivery. |
| **YOUTUBE** | **65.0** | Medium | Web/Social. Tolerates compression artifacts typical of H.264 web streams. |

## 3. When to Tune

### Scenario A: Too Many False Positives (Rejection of Good Files)
**Symptom:** A clean, high-quality video is marked as `REJECTED`.
**Common Causes:**
* Film grain (artistic intent).
* Dark, underwater, or foggy scenes (low contrast/texture).
**Fix:** **Increase** the threshold (make it more lenient).
* Example: Change `55.0` -> `60.0`.

### Scenario B: Missing Real Artifacts (False Negatives)
**Symptom:** A blocky, pixelated video passes as `PASSED`.
**Common Causes:**
* Anime or Cartoons (BRISQUE is trained on natural photos, not line art).
* Very static content (PowerPoint slides).
**Fix:** **Decrease** the threshold (make it stricter).
* Example: Change `55.0` -> `45.0`.

## 4. Calibration Workflow

To scientifically find the perfect number for your content library:

1.  **Generate Test Data:**
    Use the included tool to create degraded versions of your specific content type.
    ```bash
    python tools/generate_test_videos.py --input source_master.mp4
    ```

2.  **Run Analysis:**
    Run the validator on the "High" and "Low" quality outputs.
    ```bash
    python main.py --input test_data/videos/low_quality.mp4 --outdir calibration_test --mode strict
    ```

3.  **Check the Score:**
    Open the JSON report and find `avg_quality_score`.
    * If Low Quality video scored **75.0**, and your threshold is **55.0**, the system works (75 > 55 = Reject).
    * If Low Quality video scored **45.0**, your threshold is too high (45 < 55 = Pass). Lower it to **40.0**.

## 5. Configuration
Modify `src/config/threshold_registry.py` to apply changes:

```python
"custom_profile": {
    "ml_artifacts": {
        "enabled": True,
        "model": "BRISQUE",
        "threshold_score": 62.5,  # <--- YOUR NEW VALUE HERE
        "sample_rate_fps": 1.0
    }
}