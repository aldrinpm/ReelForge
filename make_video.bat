@echo off
rem ============================================================
rem  One-click video builder
rem  Put prompt.txt + 6 images into inbox\<name>\, then run this.
rem ============================================================
cd /d E:\AI-Video-Production

if "%~1"=="" goto choose
set "RUN_NAME=%~1"
goto run

:choose
echo Available videos in inbox:
dir /b inbox 2>nul
echo.
set /p RUN_NAME=Video name (folder under inbox):
if "%RUN_NAME%"=="" (
  echo No name entered.
  pause
  exit /b 1
)

:run
"E:\ai\AirLLM\py3.11.9\python.exe" "scripts\run_video.py" %RUN_NAME%
if errorlevel 1 (
  echo.
  echo Pipeline failed - see the messages above and the log in logs\.
  pause
)
exit /b 0
