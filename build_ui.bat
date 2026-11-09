@echo off
rem Package the desktop UI into a folder (onedir = faster startup, no extraction flicker).
rem Requires: pyinstaller (pip install pyinstaller) in the base Python.
cd /d E:\AI-Video-Production
"E:\ai\AirLLM\py3.11.9\python.exe" -m PyInstaller ^
  -y ^
  --onedir ^
  --name "ReelForge" ^
  --add-data="ui:ui" ^
  --add-data="scripts:scripts" ^
  --add-data="config.json:." ^
  --hidden-import "ui.ui_backend" ^
  --hidden-import "config" ^
  --hidden-import "llm_client" ^
  --hidden-import "engineio.async_drivers.threading" ^
  --noconsole ^
  ui.py
if errorlevel 1 (
  echo.
  echo Build failed. Install PyInstaller: pip install pyinstaller
  pause
  exit /b 1
)
echo.
echo Build complete: dist\ReelForge\ReelForge.exe
echo Run the exe from the dist folder. Do NOT move it alone.
echo NOTE: FFmpeg and model weights are NOT bundled (on PATH / E: cache).
pause