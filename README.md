# AQC System v2.0 - ML-Powered Quality Control

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Status: Production](https://img.shields.io/badge/Status-Production%20Ready-green.svg)](docs/COMPLIANCE.md)

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

## 🚀 Quick Start

### 1. Installation
Requires Python 3.10+ and FFmpeg.

```bash
# Clone repository
git clone [https://github.com/Vedant-Pophali/AQC_System.git](https://github.com/Vedant-Pophali/AQC_System.git)
cd aqc_system

# Install dependencies
pip install -r requirements.txt