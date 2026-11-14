# Stage 04 — Subtitles (SRT)

## Inputs
| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Manifest | images/approved_set.json | scenes[].narration, duration_seconds | Text + scene starts |
| Audio sidecars | audio/scene_XX_metadata.json | duration_seconds | Measured narration length |
| Style | scripts/assemble_video.py | SUBTITLE_STYLE constant | Burn-in font/size/outline/margin |

## Process
1. Run scripts/generate_subtitles.py (--out subtitles/<slug>.srt).
2. Narration starts scene_start + 0.4s. Two cues per scene, split at natural pauses.
3. Char-proportional cue timing. Cue text must reproduce narration exactly.
4. Run scripts/verify_subtitles.py (wording gate; exits non-zero on failure).
5. Hand-picked SPLITS overrides win when wording matches; otherwise auto-split.

## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| SRT | subtitles/<slug>.srt | SRT (2 cues/scene) |

## Checkpoint
None (auto-gated by verify_subtitles.py).

## Audit
- scripts/verify_subtitles.py exits 0 (monotonic timing, no overlaps).
- Cue texts reproduce narration wording exactly.
- Last cue ends <= timeline - 0.5s.
- Burn-in preflight (assemble_video.py) confirms subtitles filter works.

## References
- scripts/assemble_video.py — `SUBTITLE_STYLE` (Arial 15, outline 2, MarginV 36)
- _config/qa_thresholds.md — duration / platform-fit thresholds