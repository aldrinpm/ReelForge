# Layer 1 — Task Router (ICM)

Read this after CLAUDE.md (Layer 0). Then read only the stage CONTEXT.md for the
stage you are working on. Do NOT load everything.

## Pipeline stages (numbered = execution order)

| # | Stage | Script | Inputs | Outputs | Checkpoint |
|---|-------|--------|--------|---------|------------|
| 01 | Storyboard | (desktop UI) or `--scenes` JSON | user-defined scenes | in-memory scene list | — |
| 02 | Images | scripts/run_video.py (auto) | user media + scenes | images/scene_XX.png + metadata + approved_set.json | Contact sheet review (human) |
| 03 | Narration | scripts/generate_narration.py | approved_set.json | audio/scene_XX.wav + metadata | Voice audition (human) |
| 04 | Subtitles | scripts/generate_subtitles.py + verify_subtitles.py | approved_set.json + audio sidecars | subtitles/<slug>.srt | Wording gate (auto) |
| 05 | Assembly | scripts/assemble_video.py | approved_set.json + audio + srt | output/<stamp>_<slug>.mp4 | — |
| 06 | QA | scripts/gates.py + ffprobe / volumedetect | MP4 | verdict (MP4-only output) | Final MP4 review (human) |

Stage 01 note: storyboard generation is **not** part of the pipeline. The
desktop UI supplies the scenes (narration, on-screen text, duration, media).
`scripts/generate_video_idea.py` and `scripts/llm_client.py` remain available
for standalone LLM use and are reachable from the UI's "Generate from AI"
dialog; they are not part of the one-click run.

## One-click path

The desktop UI is the entry point: `build_ui.bat` → `dist/ReelForge/ReelForge.exe`
→ `ui/ui_backend.py` → `scripts/run_video.py --name <slug> --scenes <file> --media <files>`.
The headless equivalent is the same `scripts/run_video.py` invocation.
See SETUP.md section 10.

## Where things live

- Configuration (voice, LLM, paths, QA thresholds): `_config/`
- Cross-stage resources (glossary, fact-check sources): `shared/`
- Stage-specific rules: `pipeline/NN-<stage>/references/`
- Per-run artifacts: images/, audio/, subtitles/, output/, logs/, temp/
- Long-term memory: `vault/` (Obsidian PARA)
- Codebase graph: `graphify-out/` (local, regenerated)

## Human checkpoints (do not skip)

1. Image contact sheet (pipeline/02 or run_video staging)
2. Narration voice audition (audio/test_kokoro_af_heart.wav)
3. Final MP4 review

## Audits (run before declaring a stage done)

- Docs: scripts/verify_docs.py (stdlib only) — ICM doc/code drift, including
  retired features reappearing in the docs.
- Stage 02: scripts/verify_images.py (stdlib only, no Pillow)
- Stage 04: scripts/verify_subtitles.py (wording gate)
- Stage 06: scripts/gates.py enforces the gate.yaml thresholds
  (duration, scene count, max_volume) on top of ffprobe geometry/codec checks.

## Canonical sources (do not duplicate)

- Voice/model/path config: `_config/` (single source)
- Scene durations & narration: the scene list (desktop UI / `--scenes` JSON) + approved_set.json
- Subtitle wording: must reproduce narration exactly (verify_subtitles.py)
- QA thresholds: `gate.yaml` (machine-readable, **enforced** by `scripts/gates.py`).
  `_config/qa_thresholds.md` is the prose mirror of the same numbers.

## Layered loading rule

Load Layer 0 (CLAUDE.md) always. Load Layer 1 (this file) on entry.
Load Layer 2 (stage CONTEXT.md) only for the stage you are working on.
Load Layers 3-4 (references/, artifacts) selectively per the stage Inputs table.