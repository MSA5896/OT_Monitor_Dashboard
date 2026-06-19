@echo off
title OT Monitor – Starting...
echo.
echo  OT Infection Monitoring Dashboard
echo  ----------------------------------
echo  Starting backend on http://localhost:8001
echo.

cd /d "%~dp0backend"

:: Kill any stale process on port 8001
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8001 "') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: Start backend in a new terminal window (shows logs)
start "OT Monitor Backend" cmd /k python main.py

:: Wait for backend to start
timeout /t 4 /nobreak >nul

:: Open the dashboard in the default browser
start "" "http://localhost:8001/"

echo  Browser opened at http://localhost:8001/
echo.
echo  Credentials:
echo    Admin  : admin  / OTAdmin2024
echo    Viewer : nurse  / OTNurse2024
echo.
pause
