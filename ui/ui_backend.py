"""FastAPI backend for the ReelForge desktop UI.

Exposes the pipeline (run_video.py) and service health via a localhost-only
HTTP API consumed by the pywebview frontend. Heavy work runs in background
threads; progress is streamed over SSE.
"""
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
from pathlib import Path
from typing import Optional

# In a PyInstaller --noconsole build, sys.stdout/stderr are None.
if getattr(sys, "frozen", False):
    _log_dir = Path(os.environ.get("TEMP", ".")) / "ReelForge"
    _log_dir.mkdir(parents=True, exist_ok=True)
    _log_file = open(_log_dir / "backend.log", "w", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = _log_file
    if sys.stderr is None:
        sys.stderr = _log_file

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ROOT = Path(r"E:\AI-Video-Production")
SCRIPTS = ROOT / "scripts"
BASE_PY = r"E:\ai\AirLLM\py3.11.9\python.exe"
VENV_PY = ROOT / "venv-tts" / "Scripts" / "python.exe"
CONFIG_PATH = ROOT / "config.json"

_console_queue = queue.Queue()
_console_history = []
_MAX_CONSOLE_HISTORY = 1000
_health_prev = {}


def console_log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    _console_history.append(line)
    if len(_console_history) > _MAX_CONSOLE_HISTORY:
        del _console_history[:len(_console_history) - _MAX_CONSOLE_HISTORY]
    _console_queue.put({"type": "console", "line": line})
    try:
        print(line, flush=True)
    except Exception:
        pass


console_log("Backend started", "INFO")
console_log(f"ROOT={ROOT}", "DEBUG")
console_log(f"Config: {CONFIG_PATH}", "DEBUG")

app = FastAPI(title="ReelForge", version="1.0")

# CORS for pywebview (same-origin should work, but be safe)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Static frontend ---
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# --- Service health ---

def _probe_ffmpeg():
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        ver = (r.stdout or "").splitlines()[0] if r.returncode == 0 else ""
        status = "ok" if r.returncode == 0 else "down"
        console_log(f"FFmpeg: {status} ({ver[:40]})", "DEBUG" if status == "ok" else "WARN")
        return {"status": status, "version": ver[:60]}
    except Exception as e:
        console_log(f"FFmpeg probe failed: {e}", "ERROR")
        return {"status": "down", "error": str(e)}


def _probe_espeak():
    p = Path(r"C:\Program Files\eSpeak NG\espeak-ng.exe")
    return {"status": "ok" if p.exists() else "down", "path": str(p)}


def _probe_venv():
    return {"status": "ok" if VENV_PY.exists() else "down", "path": str(VENV_PY)}


@app.get("/health")
def health():
    global _health_prev
    h = {
        "ffmpeg": _probe_ffmpeg(),
        "espeak": _probe_espeak(),
        "venv_tts": _probe_venv(),
        "config_exists": CONFIG_PATH.exists(),
    }
    for k, v in h.items():
        if isinstance(v, dict) and "status" in v:
            prev = _health_prev.get(k)
            if prev != v["status"]:
                console_log(f"Health {k}: {prev or 'init'} -> {v['status']}", "INFO" if v["status"] == "ok" else "WARN")
                _health_prev[k] = v["status"]
    return h


@app.get("/console/stream")
def console_stream():
    def event_gen():
        # Send history first
        for line in _console_history:
            yield f"data: {json.dumps({'type': 'console', 'line': line})}\n\n"
        while True:
            try:
                msg = _console_queue.get(timeout=1)
                yield f"data: {json.dumps(msg)}\n\n"
            except queue.Empty:
                yield ": keepalive\n\n"
    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.get("/console/history")
def console_history():
    return {"lines": _console_history[-200:]}

@app.get("/config")
def get_config():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


class ConfigUpdate(BaseModel):
    config: dict


@app.put("/config")
def put_config(body: ConfigUpdate):
    CONFIG_PATH.write_text(
        json.dumps(body.config, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {"ok": True}


@app.post("/config/validate")
def validate_config(body: ConfigUpdate):
    """Validate config: check voice availability."""
    errors = []
    cfg = body.config
    # Check voice
    voice = cfg.get("tts", {}).get("voice", "")
    if voice:
        try:
            sys.path.insert(0, str(SCRIPTS))
            import generate_narration as gn
            if voice not in gn.KOKORO_VOICES:
                errors.append(f"Voice '{voice}' not in known list")
        except Exception:
            pass
    return {"valid": len(errors) == 0, "errors": errors}


# --- Models / voices ---

@app.get("/config/defaults")
def config_defaults():
    """Built-in defaults (scripts/config.py) so Settings can reset safely."""
    try:
        sys.path.insert(0, str(SCRIPTS))
        import config as cfg_mod
        d = cfg_mod.DEFAULT_CONFIG
        tts_keys = ("voice", "speed")
        return {"config": {
            "tts": {k: d["tts"][k] for k in tts_keys if k in d["tts"]},
        }}
    except Exception as e:
        return {"config": None, "error": str(e)}


@app.get("/models")
def models():
    # LLM removed; return empty list
    return {"models": [], "current": None}


@app.get("/voices")
def voices():
    # Curated list; availability is probed by /voices/probe if needed.
    curated = [
        "af_heart", "af_alloy", "af_aoede", "af_bella", "af_jessica", "af_kore",
        "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",
        "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam", "am_michael",
        "am_onyx", "am_puck", "am_santa",
        "bf_alice", "bf_emma", "bf_isabella", "bf_lily",
        "bm_daniel", "bm_fable", "bm_george", "bm_lewis",
    ]
    return {"voices": curated}


# --- Run note / voice preview helpers ---

class VoicePreviewRequest(BaseModel):
    voice: Optional[str] = None
    speed: Optional[float] = None
    text: str = "Hello! This is a preview of the selected voice for your video narration."


@app.post("/voice/preview")
def voice_preview(body: VoicePreviewRequest):
    """Generate (or reuse) a short Kokoro preview WAV for the chosen voice."""
    cmd = [VENV_PY.as_posix() if False else str(VENV_PY), str(SCRIPTS / "generate_narration.py"), "--preview"]
    if body.voice:
        cmd += ["--voice", body.voice]
    if body.speed is not None:
        cmd += ["--speed", str(body.speed)]
    # Override the default preview text is not supported by the script; it uses its own.
    r = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW, timeout=180,
    )
    # Determine which voice was actually used (fall back to config)
    if body.voice:
        voice = body.voice
    else:
        try:
            import sys as _sys
            _sys.path.insert(0, str(SCRIPTS))
            import config as _cfg
            voice = _cfg.resolve_tts_config(_cfg.load_config(), {}).get("voice", "af_heart")
        except Exception:
            voice = "af_heart"
    rel = f"audio/preview_{voice}.wav"
    full = ROOT / rel
    if r.returncode != 0 or not full.exists():
        return {"ok": False, "error": (r.stderr or r.stdout or "preview generation failed"), "voice": voice}
    return {"ok": True, "voice": voice, "path": rel, "url": "/files/" + rel}


@app.post("/run/{job_id}/write-note")
def write_run_note_endpoint(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Unknown job")
    if job.get("status") not in ("done", "failed", "cancelled"):
        raise HTTPException(409, "Job not finished yet")
    mp4_rel = (job.get("result") or {}).get("mp4")
    cmd = [BASE_PY, str(SCRIPTS / "write_run_note.py")]
    if mp4_rel:
        cmd += ["--mp4", mp4_rel]
    elif job.get("slug"):
        cmd += ["--slug", str(job["slug"])]
    r = subprocess.run(
        cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW, timeout=120,
    )
    note_path = None
    for line in (r.stdout or "").splitlines():
        line = line.strip()
        if line.lower().startswith("run note written:"):
            note_path = line.split(":", 1)[1].strip()
            break
    rel = None
    if note_path:
        try:
            full = Path(note_path)
            if full.is_absolute():
                rel = str(full.relative_to(ROOT))
            else:
                rel = note_path
        except Exception:
            rel = note_path
    if r.returncode != 0:
        return {"ok": False, "error": (r.stderr or r.stdout or "write-run-note failed"), "output": r.stdout}
    return {"ok": True, "note": rel, "output": r.stdout}

import queue
# --- Run management (SSE-streamed) ---

import uuid

_jobs = {}  # job_id -> {status, proc, log_queue, log_history, result, error, media_dir}


from typing import Optional

# ... (other code) ...

class RunRequest(BaseModel):
    name: str
    prompt: str = ""
    media: list = []   # list of absolute file paths (optional; else reads inbox/<name>/)
    voice: Optional[str] = None
    speed: float = 1.0
    overlay: bool = True
    overlay_duration: float = 3.0
    overlay_position: str = "top"
    write_run_note: bool = False
    music: Optional[str] = None  # background music track (absolute path)


def _prepare_inbox(job_id, req):
    """Create inbox/<name>/ with prompt.txt + media files (copied). Returns (slug, inbox_dir)."""
    slug = re_slug(req.name)
    inbox_dir = ROOT / "inbox" / slug
    inbox_dir.mkdir(parents=True, exist_ok=True)
    if req.prompt.strip():
        (inbox_dir / "prompt.txt").write_text(req.prompt.strip(), encoding="utf-8")
    for m in req.media:
        src = Path(m)
        if src.exists() and src.is_file():
            dst = inbox_dir / src.name
            # Skip if source and destination are the same file
            try:
                same = src.resolve() == dst.resolve()
            except Exception:
                same = False
            if same:
                console_log(f"Skipping same-file copy: {src}", "DEBUG")
                continue
            console_log(f"Copying {src} -> {dst}", "DEBUG")
            shutil.copy2(str(src), str(dst))
    if req.music:
        try:
            src = Path(str(req.music))
            if src.is_file():
                dst = inbox_dir / src.name
                if src.resolve() != dst.resolve():
                    console_log(f"Anchoring music into inbox: {src.name}", "DEBUG")
                    shutil.copy2(str(src), str(dst))
                req.music = str(dst)
        except Exception as e:
            console_log(f"Could not anchor music into inbox: {e}", "WARN")
    return slug, inbox_dir


def re_slug(name):
    import re
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_") or "run"


def _run_worker(job_id, req):
    job = _jobs[job_id]
    q = job["log_queue"]
    history = job["log_history"]
    def _put(msg):
        q.put(msg)
        history.append(msg)
    try:
        console_log(f"Starting run: {req.name}", "INFO")
        slug, inbox_dir = _prepare_inbox(job_id, req)
        job["slug"] = slug
        console_log(f"Inbox prepared: {inbox_dir} ({len(list(inbox_dir.iterdir()))} files)", "INFO")

        # Build command
        cmd = [BASE_PY, str(SCRIPTS / "run_video.py"), slug]
        if req.voice:
            cmd += ["--voice", req.voice]
        if req.speed and req.speed != 1.0:
            cmd += ["--tts-speed", str(req.speed)]
        if req.music:
            # Defensive: coerce non-string/NaN values to a string path
            try:
                req.music = str(req.music).strip()
            except Exception:
                req.music = None
            # Skip malformed values (e.g. a leftover JS object leaked through as JSON)
            if req.music and not req.music.startswith("{") and not req.music.startswith("["):
                music_path = Path(req.music)
                if not music_path.is_file():
                    console_log(f"Music file NOT found: {req.music}", "WARN")
                    raise FileNotFoundError(f"Music file not found: {req.music}")
                console_log(f"Background music: {music_path.name}", "INFO")
                cmd += ["--music", str(music_path)]
            else:
                # Keep a diagnostic either way (malformed path leak or truly unselected)
                if req.music:
                    console_log(f"Music value ignored (not a path): {req.music}", "WARN")
                else:
                    console_log("No background music selected (skipped)", "DEBUG")
                req.music = None
        if not req.overlay:
            cmd += ["--no-overlay"]
        else:
            cmd += ["--overlay-duration", str(req.overlay_duration),
                    "--overlay-position", req.overlay_position]
        if req.write_run_note:
            cmd += ["--write-run-note"]
        cmd += ["--no-open"]

        _put({"type": "log", "line": f"Command: {' '.join(cmd)}"})
        _put({"type": "stage", "stage": "Starting pipeline"})
        proc = subprocess.Popen(
            cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        job["proc"] = proc
        for line in proc.stdout:
            line = line.rstrip("\n")
            _put({"type": "log", "line": line})
            console_log(f"[{slug}] {line}", "PIPELINE")
            # Detect stage headers
            if line.strip().startswith("[") and "]" in line:
                _put({"type": "stage", "stage": line.strip()})
        proc.wait()
        if proc.returncode != 0:
            job["status"] = "failed"
            job["error"] = f"Pipeline exited with code {proc.returncode}"
            console_log(f"Run {slug} FAILED (exit {proc.returncode})", "ERROR")
            _put({"type": "error", "message": job["error"]})
            return

        # Find the produced MP4 (most recent matching slug)
        mp4s = sorted(
            (ROOT / "output").glob(f"*_{slug}.mp4"),
            key=lambda p: p.stat().st_mtime,
        )
        mp4 = mp4s[-1] if mp4s else None
        kit = mp4.with_suffix(".publishing.json") if mp4 else None
        srt = mp4.with_suffix(".srt") if mp4 else None
        # Contact sheet (cosmetic)
        cs_matches = sorted((ROOT / "images").glob(f"contact_sheet*.jpg"), key=lambda p: p.stat().st_mtime)
        cs = cs_matches[-1] if cs_matches else None

        job["status"] = "done"
        job["result"] = {
            "mp4": str(mp4.relative_to(ROOT)) if mp4 else None,
            "size_mb": round(mp4.stat().st_size / 1_048_576, 1) if mp4 else 0,
            "kit": json.loads(kit.read_text(encoding="utf-8")) if kit and kit.exists() else None,
            "srt": str(srt.relative_to(ROOT)) if srt and srt.exists() else None,
            "contact_sheet": str(cs.relative_to(ROOT)) if cs and cs.exists() else None,
        }
        console_log(f"Run {slug} COMPLETE: {mp4.name if mp4 else 'no mp4'}", "INFO")
        _put({"type": "done"})
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        console_log(f"Run failed: {e}", "ERROR")
        _put({"type": "error", "message": str(e)})


@app.post("/run")
def start_run(req: RunRequest):
    if not req.name.strip():
        raise HTTPException(400, "Run name required")
    job_id = uuid.uuid4().hex[:8]
    _jobs[job_id] = {
        "status": "running", "proc": None, "log_queue": queue.Queue(), "log_history": [],
        "result": None, "error": None, "slug": req.name,
    }
    threading.Thread(target=_run_worker, args=(job_id, req), daemon=True).start()
    return {"job_id": job_id}


@app.get("/run/{job_id}/stream")
def run_stream(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(404, "Unknown job")
    job = _jobs[job_id]
    q = job["log_queue"]
    history = job.get("log_history", [])

    def event_gen():
        # Send history first so late-connecting clients see the initial stage
        for msg in history:
            yield f"data: {json.dumps(msg)}\n\n"
        while True:
            try:
                msg = q.get(timeout=1)
            except queue.Empty:
                if job["status"] in ("done", "failed"):
                    yield f"data: {json.dumps({'type': 'done' if job['status']=='done' else 'error', 'message': job.get('error')})}\n\n"
                    break
                yield ": keepalive\n\n"
                continue
            yield f"data: {json.dumps(msg)}\n\n"
            if msg.get("type") in ("done", "error"):
                break

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.post("/run/{job_id}/cancel")
def cancel_run(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Unknown job")
    proc = job.get("proc")
    if proc and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
    job["status"] = "cancelled"
    return {"ok": True}


@app.get("/run/{job_id}/result")
def run_result(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Unknown job")
    if job["status"] == "running":
        return {"status": "running"}
    if job["status"] in ("failed", "cancelled"):
        return {"status": job["status"], "error": job.get("error")}
    return {"status": "done", **(job["result"] or {})}


@app.get("/run-by-name/{stem}/result")
def run_by_name_result(stem: str):
    """Result payload for an existing output/*.mp4 (History screen "View")."""
    if "/" in stem or "\\" in stem or ".." in stem:
        raise HTTPException(400, "Invalid run name")
    mp4 = ROOT / "output" / f"{stem}.mp4"
    if not mp4.exists():
        raise HTTPException(404, "Run not found")
    kit = mp4.with_name(mp4.stem + ".publishing.json")
    srt = mp4.with_name(mp4.stem + ".srt")
    cs_matches = sorted((ROOT / "images").glob("contact_sheet*.jpg"), key=lambda p: p.stat().st_mtime)
    cs = cs_matches[-1] if cs_matches else None
    return {
        "status": "done",
        "mp4": str(mp4.relative_to(ROOT)),
        "size_mb": round(mp4.stat().st_size / 1_048_576, 1),
        "kit": json.loads(kit.read_text(encoding="utf-8")) if kit.exists() else None,
        "srt": str(srt.relative_to(ROOT)) if srt.exists() else None,
        "contact_sheet": str(cs.relative_to(ROOT)) if cs and cs.exists() else None,
    }


@app.get("/runs")
def list_runs():
    runs = []
    for mp4 in sorted((ROOT / "output").glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True):
        runs.append({"name": mp4.stem, "path": str(mp4.relative_to(ROOT)), "size_mb": round(mp4.stat().st_size / 1_048_576, 1)})
    return {"runs": runs[:20]}


@app.get("/files/{file_path:path}")
def serve_file(file_path: str):
    full = ROOT / file_path
    if not full.exists() or not full.is_file():
        raise HTTPException(404, "File not found")
    # Safety: ensure within ROOT
    try:
        full.resolve().relative_to(ROOT.resolve())
    except ValueError:
        raise HTTPException(403, "Forbidden")
    return FileResponse(str(full))


# --- Inbox details (for re-run) ---

@app.get("/inbox/{name}")
def inbox_details(name: str):
    import re
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
    inbox_dir = ROOT / "inbox" / slug
    if not inbox_dir.exists():
        # Try to find by partial match
        matches = [d for d in (ROOT / "inbox").iterdir() if d.is_dir() and slug.lower() in d.name.lower()]
        if matches:
            inbox_dir = matches[0]
            slug = inbox_dir.name
        else:
            raise HTTPException(404, f"Inbox folder not found: {name}")
    prompt = ""
    prompt_path = inbox_dir / "prompt.txt"
    if prompt_path.exists():
        prompt = prompt_path.read_text(encoding="utf-8").strip()
    media = sorted(
        [str(p) for p in inbox_dir.iterdir() if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".mpg", ".mpeg", ".flv", ".wmv", ".gif")],
        key=lambda x: Path(x).name.lower(),
    )
    return {"name": slug, "prompt": prompt, "media": media, "media_names": [Path(m).name for m in media]}

@app.post("/pick-files")
def pick_files():
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    files = filedialog.askopenfilenames(
        title="Select media files (images, clips, GIFs)",
        filetypes=[
            ("Media files", "*.png *.jpg *.jpeg *.webp *.mp4 *.mov *.mkv *.avi *.webm *.m4v *.mpg *.mpeg *.flv *.wmv *.gif"),
            ("All files", "*.*"),
        ],
    )
    root.destroy()
    return {"files": list(files)}


@app.post("/pick-music")
def pick_music():
    """Backend fallback single-file dialog for background music."""
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    files = filedialog.askopenfilename(
        title="Select background music track",
        filetypes=[
            ("Audio files", "*.mp3 *.wav *.m4a *.flac *.ogg *.aac *.opus *.aiff"),
            ("All files", "*.*"),
        ],
    )
    root.destroy()
    return {"file": str(files) if files else ""}


# --- Loop doctor ---

@app.post("/doctor")
def run_doctor():
    try:
        r = subprocess.run(
            [BASE_PY, str(SCRIPTS / "loop_doctor.py")],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return {"output": (r.stdout or "") + (r.stderr or ""), "exit_code": r.returncode}
    except Exception as e:
        return {"output": str(e), "exit_code": 1}


class FolderRequest(BaseModel):
    path: str


@app.post("/open-folder")
def open_folder(body: FolderRequest):
    """Launch Windows Explorer at a directory inside ROOT (no browser fallback)."""
    try:
        full = (ROOT / body.path).resolve() if not Path(body.path).is_absolute() else Path(body.path).resolve()
    except Exception:
        raise HTTPException(400, "Invalid path")
    try:
        full.relative_to(ROOT.resolve())
    except ValueError:
        raise HTTPException(403, "Path outside workspace")
    if not full.exists() or not full.is_dir():
        raise HTTPException(404, "Folder not found")
    try:
        subprocess.Popen(["explorer", str(full)], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        raise HTTPException(500, f"Failed to open folder: {e}")
    return {"ok": True, "path": str(full)}


@app.get("/download/{file_path:path}")
def download_file(file_path: str):
    """Serve a file with an attachment disposition so browsers/pywebview download it."""
    full = ROOT / file_path
    if not full.exists() or not full.is_file():
        raise HTTPException(404, "File not found")
    try:
        full.resolve().relative_to(ROOT.resolve())
    except ValueError:
        raise HTTPException(403, "Forbidden")
    return FileResponse(str(full), filename=full.name, headers={"Content-Disposition": f'attachment; filename="{full.name}"'})


@app.get("/")
def index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "ReelForge UI backend. Frontend not yet built."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
