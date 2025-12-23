@echo off
setlocal
cd /d "%~dp0"

echo [INFO] --- QC TOOL LAUNCHER ---
echo [INFO] Working Directory: %~dp0

:: 1. SETUP VENV (If missing)
if not exist venv (
    echo [INFO] Creating Python environment...
    python -m venv venv
)

:: 2. INSTALL & REPAIR (Verbose Mode)
echo.
echo [INFO] Checking libraries...
echo (This ensures all modules are present. Please wait...)
:: Install everything from requirements
venv\Scripts\pip install -r requirements.txt >nul 2>&1

:: FORCE FIX: Remove the "Headless" version that breaks the GUI
:: We run this EVERY time to guarantee the conflict is gone.
echo [INFO] Removing conflicting OpenCV versions...
venv\Scripts\pip uninstall -y opencv-python-headless >nul 2>&1

:: FORCE FIX: Install the "Standard" version required for the GUI
echo [INFO] Installing standard OpenCV...
venv\Scripts\pip install opencv-python >nul 2>&1

:: FORCE FIX: Ensure Pandas/EasyOCR are present (Fixes ModuleNotFoundError)
echo [INFO] Verifying core modules...
venv\Scripts\pip install pandas plotly easyocr >nul 2>&1

:: 3. LAUNCH (Directly, no 'start' command)
echo.
echo [INFO] Launching Tool...

if not exist "src\launcher.py" (
    echo [CRITICAL ERROR] Could not find src\launcher.py!
    echo Please ensure the 'src' folder is next to this script.
    pause
    exit /b
)

:: Run Python directly in this window so we see errors
venv\Scripts\python.exe src\launcher.py

:: 4. ERROR HANDLING
if %errorlevel% neq 0 (
    echo.
    echo ========================================================
    echo [CRITICAL] The tool crashed.
    echo PLEASE COPY THE ERROR MESSAGE ABOVE AND PASTE IT IN CHAT
    echo ========================================================
    pause
) else (
    echo.
    echo [INFO] Tool closed normally.
    pause
)