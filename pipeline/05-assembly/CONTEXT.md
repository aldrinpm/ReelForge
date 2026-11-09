# Stage 05 — Assembly (FFmpeg)

## Inputs
| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Manifest | images/approved_set.json | scenes[] (image, source_type, duration) | What to render |
| Audio | audio/scene_XX.wav | Full | Narration |
| Subtitles | subtitles/<slug>.srt | Full | Burn-in + side-load |
| Config | _config/qa_thresholds.md | FPS, size, CRF | Encode settings |

## Process (two-pass)
Pass 1 — normalize each scene to temp/scene_XX_norm.mp4 (1080x1920, 30fps):
- image: lanczos upscale 2560x3840 -> crop 2160x3840 -> zoompan (Ken Burns) -> 1080x1920
- clip/gif: scale+crop 1080x1920, fps=30, tpad freeze if short, trim to duration+0.5s
Pass 2 — xfade chain (0.5s) + narration adelay (scene_start+0.4s) + amix + aresample 48k stereo + subtitles burn-in + encode.
- libx264, preset medium, CRF 18, -pix_fmt yuv420p, AAC 160k, +faststart.

## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| MP4 | output/<stamp>_<slug>.mp4 | H.264/AAC, 1080x1920, 30fps |
| Sidecar SRT | output/<stamp>_<slug>.srt | Copy of subtitles |
| Filter graph | temp/filter_complex.txt | FFmpeg filter script |

## Checkpoint
None (QA is stage 06).

## Audit
- Render exits 0; output file exists.
- Duration == timeline (+/-0.25s).
- No FFmpeg errors in stderr.

## References
- _config/qa_thresholds.md
- scripts/assemble_video.py (MOTIONS, SUBTITLE_STYLE)