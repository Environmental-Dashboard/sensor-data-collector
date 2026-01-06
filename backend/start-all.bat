@echo off
REM Sensor Data Collector - Start All Services
REM Usage: start-all.bat [/hidden]
REM   /hidden - Run without any visible windows

cd /d "%~dp0"

if "%1"=="/hidden" (
    echo Starting services in hidden mode...
    wscript.exe "%~dp0start-hidden.vbs"
    echo Services starting in background. Check backend.log and tunnel.log for status.
    exit /b
)

echo ============================================
echo   Sensor Data Collector - Starting Services
echo ============================================
echo.
echo Starting backend and tunnel...
echo Log files will be created in: %~dp0
echo   - backend.log
echo   - tunnel.log  
echo   - tunnel_url.txt (contains current tunnel URL)
echo.

REM Start both hidden
wscript.exe "%~dp0start-hidden.vbs"

echo.
echo Services are starting in background.
echo.
echo To check status:
echo   - View backend.log for backend status
echo   - View tunnel.log for tunnel status
echo   - View tunnel_url.txt for current tunnel URL
echo.
echo Press any key to exit...
pause >nul
