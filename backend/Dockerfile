# Build Stage
FROM maven:3.9.6-eclipse-temurin-17 AS build
WORKDIR /app
COPY pom.xml .
COPY src ./src
RUN mvn clean package -DskipTests

# Run Stage
FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=build /app/target/aqc-backend-0.0.1-SNAPSHOT.jar app.jar

# Expose Port
EXPOSE 8080

# Environment Variables (Default to Production/Remote)
ENV APP_AQC_EXECUTION_MODE=REMOTE
ENV APP_STORAGE_UPLOAD_DIR=/tmp/uploads

entrypoint ["java", "-jar", "app.jar"]
