@echo off
REM Helper script to run Spectra AQC Backend with correct Java Environment
set "JAVA_HOME=C:\Program Files\Microsoft\jdk-21.0.10.7-hotspot"
set "PATH=%JAVA_HOME%\bin;%PATH%"

echo ==========================================
echo Starting Spectra AQC Backend
echo USING JAVA_HOME: %JAVA_HOME%
echo ==========================================

REM Ensure we are in the backend directory (where pom.xml is)
cd /d "%~dp0"

mvn spring-boot:run -DskipTests
