# AQC System (Automated Quality Control)

**Version:** 1.0.0 (Product-Ready)  
**License:** MIT / Open Source  

## 📖 Overview
The **AQC System** is a broadcast-grade automated quality control tool designed to validate video assets against strict technical specifications. It replaces manual spot-checking with frame-accurate automated analysis.

It is capable of detecting:
* **Visual Defects:** Black frames, Freeze frames, Interlacing artifacts, Letterboxing/Pillarboxing.
* **Audio Defects:** Loudness violations (EBU R128), Phase cancellation, Clipping, Dropouts.
* **Structural Issues:** Container corruption, Missing metadata, Codec mismatches.
* **A/V Sync:** Synchronization drift and offset.

## 🚀 Key Features
* **3 Operation Modes:**
    * `STRICT`: For Broadcast TV (EBU R128, -23 LUFS, Perfect Sync).
    * `NETFLIX_HD`: For Premium Streaming (High bitrate, 0 freeze tolerance).
    * `YOUTUBE`: For Web/Social (Relaxed Loudness -14 LUFS, Loose Sync).
* **Batch Processing:** Scan 1,000+ videos in parallel and get a single Excel summary.
* **Interactive Dashboard:** HTML reports with clickable timelines that jump video playback to the exact error frame.
* **Governance:** Reproducible Config Hashes to ensure audit trails.

---

## 🛠️ Installation

### Prerequisites
1.  **Docker Desktop** (Recommended for stability).
2.  **Python 3.10+** (Required only to launch the GUI).

### Setup
1.  Unzip the package.
2.  Open a terminal in the folder.
3.  Install dependencies (for the GUI and Local Runner):
    ```bash
    pip install -r requirements.txt
    ```

---

## 🖥️ How to Use (3 Methods)

### Method 1: The "Boss Mode" (GUI) - Recommended
*Best for: Non-technical users who want to scan a folder of videos.*

1.  Make sure **Docker Desktop** is running.
2.  Double-click **`run_aqc.bat`**.
3.  The **AQC Launcher** window will appear.
    * **Input Folder:** Select the folder containing your videos.
    * **Output Folder:** Select where you want the reports.
    * **Profile:** Choose `Strict`, `Netflix`, or `YouTube`.
4.  Click **START QC BATCH**.
5.  The system will process files in the background and notify you when finished.

### Method 2: Batch CLI (Power User)
*Best for: Running large batches on a server or without the GUI.*

```bash
python batch_runner.py --input_dir "C:\Videos" --output_dir "C:\Reports" --mode strict --workers 4