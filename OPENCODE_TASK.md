# OpenCode Agent Task --- ReelForge

## Objective

Continue the existing local AI video-production project using
`PROJECT_CONTEXT.md` and the ICM layers (`_core/`, `_config/`,
`pipeline/*/CONTEXT.md`, `CLAUDE.md`).

The intended coding-agent model is the user's local Qwythos 9B V2 MTP
GGUF model:

`empero-ai/qwythos-9b-v2-gguf/qwythos-9b-v2-mtp-q4_k_m.gguf`

Do not assume OpenCode's provider/model configuration is complete
without inspecting it. Do not change the model configuration unless
requested.

## Current task

First video approved and upload-ready. Task 8 one-click orchestrator is
built and QA-tested (PROJECT_CONTEXT.md section 6.7). ICM integration
layer (documentation-only) + Obsidian vault + local Graphify graph are
now in place.

1.  **First live validation of the storyboard path.** Closed: live Qwythos/LM Studio storyboard run completed successfully (stamp 20261108_030815, slug webdev21; QA passed, 21.0s).

2.  **User-side:** upload `output\20261107_1552_How_black_holes_work.mp4`
    to Facebook Reels / YouTube Shorts. Capture exact error text if
    rejected.

3.  **Optional:** refresh the knowledge graph after code changes with
    `scripts\graph_rebuild.bat`.

Status updates (2026-11-08): item 1 closed (webdev21 live run passed); items 2 and 3 waived by user (not needed / not priority); item 5 desktop UI implementation approved and in progress; environment readiness verified via loop_doctor.py.
## Assets for the current approved production

-   Image manifest + metadata:
    `E:\AI-Video-Production\images\approved_set.json`
-   Storyboard (revised narration + durations 9/9/9.5/10/9/9.5):
    `E:\AI-Video-Production\output\20261107_123353_How_black_holes_work.json`
-   Narration: `audio\scene_01.wav` ... `scene_06.wav` + sidecars
-   Subtitles: `subtitles\how_black_holes_work.srt` (burned + side-load)
-   Final video: `output\20261107_1552_How_black_holes_work.mp4`
-   Publishing kit:
    `output\20261107_1552_How_black_holes_work.publishing.json`
-   Orchestrator: `scripts\run_video.py` + `make_video.bat`
-   ICM layers: `_core/`, `_config/`, `pipeline/*/CONTEXT.md`, `CLAUDE.md`
-   Vault: `vault/` (Obsidian PARA). Graph: `graphify-out/`

## Constraints

-   Do not regenerate approved images, narration, or subtitles without
    a demonstrated reason; preserve the archive-first behavior of the
    orchestrator (nothing ever deleted).
-   Python 3.11.9 at `E:\ai\AirLLM\py3.11.9\python.exe` for
    verification; `E:\AI-Video-Production\venv-tts` only for TTS work
    (narration + assembly run through it).
-   ffmpeg CLI changes in v9: `-/filter_complex <file>` instead of the
    removed `-filter_complex_script`; `-fps_mode` instead of `-vsync`.
-   Do not install extra packages; everything runs on the validated
-   Qwythos must not share the 8 GB GPU with Stable Diffusion; the
-   ICM layered context: read `_core/CONTEXT.md` then only the stage
    CONTEXT.md you need. Do not load everything.