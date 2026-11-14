# ReelForge --- Local AI Video Pipeline

ReelForge turns a topic into a publish-ready vertical MP4 (1080x1920)
entirely on your own machine: scenes -> attached media -> local Kokoro
narration -> subtitles -> FFmpeg assembly -> QA.

## Start here (ICM layered context)

Read in this order; load only what the task needs.

1.  `CLAUDE.md` --- Layer 0, always.
2.  `_core/CONTEXT.md` --- Layer 1, task router + stage map + gates.
3.  `pipeline/NN-<stage>/CONTEXT.md` --- Layer 2, only the stage you touch.
4.  `_config/` --- canonical voice / paths / QA thresholds.

`PROJECT_CONTEXT.md` and `OPENCODE_TASK.md` are **historical snapshots**,
superseded by the ICM layers above.

## Quick start (desktop app)

1.  Run `build_ui.bat` to build the app, then launch
    `dist\ReelForge\ReelForge.exe`.
2.  In **New Run**, add scenes (narration, overlay text, duration), attach
    media per scene, then press **Start Run**.
3.  The MP4 lands in `output\`. Full behavior and flags: `SETUP.md`.

## Quick start (headless / CLI)

```
python scripts\run_video.py --name <slug> --scenes <scenes.json> --media <file> [<file> ...]
```

`scenes.json` is a list of scenes: `scene_number`, `narration_segment`,
`on_screen_text`, `duration_seconds`, optional `media_path`. The desktop
UI writes exactly this file and invokes the same script.

## Audits

-   `python scripts\loop_doctor.py` --- environment / prerequisite health.
-   `python scripts\verify_docs.py` --- ICM doc/code drift check.
-   `python scripts\verify_images.py`, `verify_subtitles.py` --- stage gates.

## Files

-   `CLAUDE.md`, `_core/`, `_config/`, `pipeline/` --- the live ICM context.
-   `gate.yaml` --- machine-readable thresholds **enforced** by the QA stage.
-   `config.json` --- runtime config for LLM provider/model/endpoint and TTS
    voice/speed (gitignored; contains secrets).

