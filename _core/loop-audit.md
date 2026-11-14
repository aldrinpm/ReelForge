# Loop audit — ReelForge (verifier definition)

The "verifier" for this project is the set of automated + human gates below.
A run is PASS only if every applicable gate passes. Promotion to L3 (gate.yaml)
requires 5 consecutive PASS runs.

## Automated gates (must pass before declaring a stage done)

### Docs (every change)
- scripts/verify_docs.py exits 0 (stdlib only): no stale file references in
  the ICM layers, no retired feature/script mentioned, every stage
  CONTEXT.md keeps its required sections, gate.yaml components are known.

### Stage 02 — Images
- scripts/verify_images.py exits 0 (stdlib only; no Pillow).
- All images 512x768.
- Manifest entries match files on disk.
- Contact sheet generated (cosmetic; failure non-fatal).

### Stage 04 — Subtitles
- scripts/verify_subtitles.py exits 0 (monotonic timing, no overlaps).
- Cue texts reproduce narration wording exactly.
- Last cue ends <= timeline - 0.5s.

### Stage 05 — Assembly
- ffmpeg exits 0; output file exists.
- Duration == timeline (+/-0.25s).
- No FFmpeg errors in stderr.

### Stage 06 — QA
- ffprobe: 1080x1920, 30fps, h264, yuv420p, aac 48kHz stereo.
- Duration matches the manifest timeline (+/-0.25s).
- volumedetect: max_volume <= -0.3 dB.
- gate.yaml thresholds ENFORCED by scripts/gates.py: duration within
  1-90s (Reels max 90s; Shorts 60s) and scene count within 1-99999
  (no fixed cap — scene count depends on prompt).
  Duration/scene-count violations may be acknowledged with
  `--allow-overlong`; clipping may not.
- Output is MP4-only (no publishing kit, no SRT sidecar).

## Human checkpoints (never skip)
1. Image contact sheet review.
2. Narration voice audition.
3. Final MP4 review before upload.

## Anti-patterns (block promotion if present)
See _core/anti-patterns.md.