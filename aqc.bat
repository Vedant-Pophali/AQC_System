@echo off
setlocal enabledelayedexpansion

REM ==================================================
REM  AQC - Automated Quality Control (Windows CLI)
REM ==================================================

REM ---- Resolve project root ----
set SCRIPT_DIR=%~dp0
set SRC_DIR=%SCRIPT_DIR%src

REM ---- Python detection ----
where python >nul 2>nul
if errorlevel 1 (
    echo [FATAL] Python not found in PATH.
    echo Install Python 3.9+ and retry.
    exit /b 1
)

REM ---- Entry point ----
if "%1"=="" goto HELP
if "%1"=="-h" goto HELP
if "%1"=="--help" goto HELP

REM ---- Defaults ----
set INPUT=
set MODE=strict
set OUTDIR=reports
set SEGMENT=

REM ---- Parse arguments ----
:PARSE
if "%1"=="" goto RUN

if "%1"=="--input" (
    set INPUT=%2
    shift
    shift
    goto PARSE
)

if "%1"=="--mode" (
    set MODE=%2
    shift
    shift
    goto PARSE
)

if "%1"=="--outdir" (
    set OUTDIR=%2
    shift
    shift
    goto PARSE
)

if "%1"=="--segment" (
    set SEGMENT=%2
    shift
    shift
    goto PARSE
)

echo [ERROR] Unknown argument: %1
goto HELP

REM ---- Run QC ----
:RUN
if "%INPUT%"=="" (
    echo [ERROR] --input is required
    goto HELP
)

REM ---- Resolve input path ----
if not exist "%INPUT%" (
    echo [FATAL] Input file not found:
    echo         %INPUT%
    echo.
    echo Hint:
    echo   - Use a full path, or
    echo   - Place the file in this directory, or
    echo   - Use .\filename.mp4
    exit /b 1
)

echo.
echo ================================================
echo   AQC - Automated Quality Control
echo ================================================
echo   Input   : %INPUT%
echo   Mode    : %MODE%
if not "%SEGMENT%"=="" (
    echo   Segment : %SEGMENT% sec
) else (
    echo   Segment : disabled
)
echo   Output  : %OUTDIR%
echo ================================================
echo.

REM ---- Build command ----
set CMD=python "%SRC_DIR%\run_qc_pipeline.py" --input "%INPUT%" --mode %MODE% --outdir "%OUTDIR%"

if not "%SEGMENT%"=="" (
    set CMD=%CMD% --segment %SEGMENT%
)

REM ---- Execute ----
%CMD%

set EXIT_CODE=%ERRORLEVEL%

echo.
if %EXIT_CODE% NEQ 0 (
    echo [FAILED] QC pipeline exited with code %EXIT_CODE%
) else (
    echo [DONE] QC pipeline completed successfully
)

exit /b %EXIT_CODE%

REM ---- Help ----
:HELP
echo.
echo AQC - Automated Quality Control (Windows)
echo.
echo Usage:
echo   aqc --input ^<video_file^> [options]
echo.
echo Required:
echo   --input ^<file^>          Input video file
echo.
echo Optional:
echo   --mode strict^|ott        QC mode (default: strict)
echo   --outdir ^<dir^>          Output directory (default: reports)
echo   --segment ^<seconds^>     Enable temporal segmentation
echo.
echo Examples:
echo   aqc --input .\sample.mp4
echo   aqc --input .\sample.mp4 --segment 300
echo   aqc --input C:\videos\movie.mp4 --mode ott --segment 600
echo.
exit /b 0
