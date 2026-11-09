# Layer 1 — Task Router (ICM)

Read this after CLAUDE.md (Layer 0). Then read only the stage CONTEXT.md for the
stage you are working on. Do NOT load everything.

## Pipeline stages (numbered = execution order)

| # | Stage | Script | Inputs | Outputs | Checkpoint |
|---|-------|--------|--------|---------|------------|
| 01 | Storyboard | scripts/generate_video_idea.py | inbox/<name>/prompt.txt | output/<stamp>_<slug>_storyboard.json | Fact-check narration (human) |
| 02 | Images | scripts/generate_scene_images.py (manual) OR run_video.py (auto) | storyboard JSON | images/scene_XX.png + metadata + approved_set.json | Contact sheet review (human) |
| 03 | Narration | scripts/generate_narration.py | approved_set.json | audio/scene_XX.wav + metadata | Voice audition (human) |
| 04 | Subtitles | scripts/generate_subtitles.py + verify_subtitles.py | approved_set.json + audio sidecars | subtitles/<slug>.srt | Wording gate (auto) |
| 05 | Assembly | scripts/assemble_video.py | approved_set.json + audio + srt | output/<stamp>_<slug>.mp4 | — |
| 06 | QA | ffprobe / volumedetect | MP4 | verdict + publishing kit | Final MP4 review (human) |

## One-click path

`make_video.bat` → `scripts/run_video.py <name>` runs stages 01-06 automatically
with archive-first staging. See SETUP.md section 10.

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

- Stage 02: scripts/verify_images.py (stdlib only, no Pillow)
- Stage 04: scripts/verify_subtitles.py (wording gate)
- Stage 06: ffprobe geometry/codec/duration + volumedetect (max_volume <= -0.3 dB)

## Canonical sources (do not duplicate)

- Voice/model/path config: `_config/` (single source)
- Scene durations & narration: storyboard JSON + approved_set.json
- Subtitle wording: must reproduce narration exactly (verify_subtitles.py)

## Layered loading rule

Load Layer 0 (CLAUDE.md) always. Load Layer 1 (this file) on entry.
Load Layer 2 (stage CONTEXT.md) only for the stage you are working on.
Load Layers 3-4 (references/, artifacts) selectively per the stage Inputs table.