# AQC System API & CLI Reference

## 1. Command Line Interface (CLI)

The AQC system is primarily designed to be run via the command line.

### 1.1 Single File Analysis (`main.py`)
Analyzes a single video file and generates a full QC report.

```bash
python main.py --input <VIDEO_PATH> --outdir <OUTPUT_DIR> [--mode <PROFILE>] [--fix]