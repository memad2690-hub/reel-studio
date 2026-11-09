@echo off
rem Reel Studio launcher (Windows). Double-click this file.
rem The studio runs only on this computer (http://127.0.0.1) and is never reachable from the internet.
title Reel Studio
cd /d "%~dp0"

where git >nul 2>nul && (
  echo Getting the latest version...
  git pull --ff-only
)

echo Checking Python packages...
python -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo.
  echo Python or pip is not working. Install Python 3.11+ from python.org and tick "Add to PATH".
  pause
  exit /b 1
)

if not exist node_modules\playwright (
  echo Installing the renderer - first run only...
  call npm install
  call npx playwright install chromium
)

echo.
echo Starting Reel Studio - the browser opens by itself.
echo Keep this window open while you work. Close it, or press Ctrl+C, to stop the studio.
echo.
python reel.py studio --open
pause
