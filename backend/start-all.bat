@echo off
REM Sensor Data Collector - Master Startup Script
REM Starts both the backend and Cloudflare tunnel

echo ============================================
echo   Sensor Data Collector - Starting...
echo ============================================

REM Start backend in a new window
start "Sensor Backend" powershell -ExecutionPolicy Bypass -File "%~dp0start-backend.ps1"

REM Wait a moment for backend to initialize
timeout /t 5 /nobreak

REM Start Cloudflare tunnel in a new window  
start "Cloudflare Tunnel" powershell -ExecutionPolicy Bypass -File "%~dp0start-tunnel.ps1"

echo.
echo Both services starting in separate windows.
echo.
