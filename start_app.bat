@echo off
title Enterprise Intelligence Explorer - Launcher
echo ============================================================
echo      Enterprise Intelligence Explorer - Startup
echo ============================================================
echo.

echo 1/2 Starting Backend API (Port 8000)...
start "Backend API" cmd /c "cd /d "%~dp0backend" && py -3 -m uvicorn main:app --port 8000"

echo 2/2 Starting Frontend Website (Port 3000)...
start "Frontend Dashboard" cmd /c "cd /d "%~dp0frontend" && py -3 -m http.server 3000"

echo.
echo ============================================================
echo   SUCCESS: Both servers are starting in separate windows.
echo.
echo   - Website: http://localhost:3000
echo   - Backend: http://127.0.0.1:8000
echo.
echo   Keep this window open until everything has loaded.
echo ============================================================
echo.
pause
