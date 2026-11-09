# State — ReelForge (loop-engineering)

Current autonomy levels and last-run summary. Updated by `scripts/loop_doctor.py`
and at the end of successful `run_video.py` runs (opt-in via `--write-run-note`
also refreshes the vault mirror).

## Autonomy levels (L1 report / L2 assisted / L3 unattended)

| Component | Level | Notes |
|-----------|-------|-------|
| Storyboard generation (LM Studio) | L2 | Agent drafts; human fact-checks narration |
| Image staging (user media) | L2 | Archive-first; human reviews contact sheet |
| Narration (Kokoro) | L3 | Unattended after voice approval; auto-fit handles durations |
| Subtitles | L3 | Wording gate is automated (verify_subtitles.py) |
| Assembly (FFmpeg) | L3 | Automated; QA gates are the verifier |
| QA + publishing kit | L2 | Human reviews final MP4 before upload |
| Obsidian run note | L3 | Opt-in via --write-run-note |
| Desktop UI | L1 | Design approved; implementation in progress |

Promotion to L3 requires the verifier (QA gates) to pass on >= 5 consecutive runs.

## Last run

- Slug: webdev22
- Stamp: 20261108_105051
- Outcome: passed (QA passed)
- Verifier: PASS (19.5s, 1080x1920, h264/yuv420p, aac, -1.0 dB, mixed media)
- Run note: vault/1. Projects/webdev22-20261108_105051.md

## Blockers

- None currently blocking execution. LM Studio must be running for live storyboard generation.
- LM Studio storyboard path validated live (webdev21 run, 2026-11-08).
- Mixed-media + overlays validated (webdev21 run, 2026-11-08).
- Voice/LLM config validated (list-models, list-voices, preview, smoke tests).
- Desktop UI promoted from design draft to approved implementation (UI_DESIGN.md).

## Cost notes

Per-run token/time recorded in the Obsidian run note (vault/1. Projects/).