# ReelForge --- Setup Instructions

Setup requirements and operating guide for the local AI
video-production pipeline: **topic → storyboard → scene images →
narration → subtitles → animated 1080×1920 MP4**, all locally hosted
(no paid APIs, no cloud services).

Tested end-to-end on the machine described in section 2; first
production: `How Black Holes Work` (56 s, approved 2026-11-07).

---

## 1. Requirements at a glance

| Requirement      | Minimum                                             | This project (verified working)            |
|------------------|-----------------------------------------------------|---------------------------------------------|
| OS               | Windows 10/11 64-bit                                | Windows 11 Pro, build 22631                 |
| GPU**            | NVIDIA, ≥6 GB VRAM (Stable Diffusion 1.5)           | NVIDIA RTX 4060, 8 GB VRAM, driver 616.92   |
| CPU              | 6+ cores (helps FFmpeg encode/render)               | AMD Ryzen 7 5700X (8C/16T)                  |
| RAM              | 16 GB                                               | 32 GB                                       |
| Free disk*       | ≈25 GB (models + venvs + assets), on a fast local drive | Drive E: dedicated to models and assets  |
| Internet         | Required only during installation                   | Nothing downloads at runtime (weights cached on E:) |
| Python           | 3.11.x + 3.13.x available                           | 3.11.9 at `E:\ai\AirLLM\py3.11.9\python.exe`, 3.13.7, 3.15.2 |
| TTS              | Kokoro-82M runs **on CPU** — no VRAM needed         | kokoro 0.9.4 + torch 2.15.0 (CPU) in venv   |

SD 1.5 checkpoint ≈ 4.3 GB, Kokoro venv + weights ≈ 1.8 GB, assets
< 0.5 GB. Keep all models/assets on E: per project rule.

\** TTS stage needs no GPU. Image generation can technically run on
CPU but is impractically slow.

---

## 2. Hardware profile used for validation

- Windows 11 Pro, build 22631
- AMD Ryzen 7 5700X, 8 cores / 16 threads
- NVIDIA RTX 4060, 8 GB VRAM, driver 616.92
- 32 GB RAM

---

## 3. Required software components

| Component                         | Version tested | Where it lives in this project |
|-----------------------------------|----------------|--------------------------------|
| Python (base)                     | 3.11.9         | `E:\ai\AirLLM\py3.11.9\python.exe` |
| LM Studio + Qwythos model         | LM Studio current | Model file: `empero-ai/qwythos-9b-v2-gguf/qwythos-9b-v2-mtp-q4_k_m.gguf` |
| SD 1.5 checkpoint                 | v1-5-pruned-emaonly | `E:\ai\Stable Diffusion\webui\models\Stable-diffusion\v1-5-pruned-emaonly.safetensors` |
| FFmpeg / ffprobe                  | 9.0.2          | on system PATH (CLI changed in v9 — see section 9) |
| eSpeak NG                         | 1.52.0         | `C:\Program Files\eSpeak NG\` (system PATH) |
| Kokoro TTS venv                   | kokoro 0.9.4   | `E:\AI-Video-Production\venv-tts` |
| Kokoro model weights (auto-download) | v1.0, 82M params | `E:\AI-Video-Production\models\huggingface` (≈313 MB) |

use the Python standard library only — do **not** install Pillow).

---

## 4. Project workspace layout

```
E:\AI-Video-Production\
├─ PROJECT_CONTEXT.md      ← handoff context (keep current)
├─ OPENCODE_TASK.md        ← current task for the agent
├─ SETUP.md                ← this file
├─ scripts\                ← pipeline scripts (see section 7)
├─ models\huggingface\     ← Kokoro weights (HF_HOME cache)
├─ output\                 ← storyboards, MP4s, publishing kits
│   └─ archive\            ← superseded storyboards/renders
├─ images\                 ← scene PNGs + metadata + manifest
│   └─ archive\            ← rejected/superseded images
├─ audio\                  ← narration WAVs + metadata
│   └─ archive\
├─ subtitles\              ← SRT
├─ temp\                   ← filter graphs, QA frames
├─ venv-tts\               ← dedicated TTS virtualenv
├─ contacts/               (not used; contact sheets live in images\)
├─ clips\, logs\, workflows\  ← reserved
```

---

## 5. Component installation

### 5.1 Python 3.11.9

Confirmed at `E:\ai\AirLLM\py3.11.9\python.exe`. Verify:

```powershell
& 'E:\ai\AirLLM\py3.11.9\python.exe' --version   # Python 3.11.9
```

### 5.2 FFmpeg 9.0.2

On PATH (`ffmpeg -version`). FFmpeg 9 changed two CLI flags that the
pipeline scripts rely on (see section 9):

| Removed in v9             | Replacement in v9                |
|---------------------------|----------------------------------|
| `-filter_complex_script`  | `-/filter_complex <file>`        |
| `-vsync`                  | `-fps_mode`                      |

### 5.3 eSpeak NG 1.52.0

Installed to `C:\Program Files\eSpeak NG\` and added to the **system**
PATH. It is the phonemizer fallback for Kokoro/misaki.

Verify in a **new** terminal:

```powershell
espeak-ng --version
# eSpeak NG text-to-speech: 1.52.0  Data at: C:\Program Files\eSpeak NG\/espeak-ng-data
```

Note: a shell that was open *before* the PATH update keeps a stale
PATH. New terminals pick it up automatically; agent sessions can
refresh with:

```powershell
$env:PATH = [Environment]::GetEnvironmentVariable('PATH','Machine') + ';' +
            [Environment]::GetEnvironmentVariable('PATH','User') + ';' + $env:PATH
```

### 5.4 LM Studio + Qwythos 9B V2 MTP GGUF

1. Install LM Studio, download the model
   `empero-ai/qwythos-9b-v2-gguf/qwythos-9b-v2-mtp-q4_k_m.gguf`.
2. Start LM Studio's local server (API at `http://127.0.0.1:1234/v1`).
3. Needed only for **storyboard generation** stage.

Known cosmetic issue: `generate_video_idea.py` prints "Qwen" in its
progress text while actually configured for Qwythos — label only.


Install at `E:\ai\Stable Diffusion\webui`. Startup file
`webui-user.bat` must contain:

```bat
@echo off
set PYTHON=E:\ai\AirLLM\py3.11.9\python.exe
set GIT=
set VENV_DIR=E:\ai\Stable Diffusion\webui\venv
set COMMANDLINE_ARGS=--api --medvram
call webui.bat
```

lets an 8 GB GPU coexist with desktop load. Launch with

```powershell
# v1-5-pruned-emaonly
```

### 5.6 Kokoro TTS venv (one-time, ≈10 min)

```powershell
& 'E:\ai\AirLLM\py3.11.9\python.exe' -m venv 'E:\AI-Video-Production\venv-tts'
& 'E:\AI-Video-Production\venv-tts\Scripts\python.exe' -m pip install --upgrade pip
& 'E:\AI-Video-Production\venv-tts\Scripts\python.exe' -m pip install kokoro soundfile
```

Installed stack: `kokoro 0.9.4`, `torch 2.15.0` (CPU build on Windows),
`misaki 0.9.4` (G2P), `transformers`, `spacy`, `espeakng-loader`,
`soundfile`, `huggingface-hub`.

First run downloads the model weights into `HF_HOME`
(section 6) and auto-installs spaCy's `en_core_web_sm`
(12.8 MB) into the venv. Weight cache: ≈313 MB.

Test (`scripts\test_kokoro.py` does exactly this):

```powershell
& 'E:\AI-Video-Production\venv-tts\Scripts\python.exe' 'E:\AI-Video-Production\scripts\test_kokoro.py'
# → audio\test_kokoro_af_heart.wav (~5.9 s clip, CPU, faster than real time)
```

---

## 6. Environment variables

| Variable  | Value (required)                                  | Why |
|-----------|---------------------------------------------------|-----|
| `HF_HOME` | `E:\AI-Video-Production\models\huggingface`       | Keeps model weights on E:, never C: (project rule). All pipeline scripts set this internally. |
| `HF_HUB_DISABLE_SYMLINKS_WARNING` | `1` (optional) | Silences the harmless Windows symlink warning. |
| system PATH | must contain `C:\Program Files\eSpeak NG\` and FFmpeg | espeak-ng / ffmpeg discovery |

---

## 7. Pipeline scripts and how to run them

All scripts live in `E:\AI-Video-Production\scripts\`. Run from
anywhere; paths are absolute internally. Read `images\approved_set.json`
first to understand the current production's stage mapping.

⚠️ **Per-video wiring:** the scripts are wired to the first production
(`How Black Holes Work`):
`generate_scene_images.py` has a `STORYBOARD` constant pointing at
`output\20261107_123353_How_black_holes_work.json`, and
`generate_narration.py` / `generate_subtitles.py` /
`assemble_video.py` read `images\approved_set.json`. For a new topic:
generate the new storyboard with step 1, point the script's storyboard
constant at it, and rebuild the approved-image manifest after image
review. Full per-topic automation is the planned Task 8 orchestrator.

### Stage 1 — Storyboard (needs LM Studio running)

```powershell
& 'E:\ai\AirLLM\py3.11.9\python.exe' 'E:\AI-Video-Production\scripts\generate_video_idea.py' "your topic here"
```

- Topic may also be omitted (interactive prompt).
- Validates exactly 6 scenes and total 45–60 s; writes
  `output\YYYYMMDD_HHMMSS_Topic.json` with per-scene narration, image
  prompts, motion directions, fact-check notes, source suggestions.
- **Human step:** fact-check/revise narration in the JSON (see the
  required caveats pattern used for the first video in
  `PROJECT_CONTEXT.md` §6.2).


```powershell
& 'E:\ai\AirLLM\py3.11.9\python.exe' 'E:\AI-Video-Production\scripts\generate_scene_images.py'
# flags:
#   --scenes 5 | 3-6 | 3,5,6    (default 3-6)
#   --suffix v2                 (default v2 → scene_XX_v2.png)
#   --seed 22350                (default 12345 + scene number)
```

  22 steps, CFG 6.5, DPM++ 2M.
- Writes PNG + `<name>_metadata.json` per scene.
- Prompt overrides for scenes 3–6 and a scene-5 negative override
  enforce the science constraints (no white-dot singularity, nothing
  escapes the horizon, obvious lensing).
- Never overwrite approved files until replacements are verified;
  rejected candidates go to `images\archive\`.

Contact sheet for review (3×2 grid, full 512×768 tiles):

```powershell
ffmpeg -y -i images\scene_01.png -i images\scene_02.png -i images\scene_03.png `
 -i images\scene_04.png -i images\scene_05.png -i images\scene_06.png `
 -filter_complex "[0:v][1:v][2:v]hstack=inputs=3[top];[3:v][4:v][5:v]hstack=inputs=3[bot];[top][bot]vstack=inputs=2" `
 -frames:v 1 -q:v 2 images\contact_sheet.jpg
```

(Harmless "image sequence pattern" warning may appear; the JPG is
written correctly.)

After approval, `images\approved_set.json` maps each scene to its
approved PNG + metadata; downstages read from this manifest.

### Stage 3 — Narration (CPU only; no services needed)

```powershell
& 'E:\AI-Video-Production\venv-tts\Scripts\python.exe' 'E:\AI-Video-Production\scripts\generate_narration.py'
```

- Voice `af_heart` (en-US), speed 1.0, 24 kHz mono, peak-normalized to
  0.89 (−1 dBFS) for music headroom.
- Writes `audio\scene_XX.wav` + `scene_XX_metadata.json` (includes the
  per-scene duration used later for subtitle timing).
- Deterministic: same text/voice/speed → same durations.
- Report flags `[LONG]` when a segment exceeds its scene slot minus
  0.5 s — then either trim the line or extend that scene's duration in
  the storyboard/manifest (first video used 9/9/9.5/10/9/9.5 s).

### Stage 4 — Subtitles (CPU only)

```powershell
& 'E:\ai\AirLLM\py3.11.9\python.exe' 'E:\AI-Video-Production\scripts\generate_subtitles.py'
& 'E:\ai\AirLLM\py3.11.9\python.exe' 'E:\AI-Video-Production\scripts\verify_subtitles.py'
```

- Reads narration from the manifest + measured durations from the
  audio sidecars; narration starts 0.4 s after each scene start.
- Two cues per scene, split at natural pauses with char-proportional
  timing; the script **fails if the cue texts do not reproduce the
  narration wording exactly**.
- Output: `subtitles\how_black_holes_work.srt`.

### Stage 5 — Assembly (CPU only; ≈20–25 s)

```powershell
& 'E:\AI-Video-Production\venv-tts\Scripts\python.exe' 'E:\AI-Video-Production\scripts\assemble_video.py'
```

- Per scene: 512×768 → lanczos upscale 2560×3840 → 9:16 center crop →
  `zoompan` Ken Burns (motion per storyboard `motion_direction`) →
  1080×1920. Never stretches.
- 0.5 s crossfades at scene boundaries, 0.5 s fade-in/out, exactly the
  manifest total timeline.
- Narration segments delayed to `scene_start + 0.4 s`, mixed to 48 kHz
  stereo; subtitles burned in (Arial 15, white/black outline,
  bottom-center, mobile-safe MarginV=36) with preflight check.
- Encodes libx264 CRF 18 `-pix_fmt yuv420p` + faststart →
  `output\YYYYMMDD_HHMM_How_black_holes_work.mp4`.
- Superseded renders → `output\archive\`.

### Stage 6 — QA

```powershell
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,profile,pix_fmt,width,height,r_frame_rate,nb_frames,duration -of default=noprint_wrappers=1 <mp4>
ffmpeg -i <mp4> -map 0:a:0 -af volumedetect -f null -
ffmpeg -y -i <mp4> -vf "select='eq(n\,600)'" -fps_mode passthrough -frames:v 1 temp\qa_frame.png
```

Targets: 56 s (45–60 allowed), 1080×1920, 30 FPS, H.264 **yuv420p**,
AAC stereo, max volume ≈ −1.0 dB (no clipping), caption placement and
composition in the grabs. Publishing kit template:
`output\20261107_1552_How_black_holes_work.publishing.json`.

---

## 8. Runtime services per stage (who must be running)

|---------------------------|----------------------|-------------------|----------|
| Storyboard generation     | **Required**         | off is fine       | Optional (model loaded on GPU speeds it; unload afterwards) |
| Scene image generation    | **Not loaded on GPU** | **Required**     | Yes (~2 GB free needed) |
| Narration / subtitles     | Not required         | Not required      | No (CPU) |
| Assembly / QA             | Not required         | Not required      | No (CPU) |

**VRAM rule:** Qwythos and Stable Diffusion must not share the 8 GB
GPU simultaneously. Before image generation, unload/eject the model
in LM Studio or quit it. Kokoro never uses the GPU by design.

---

## 9. Known issues and gotchas

1. **FFmpeg 9 CLI renames**: `-filter_complex_script` →
   `-/filter_complex <file>`; `-vsync` → `-fps_mode passthrough…`.
   Older tutorials/StackOverflow answers are wrong for v9.
2. **PATH staleness in open shells** after installing eSpeak NG.
3. **HF symlink warning** on Windows is harmless (weights still cache).
4. **misaki auto-installs** `en_core_web_sm` into the venv on first
   narration run — expected.
5. **"Qwen" label** in the storyboard script output — cosmetic only.
6. **Do not install Pillow** or extra packages "just in case";
   verification uses the standard library (`verify_images.py`,
   `verify_subtitles.py`).
7. **Don't run stages concurrently** that compete in VRAM (rule above);
   the 8 GB card can hold SD 1.5 with ~2 GB headroom.
8. Wait for user review checkpoints (images contact sheet, narration
   voice test, final MP4) — the pipeline is explicitly
   human-in-the-loop at those three points.

---

## 10. One-click pipeline (Task 8 orchestrator)

For new videos, skip the manual stage commands from section 7:

1.  Create `inbox\<video-name>\`.
2.  Add `prompt.txt` (the topic/story) **and 1--12 media files**
    (images png/jpg/jpeg/webp, video clips mp4/mov/mkv/avi/webm/m4v/mpg/mpeg/flv/wmv,
    or animated GIFs; filename order = scene order).
3.  Double-click `make_video.bat` and type the folder name (or run
    `python scripts\run_video.py <video-name>`).
4.  ~3--5 min later: `output\<stamp>_<name>.mp4` + a `.publishing.json`
    kit + `.srt` sidecar; Explorer opens at the finished MP4.

Behavior worth knowing:

-   LM Studio (Qwythos loaded, server on 1234) is the only service that
    attached media (images, clips, GIFs) ARE the scenes.
-   Video clips and GIFs are normalized to 1080x1920/30fps and trimmed
    to the scene duration; shorter clips freeze on their last frame
    (GIFs play once, then freeze). Images keep the Ken Burns motion.
-   Previous `images\`, `audio\`, `subtitles\` working files are moved
    into their `archive\` folders with a stamp prefix (never deleted).
-   Image inputs are normalized to 512x768 with scale+crop (never
    stretched) and `images\approved_set.json` is rebuilt from the
    storyboard; a contact sheet is saved for the record.
-   Scene durations auto-fit to the measured narration (narration +
    0.9 s, rounded up to 0.5 s) --- so the final timeline can be longer
    than the storyboard's initial durations; totals outside 45--60 s
    log a WARNING but still render.
-   Subtitles: two cues per scene from automatic midpoint-punctuation
    splits (the hand-picked SPLITS overrides still win when their
    wording matches), and wording is hard-verified before assembly.
-   QA gates before publish: 1080x1920, h264 yuv420p, aac, duration
    equals the timeline, max_volume <= -0.3 dB. Failures abort with the
    stage and fix shown; full log in `logs\<stamp>_<name>.log`.
-   Useful flags: `--storyboard <json>` reuses an existing storyboard
    (LM Studio not needed; ideal for narration/subtitle re-runs),
    `--no-open` suppresses Explorer.

## 11. LLM and voice configuration

The LLM (storyboard) and TTS voice are now configurable via
`config.json` (project root) or CLI flags, instead of being hardcoded.

### LLM (storyboard generation)

- Provider presets: lmstudio (default), ollama, vllm, llamacpp, openai,
  openrouter, groq, together, custom.
- CLI: `--llm <provider>`, `--llm-url`, `--llm-model`, `--llm-key`,
  `--temperature`, `--max-tokens`, `--timeout`, `--list-models`,
  `--system-prompt-file`.
- Cloud providers are opt-in (data leaves the machine; costs apply).
  Prefer local per project rules.
- API keys: prefer env vars (OPENAI_API_KEY etc.); config stores env name,
  never the secret in logs.

### Voice (Kokoro TTS)

- 28 English voices available (US 'a' + British 'b' prefixes).
- CLI: `--voice <code>`, `--speed`, `--list-voices`, `--preview`.
- Preview: `python scripts\\generate_narration.py --preview --voice bf_emma`
  writes `audio/preview_bf_emma.wav`.
- Kokoro is English-only (no Filipino). Changing voice changes durations;
  auto-fit in run_video.py handles it.

### Files
- `config.json` — runtime config (gitignored; contains secrets).
- `scripts/config.py` — loader + resolver (stdlib only).
- `scripts/llm_client.py` — OpenAI-compatible client (stdlib only).

## 12. Desktop UI (pywebview)

The pipeline can also be driven from a desktop window:

    python ui.py

Or package it: `build_ui.bat` (requires PyInstaller).

Features: service health, new-run form with file picker, live SSE progress,
result viewer (MP4 + SRT + publishing kit), settings (form + JSON),
history with re-run, loop doctor. Same backend as headless mode.

Stack: pywebview (Edge WebView2) + FastAPI + Tailwind/HTMX/Alpine.js.
Bundle: ~30-45 MB (FFmpeg and model weights NOT bundled).

```powershell
# 1. Python base
& 'E:\ai\AirLLM\py3.11.9\python.exe' --version
# 2. FFmpeg 9
ffmpeg -version
# 3. eSpeak NG (new terminal)
espeak-ng --version
# 4. LM Studio API (server started, model loaded)
(Invoke-RestMethod 'http://127.0.0.1:1234/v1/models').data.id
# 6. TTS venv
& 'E:\AI-Video-Production\venv-tts\Scripts\python.exe' -c "import kokoro, torch, soundfile; print('kokoro OK, torch', torch.__version__)"
# 7. VRAM headroom
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
# 8. End-to-end: run stages 1→6 in order, following section 7
```

All green → the pipeline reproduces the full video production
locally, stage by stage, with the human checkpoints in place.
