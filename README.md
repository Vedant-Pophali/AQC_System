# AQC System v2.0 - ML-Powered Quality Control


## 📖 Overview
The **Automated Quality Control (AQC) System** is an enterprise-grade pipeline designed to validate broadcast and streaming media against strict technical compliance standards (EBU R.128, Netflix Delivery Specs). 

It features a novel **Machine Learning Artifact Detector** (BRISQUE) that "sees" video quality like a human, rejecting files with macro-blocking, noise, or blur—even if the bitrate is technically sufficient.

### 🌟 Key Features
- 🤖 **ML Artifact Detection**: No-Reference Image Quality Assessment (NR-IQA) using OpenCV & BRISQUE.
- 🔊 **Audio Compliance**: EBU R.128 Loudness, True Peak, and Phase Coherence monitoring.
- 📹 **Video Integrity**: Detection of Freeze Frames, Black Frames, Digital Dropouts, and Interlacing.
- 🔒 **Governance**: Cryptographic config hashing ensures every report is traceable and reproducible.
- 📊 **Visualization**: Interactive HTML dashboard with error timelines and risk heatmaps.

---

## 🏗️ Architecture & Configuration

### Execution Engines
The AQC System supports two execution modes for the analysis pipeline:

1.  **Monolithic Engine (Default)**:
    - **Stability**: High. Recommended for local environment and single-node deployments.
    - **Script**: `main.py`
    - **Behavior**: Runs completely within a single process.

2.  **Spark Engine (Experimental)**:
    - **Scalability**: High. designed for distributed clusters.
    - **Script**: `main_spark.py`
    - **Behavior**: Offloads segment processing to Apache Spark workers.

### ⚙️ Configuration
You can switch engines by modifying `backend/src/main/resources/application.yml`:

```yaml
app:
  aqc:
    engine: MONOLITH # or SPARK
```

## 🐞 Troubleshooting
If you encounter `MojoExecutionException` or H2 database locks:
1.  Delete `backend/data/*.db` files.
2.  The system is configured to use H2 in-memory mode by default for development.

## 🤝 Contributing
1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## 🚀 Quick Start

### 1. Installation
Requires Python 3.10+ and FFmpeg.

```bash
# Clone repository
git clone [https://github.com/Vedant-Pophali/AQC_System.git](https://github.com/Vedant-Pophali/AQC_System.git)
cd aqc_system

# Install dependencies
pip install -r requirements.txt
