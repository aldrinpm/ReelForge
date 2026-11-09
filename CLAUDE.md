# ReelForge — Agent Entry Point (ICM Layer 0)

You are working in `E:\AI-Video-Production`, a local AI video-production pipeline
(topic → storyboard → scene images → narration → subtitles → animated 1080x1920 MP4).

## Read order (layered context — do not load everything)

1. This file (Layer 0) — always.
2. `_core/CONTEXT.md` (Layer 1) — task router, stage map, checkpoints, audits.
3. `pipeline/NN-<stage>/CONTEXT.md` (Layer 2) — only the stage you are working on.
4. `pipeline/NN-<stage>/references/` and artifacts (Layers 3-4) — selectively, per the
   stage's Inputs table.

Do NOT load the entire `PROJECT_CONTEXT.md` or all stage contracts at once.

## Project rules (non-negotiable)

- Prefer free, locally hosted models and open-source software. No paid APIs/cloud by default.
- Keep all models/assets/artifacts on drive E:.
- Python 3.11.9 at `E:\ai\AirLLM\py3.11.9\python.exe` for verification; `venv-tts` only for TTS.
- Do not install packages without demonstrating need (Pillow must not be installed).
- Qwythos (LM Studio GPU) and Stable Diffusion image gen must never run concurrently on the 8 GB GPU.
- Kokoro TTS is CPU-only.
- Storyboard model: Qwythos 9B V2 MTP GGUF. Do not change OpenCode model config unless requested.
- Human approval checkpoints: image set, narration voice, final MP4.
- Never delete superseded artifacts — archive them (images\archive\, audio\archive\, output\archive\).
- FFmpeg 9 CLI: `-/filter_complex <file>` (not `-filter_complex_script`), `-fps_mode` (not `-vsync`).

## Long-term memory

- `vault/` (Obsidian PARA) — run notes, learnings, templates.
- `graphify-out/` — queryable knowledge graph (local OSS). Regenerate with `scripts/graph_rebuild.bat`.

## Current handoff

- `OPENCODE_TASK.md` — current task for the agent (transitional; content migrating into ICM layers).
- `PROJECT_CONTEXT.md` — full context index (transitional).
- `SETUP.md` — setup/requirements and per-stage operating guide.

## First action

Read `_core/CONTEXT.md`, then the stage CONTEXT.md for the task at hand. If the task is
unclear, ask the user. Do not start implementation without design approval when the task
is a new feature (per OPENCODE_TASK.md workflow).