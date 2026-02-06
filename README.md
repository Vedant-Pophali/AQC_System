# Spectra AQC System

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/Vedant-Pophali/AQC_System)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Java](https://img.shields.io/badge/java-17%2B-orange)](https://www.java.com/)
[![React](https://img.shields.io/badge/react-19.0-61DAFB)](https://react.dev/)
[![Spring Boot](https://img.shields.io/badge/spring--boot-3.0-green)](https://spring.io/projects/spring-boot)

**Spectra Automated Quality Control (AQC)** is an enterprise-grade media validation pipeline designed for broadcast and OTT environments. It leverages hybrid Machine Learning (ML) and Digital Signal Processing (DSP) to ensure technical compliance with industry standards (EBU R.128, Netflix Delivery Specs).

---

## 🚀 Key Features

### 🧠 ML-Powered Visual Analysis
*   **BRISQUE Integration**: Utilizes Blind/Referenceless Image Spatial Quality Evaluator for perceptual quality scoring.
*   **Artifact Detection**: Identifies macro-blocking, digital noise, and blur anomalies.
*   **Deep Learning**: Custom models for complex visual defect recognition.

### 🔊 Audio Compliance & Engineering
*   **Loudness Normalization**: Strict adherence to **EBU R.128** (-23 LUFS) and **ATSC A/85**.
*   **Signal Integrity**: True Peak monitoring, Phase Coherence analysis, and Silence detection.
*   **Automated Remediation**: Self-healing pipeline capable of correcting loudness violations automatically.

### 📹 Video Technical QA
*   **Structural Integrity**: Validates container formats, codecs, and metadata.
*   **Anomaly Detection**: Detects black frames, freeze frames, digital dropouts, and interlacing artifacts.
*   **AV Sync**: Precision Audio-Video synchronization testing.

### 🛡️ Enterprise Governance
*   **Cryptographic Audit Trail**: Every analysis profile is hashed/signed to ensure reproducibility.
*   **Immutable Reporting**: JSON/PDF reports with embedded governance signatures.
*   **Profile Management**: Pre-configured profiles for Netflix HD, YouTube, OTT, and Strict Broadcast.

---

## 🏗️ System Architecture

The system operates on a decoupled architecture, orchestrating Python-based analysis engines via a Java Spring Boot backend, with a modern React frontend for monitoring.

```mermaid
graph TD
    User[User / Watch Folder] -->|Upload| API[Spring Boot Backend]
    
    subgraph "Core Orchestration"
        API -->|Dispatch| Engine[Analysis Engine]
        Engine -->|Route| Monolith[Local Executor]
        Engine -->|Route| Spark[Spark Cluster]
    end
    
    subgraph "Validation Pipeline (Python)"
        Monolith --> V1[Structure Check]
        Monolith --> V2[Audio Analysis]
        Monolith --> V3[Video ML (BRISQUE)]
        Monolith --> V4[AV Sync]
    end
    
    subgraph "Data & Reporting"
        V1 & V2 & V3 & V4 -->|JSON| Aggregator[Report Aggregator]
        Aggregator -->|Store| DB[(H2 / PostgreSQL)]
        Aggregator -->|Visualize| Dashboard[React Frontend]
    end
```

---

## 🛠️ Technology Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | React 19, Vite, Sass | Real-time analysis dashboard and reporting UI. |
| **Backend** | Java 17, Spring Boot 3 | REST API, Job Orchestration, File Management. |
| **Core Engine** | Python 3.10, OpenCV, SciPy | Signal processing, ML inference (PyTorch/TensorFlow compatible). |
| **Distributed** | Apache Spark | Optional scale-out for massive dataset processing. |
| **Database** | H2 (Dev) / PostgreSQL (Prod) | Job persistence and historical analytics. |

---

## ⚡ Quick Start Guide

### Prerequisites
*   **Java JDK 17+**
*   **Python 3.10+** (with `pip`)
*   **Node.js 18+** & `npm`
*   **FFmpeg** (Must be in system PATH)

### 1. Backend Setup
Start the Spring Boot server to handle API requests and orchestration.
```bash
cd backend
mvn spring-boot:run
# Server runs on http://localhost:8080
```

### 2. Frontend Setup
Launch the modern React dashboard.
```bash
cd frontend
npm install
npm run dev
# UI runs on http://localhost:5173
```

### 3. Core Engine Setup
Install Python dependencies for the analysis pipeline.
```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuration & Profiles

The system uses `src/config/threshold_registry.py` to manage compliance profiles. You can select a profile via the API or CLI.

| Profile | Description | Loudness Target |
| :--- | :--- | :--- |
| **strict** | Broadcast standard (default). | -23.0 LUFS |
| **netflix_hd** | Netflix non-linear spec. | -27.0 LUFS |
| **youtube** | Optimized for web streaming. | -14.0 LUFS |
| **ott** | General OTT aggregation spec. | -24.0 LUFS |

### Automatic Remediation
To enable auto-correction (e.g., loudness normalization), pass the `--fix` flag or enable "Auto-Fix" in the UI when submitting a job.

---

## 🤝 Contributing

We welcome contributions! Please follow the steps below:
1.  **Fork** the repository.
2.  Create a feature branch: `git checkout -b featured/new-validator`.
3.  Commit changes: `git commit -m "feat: add HDR validation"`.
4.  Push to branch: `git push origin feature/new-validator`.
5.  Open a **Pull Request**.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
