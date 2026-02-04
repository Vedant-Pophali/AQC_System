@echo off
echo ===========================================
echo   SPECTRA AQC - DEVELOPMENT LAUNCHER
echo ===========================================

echo.
echo 1. Starting Backend Server (Spring Boot)...
start "Spectra Backend" cmd /k "cd backend && run_backend.bat"

echo 2. Starting Frontend Client (Vite)...
start "Spectra Frontend" cmd /k "cd frontend && run_frontend.bat"

echo.
echo ===========================================
echo   SYSTEM STARTING...
echo ===========================================
echo   Backend will be at: http://localhost:8080
echo   Frontend will be at: http://localhost:5173
echo.
echo   (You can close this window now)
pause
