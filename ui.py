"""Entry point for the ReelForge desktop UI.

Launches the FastAPI backend on localhost and opens it in a native
pywebview window (Edge WebView2 on Windows).
"""
import os
import sys
import threading
import time
import traceback
from pathlib import Path

# In a PyInstaller --noconsole build, sys.stdout/stderr are None.
if getattr(sys, "frozen", False):
    _log_dir = Path(os.environ.get("TEMP", ".")) / "ReelForge"
    _log_dir.mkdir(parents=True, exist_ok=True)
    _log_file = open(_log_dir / "ui.log", "w", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = _log_file
    if sys.stderr is None:
        sys.stderr = _log_file

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "ui"))

import urllib.request

import webview

from ui_backend import app

PORT = 8765
URL = f"http://127.0.0.1:{PORT}"

LOADING_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>ReelForge</title>
  <style>
    body { background: #111827; color: #f3f4f6; font-family: system-ui, sans-serif;
           display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
    .splash { text-align: center; }
    .spinner { width: 48px; height: 48px; border: 4px solid #374151; border-top-color: #3b82f6;
               border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 1rem; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .msg { color: #9ca3af; font-size: 0.875rem; margin-top: 0.5rem; }
    .title { font-size: 1.5rem; font-weight: 700; margin-bottom: 1rem; }
    .error { color: #f87171; margin-top: 1rem; font-size: 0.8rem; max-width: 400px; }
  </style>
</head>
<body>
  <div class="splash">
    <div class="title">ReelForge</div>
    <div class="spinner"></div>
    <div class="msg" id="msg">Starting backend server...</div>
    <div class="error" id="err"></div>
  </div>
</body>
</html>
"""


class Api:
    def pick_files(self):
        try:
            result = window.create_file_dialog(
                webview.OPEN_DIALOG, allow_multiple=True,
                file_types=("Media files (*.png;*.jpg;*.jpeg;*.webp;*.mp4;*.mov;*.mkv;*.avi;*.webm;*.m4v;*.mpg;*.mpeg;*.flv;*.wmv;*.gif)", "All files (*.*)"),
            )
            if result:
                return list(result)
            return []
        except Exception as e:
            return {"error": str(e)}

    def pick_music(self):
        """Single file dialog for a background music track (path needed)."""
        try:
            result = window.create_file_dialog(
                webview.OPEN_DIALOG, allow_multiple=False,
                file_types=("Audio files (*.mp3;*.wav;*.m4a;*.flac;*.ogg;*.aac;*.opus;*.aiff)",
                            "All files (*.*)"),
            )
            if result:
                return list(result)[0] if isinstance(result, (list, tuple)) else str(result)
            return ""
        except Exception as e:
            return {"error": str(e)}

    def open_folder(self, path):
        try:
            import subprocess
            subprocess.Popen(["explorer", path], creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        except Exception as e:
            return {"error": str(e)}


def start_server():
    try:
        import uvicorn
        uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
    except Exception:
        traceback.print_exc()


def wait_for_server(window):
    """Poll the backend from Python; navigate the window when ready."""
    for i in range(60):
        try:
            urllib.request.urlopen(URL + "/health", timeout=2)
            window.load_url(URL)
            return
        except Exception:
            time.sleep(0.5)
            try:
                window.evaluate_js(f"document.getElementById('msg').textContent = 'Starting backend server... ({i+1})'")
            except Exception:
                pass
    # Timeout
    try:
        window.evaluate_js("document.getElementById('msg').textContent = 'Backend failed to start.'")
        window.evaluate_js("document.getElementById('err').textContent = 'Check %TEMP%\\\\ReelForge\\\\backend.log'")
    except Exception:
        pass


if __name__ == "__main__":
    t = threading.Thread(target=start_server, daemon=True)
    t.start()

    # Show loading window immediately
    window = webview.create_window(
        "ReelForge", html=LOADING_HTML,
        width=1100, height=750, resizable=True, js_api=Api(),
    )
    # Poll for server readiness in a background thread
    threading.Thread(target=wait_for_server, args=(window,), daemon=True).start()
    webview.start()