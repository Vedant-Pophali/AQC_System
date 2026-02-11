# 1. Build Stage
FROM maven:3.9.6-eclipse-temurin-17 AS build
WORKDIR /app
# Copy POM and Source relative to Root Context
COPY backend/pom.xml .
COPY backend/src ./src
RUN mvn clean package -DskipTests

# 2. Run Stage
FROM eclipse-temurin:17-jre
WORKDIR /app

# Install Python and FFmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy JAR from Build Stage
COPY --from=build /app/target/aqc-backend-0.0.1-SNAPSHOT.jar app.jar

# Copy Python Application Source
COPY main.py .
COPY src ./src
COPY requirements.txt .

# Install Python Dependencies
# Use --break-system-packages for recent Debian/Ubuntu versions if needed, or venv
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages

# Environment Configuration
ENV APP_AQC_EXECUTION_MODE=LOCAL
ENV APP_STORAGE_UPLOAD_DIR=/tmp/uploads

# Expose Port
EXPOSE 8080

# Entrypoint
ENTRYPOINT ["java", "-jar", "app.jar"]