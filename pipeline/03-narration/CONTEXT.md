# Stage 03 — Narration (TTS)

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Manifest | images/approved_set.json | scenes[].narration, duration_seconds | Text + target durations |
| Config | _config/voice.md | engine, voice, speed, clone_ref | Which engine + voice |
| Reference WAV | any user-supplied audio path (`--voice-ref`) | 5-20 s, one speaker | Cloned-voice speaker prompt |
| Audio sidecars | audio/scene_XX_metadata.json | duration_seconds | Measured durations |

## Process

Two interchangeable engines; both write the same artifacts.

1. **Kokoro presets (default).** Run scripts/generate_narration.py
   (Kokoro-82M, CPU, venv-tts) with `--voice` / `--speed`.
2. **Voice cloning.** When a reference WAV is supplied, run
   scripts/clone_narration.py instead (Chatterbox TTS, CPU, venv-clone,
   `--reference` + `--exaggeration` + `--cfg-weight`). The reference clip is a
   speaker prompt, trimmed to 20 s; no speed control (pace = cfg weight).
   Decoding goes through librosa at 24 kHz mono — never relabel a 16 kHz file
   as 24 kHz (that plays the speaker 1.5x fast and clones a higher voice).
   The 20 s cut snaps back up to 0.5 s to a quiet gap, never mid-word.
3. Voice from config (default af_heart, en-US). Kokoro is English-only;
   Chatterbox cloning is English-focused.
4. Peak-normalize each segment to 0.89 (-1 dBFS); write 24 kHz mono.
5. Write audio/scene_XX.wav + metadata sidecar (engine, voice or clone
   reference, peak, gain, duration).
6. Auto-fit: scene duration = max(storyboard, narration + 0.9s), rounded up to 0.5s (run_video.py).
7. For clips: also respect clip length (cap 15s/scene).

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Narration WAVs | audio/scene_XX.wav | WAV 24kHz mono |
| Metadata | audio/scene_XX_metadata.json | JSON (duration, engine, voice, peak, gain) |

## Checkpoint (human)

Audition the voice before subtitles: Kokoro — audio/test_kokoro_af_heart.wav or
`--preview`; cloned voice — UI "Preview clone" or clone_narration.py `--preview`
(writes audio/preview_clone.wav).

## Audit

- 6 (or N) WAVs present.
- Per-scene durations within target (flag LONG if narration > target - 0.5s).
- Total narration <= timeline - (N * 0.5) headroom.
- Peak <= -1 dBFS (no clipping).
- Cloned runs: sidecar records the reference path used (provenance).

## References

- _config/voice.md
- scripts/test_kokoro.py (preview pattern)
