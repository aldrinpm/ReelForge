# Stage 03 — Narration (TTS)

## Inputs
| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Manifest | images/approved_set.json | scenes[].narration, duration_seconds | Text + target durations |
| Config | _config/voice.md | engine, voice, speed | Which TTS + voice |
| Audio sidecars | audio/scene_XX_metadata.json | duration_seconds | Measured durations |

## Process
1. Run scripts/generate_narration.py (Kokoro-82M, CPU, venv-tts).
2. Voice from config (default af_heart, en-US). Kokoro is English-only.
3. Peak-normalize each segment to 0.89 (-1 dBFS).
4. Write audio/scene_XX.wav (24 kHz mono) + metadata sidecar.
5. Auto-fit: scene duration = max(storyboard, narration + 0.9s), rounded up to 0.5s (run_video.py).
6. For clips: also respect clip length (cap 15s/scene).

## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| Narration WAVs | audio/scene_XX.wav | WAV 24kHz mono |
| Metadata | audio/scene_XX_metadata.json | JSON (duration, voice, peak, gain) |

## Checkpoint (human)
Audition the voice (audio/test_kokoro_af_heart.wav or --preview). Approve before subtitles.

## Audit
- 6 (or N) WAVs present.
- Per-scene durations within target (flag LONG if narration > target - 0.5s).
- Total narration <= timeline - (N * 0.5) headroom.
- Peak <= -1 dBFS (no clipping).

## References
- _config/voice.md
- scripts/test_kokoro.py (preview pattern)