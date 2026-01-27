# 1. Base Image (Explicit Stable)
FROM python:3.11-slim-bookworm

# 2. Environment Config
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. FIX: Configure APT to be resilient against unstable mirrors
# Disabling pipelining fixes most "Hash Sum Mismatch" errors
RUN echo "Acquire::http::Pipeline-Depth 0;" > /etc/apt/apt.conf.d/99custom && \
    echo "Acquire::http::No-Cache true;" >> /etc/apt/apt.conf.d/99custom && \
    echo "Acquire::BrokenProxy true;" >> /etc/apt/apt.conf.d/99custom

# 4. Install System Dependencies
# We use a double-update strategy to ensure lists are fresh
RUN rm -rf /var/lib/apt/lists/* && \
    apt-get update -o Acquire::CompressionTypes::Order::=gz && \
    apt-get install -y --no-install-recommends --fix-missing \
    ffmpeg \
    libsndfile1 \
    libsm6 \
    libxext6 \
    libgl1 \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 5. Set Working Directory
WORKDIR /app

# 6. Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 7. Copy Application Code
COPY . .

# 8. Environment Variables
ENV PYTHONPATH=/app

# 9. Build-Time Health Check
RUN python -c "import cv2; print(f'Build Check: OpenCV {cv2.__version__} Ready')"

# 10. Default Command
ENTRYPOINT ["python", "main.py"]
CMD ["--help"]