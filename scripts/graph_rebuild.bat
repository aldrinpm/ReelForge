@echo off
rem Rebuild the local codebase knowledge graph (Graphify, OSS, no cloud).
cd /d E:\AI-Video-Production
graphify . --code-only --update
if errorlevel 1 (
  echo.
  echo Graphify failed. Install with: uv tool install graphifyy  (or pipx install graphifyy)
  pause
)
exit /b 0