# UI Design — Desktop Application (pywebview + FastAPI + Tailwind)

Status: APPROVED — implementation in progress (2026-11-08). Design approved by user; backend/frontend skeleton already present and passes compile checks.
Stack: pywebview (Edge WebView2) + FastAPI + Tailwind/HTMX, packaged with
PyInstaller/Nuitka (~30-45 MB). Heavy work stays in Python subprocesses.

## 1. Goals
- Wrap the existing headless pipeline in a user-friendly desktop window.
- Zero functionality loss: same stages, flags, archive-first semantics, QA gates.
- Small bundle/memory; no Electron, no Chromium bundled.
- Long jobs (3-5 min) never block the UI.

## 2. Architecture
```
[pywebview window (Edge WebView2)]
        <-> http://127.0.0.1:<port> (FastAPI, localhost only)
[Python backend: pipeline orchestrator + service probes + job queue]
        <-> subprocess / threads
```
- One uvicorn process hosts FastAPI; pywebview opens it in a native window.
- Pipeline runs in a background worker (subprocess or thread); UI subscribes via SSE.
- Cancel = terminate the worker process tree.

## 3. Screens
2. **New Run** — inbox folder picker (or create new), drag-and-drop media (images/clips/GIFs), prompt.txt editor, scene count (auto from file count), voice dropdown (with preview), LLM dropdown (with --list-models), overlay toggles, "Start".
3. **Run Progress** — stage list with live status, SSE log tail, progress bar, cancel button, ETA.
4. **Run Result** — inline MP4 player, SRT preview, publishing-kit viewer, "Open folder", "Write run note" button.
5. **Settings** — config.json editor (paths, voice, LLM, subtitle style), "Reset to defaults", "Run loop_doctor".
6. **History** — Obsidian vault notes list, re-run, compare runs.

## 4. Backend API (FastAPI)
- `GET /config` / `PUT /config` — read/write config.json
- `GET /models` — proxy --list-models
- `GET /voices` — proxy --list-voices
- `POST /voice/preview` — generate preview WAV
- `POST /run` — start a run (body: slug, prompt, media paths, voice, llm, overlay opts); returns job_id
- `GET /run/{job_id}/stream` — SSE: stage, log lines, progress, done/error
- `POST /run/{job_id}/cancel` — kill worker
- `GET /run/{job_id}/result` — mp4 path, kit, srt
- `GET /runs` — list past runs (from vault/ + output/)
- `POST /run/{job_id}/write-note` — invoke write_run_note.py

## 5. Frontend (HTMX + Tailwind)
- No Node build step. HTMX for partial updates, SSE via `htmx-ext-sse`.
- Tailwind via CDN (dev) or a single compiled CSS (prod, ~10 KB).
- Alpine.js for small client state (dropdowns, toggles).
- Total frontend bundle: < 500 KB.

## 6. Non-functional requirements
1. SSE progress stream (jobs last 3-5 min; UI must never freeze).
2. Job queue: one run at a time; kill tree on cancel.
3. Service health panel with green/red dots.
4. Preview surfaces: contact sheet, per-scene media, inline MP4, SRT text.
5. Log tail viewer (stream logs/<stamp>_<slug>.log).
6. Config persisted to config.json with "Reset to defaults".

## 7. Packaging
- PyInstaller `--onefile` or Nuitka. Bundle only Python runtime + FastAPI/uvicorn/pywebview.
- Do NOT bundle FFmpeg (on PATH) or model weights (cached on E:).
- Expected bundle: ~30-45 MB (pywebview) or ~15-25 MB (Tauri alternative).

## 8. Loop-engineering gates (L1->L2->L3)
- L1: UI feature designed + reviewed (this doc).
- L2: implemented + manual test on real topic.
- L3: shipped only after 2 passing end-to-end runs on real topics (verifier = QA gates).
- Anti-patterns: don't run pipeline in UI thread, don't block on long jobs, don't bundle FFmpeg.

## 9. Implementation order (small, testable commits)
1. FastAPI backend skeleton + /health + /config (no UI).
2. pywebview shell + dashboard screen.
3. New Run screen + file picker + SSE progress.
4. Run Result screen + previews.
5. Settings screen.
6. History screen.
7. Packaging (PyInstaller) + installer.

## 10. Open questions
1. pywebview vs Tauri (bundle size vs dev ergonomics)? Recommend pywebview.
2. Should the UI replace make_video.bat or coexist? Recommend coexist (bat stays for headless/CI).
3. Single-window or multi-window? Recommend single window with tabs.
4. Auto-update mechanism? Recommend none in v1 (manual download).