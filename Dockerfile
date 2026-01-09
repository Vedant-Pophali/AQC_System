# 1. Base Image
FROM python:3.10-slim-bookworm

# 2. Optimization & Hardening
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# 3. Install System Dependencies (Merged List)
# We include the heavy Qt/AV libraries required for QCTools
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    cmake \
    pkg-config \
    curl \
    procps \
    default-jdk \
    mediainfo \
    libbz2-dev \
    zlib1g-dev \
    ffmpeg \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libavfilter-dev \
    libavdevice-dev \
    libswscale-dev \
    libswresample-dev \
    qtbase5-dev \
    qttools5-dev-tools \
    qtmultimedia5-dev \
    qtdeclarative5-dev \
    qtquickcontrols2-5-dev \
    libqt5svg5-dev \
    libqt5opengl5-dev \
    libgl1 \
    libxext6 \
    libsm6 \
    && rm -rf /var/lib/apt/lists/*

# 4. Set JAVA_HOME (For Spark)
ENV JAVA_HOME="/usr/lib/jvm/default-java"
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# ============================================================
# 5. Build QWT (The Missing Piece for QCTools)
# ============================================================
RUN echo "--- Building QWT ---" && \
    git clone https://github.com/opencor/qwt.git /tmp/qwt && \
    cd /tmp/qwt && \
    qmake qwt.pro && \
    make -j$(nproc) && \
    make install && \
    cp /usr/local/qwt-*/lib/* /usr/lib/ && \
    rm -rf /tmp/qwt

# ============================================================
# 6. Build QCTools (CLI Version)
# ============================================================
RUN echo "--- Compiling QCTools ---" && \
    git clone --recursive https://github.com/bavc/qctools.git /tmp/qctools && \
    cd /tmp/qctools && \
    # We explicitly point to the .pro file
    qmake Project/QtCreator/QCTools.pro && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    cd / && \
    rm -rf /tmp/qctools

# 7. Set Work Directory
WORKDIR /app

# 8. Install Python Libraries (Automation Brain)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir streamlit opencv-python-headless numpy pandas plotly ffmpeg-python pyspark lxml scikit-image

# 9. Install AI Libraries (OCR)
RUN pip install --default-timeout=1000 --no-cache-dir \
    torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir easyocr

# 10. Copy Source Code
COPY src/ ./src/
COPY src/config/qc_config.json .

# 11. Final Config
RUN mkdir -p /app/reports /app/temp_upload

# 12. Entrypoint (Keep Streamlit)
EXPOSE 8501
ENTRYPOINT ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0"]