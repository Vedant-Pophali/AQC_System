# 1. Base Image: Lightweight Python
FROM python:3.10-slim-bookworm

# 2. Optimization Flags
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Install System Dependencies (FFmpeg for Audio/Signal QC)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 4. Set Work Directory
WORKDIR /app

# 5. Install Python Libraries
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy Your Code
COPY src/ ./src/
COPY qc_config.json .

# 7. Create Output Folders (Crucial for PDF/JSON reports)
RUN mkdir -p /app/reports /app/temp_upload

# 8. THE WEB COMMAND (Streamlit)
# This tells Docker: "Open Port 8501 and run the App"
EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0"]