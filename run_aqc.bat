@echo off
setlocal
echo Starting AQC System...

:: 1. Ask for file path
set /p FULL_PATH="Enter full path to video file: "

:: Remove quotes if the user added them
set FULL_PATH=%FULL_PATH:"=%

:: 2. Parse the path to get Folder and Filename
for %%F in ("%FULL_PATH%") do (
    set VIDEO_DIR=%%~dpF
    set VIDEO_NAME=%%~nxF
)

:: Remove trailing backslash from directory (Docker prefers clean paths)
if "%VIDEO_DIR:~-1%"=="\" set VIDEO_DIR=%VIDEO_DIR:~0,-1%

echo.
echo [DEBUG] Mounting Host Folder : "%VIDEO_DIR%"
echo [DEBUG] Target Filename      : "%VIDEO_NAME%"
echo.

:: 3. Run Docker
:: We mount the USER'S folder (%VIDEO_DIR%) to /data
docker run --rm ^
  -v "%VIDEO_DIR%:/data" ^
  -v "%~dp0docker_reports:/output" ^
  aqc_system ^
  --input "/data/%VIDEO_NAME%" ^
  --outdir "/output" ^
  --mode strict

echo.
echo [DONE] Processing complete. Check 'docker_reports' folder.
pause