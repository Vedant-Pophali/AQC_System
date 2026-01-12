# Use a lightweight Python base
FROM python:3.11-slim

# 1. Install System Dependencies (FFmpeg is critical)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# 2. Set Working Directory
WORKDIR /app

# 3. Install Python Libraries
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the Application Code
COPY . .

# 5. Define Environment Variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 6. Default Command (Shows Help)
CMD ["python", "batch_runner.py", "--help"]