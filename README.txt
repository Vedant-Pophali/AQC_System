Automated Media Quality Control Tool (v1.1)
===========================================

Overview
--------
This tool performs automated QC on video files, checking for:
1. Visual Defects (Black Frames)
2. Audio Compliance (EBU R.128 Loudness)
3. Vernacular Text Presence (Hindi OCR)

Installation
------------
1. Double-click 'setup.bat' (Run this only once).
   - This installs the required AI libraries (Torch, EasyOCR).

How to Run
----------
Option A: Graphical Interface (Recommended)
   - Double-click 'start_gui.bat'.
   - Select your video file and click "START QC ANALYSIS".

Option B: Command Line
   - Double-click 'run_qc.bat' and type your command:
     run_qc.bat --input your_video.mp4

Configuration (Advanced)
------------------------
You can adjust the QC thresholds in the 'qc_config.json' file.

- "target_lufs": Set the loudness target (Default: -23.0 for Broadcast).
- "sampling_interval_seconds": How often to check for text (Default: 5.0s).
   - Decrease to 1.0s for higher accuracy (Slower).
   - Increase to 10.0s for faster processing (Lower accuracy).
- "target_width_px": Internal resolution for OCR.
   - Keep at 640 for best CPU performance.

Outputs
-------
Reports are saved in the 'reports' folder.
- dashboard.html: Interactive Visual Report.
- Master_Report.json: Full technical data.