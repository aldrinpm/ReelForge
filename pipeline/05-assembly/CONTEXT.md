# Stage 05 — Assembly (FFmpeg)

## Inputs
| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Manifest | images/approved_set.json | scenes[] (image, image_source, source_type, duration) | What to render |
| Audio | audio/scene_XX.wav | Full | Narration |
| Subtitles | subtitles/<slug>.srt | Full | Burn-in only |
| Config | _config/qa_thresholds.md | FPS, size, CRF | Encode settings |

## Process (two-pass)
Pass 1 — normalize each scene to temp/scene_XX_norm.mp4 (1080x1920, 30fps):
- image: `scale` (fit, `force_original_aspect_ratio=decrease`) + `pad` to
  2160x3840 on black bars, then `zoompan` at z=1 (static hold) + downscale to
  1080x1920. Nothing is stretched and no frame edge is ever cropped, so all
  motions are pinned to z=1 (no Ken Burns zoom, no pan).
- clip/gif: fit + `pad` to 1080x1920, `fps=30`, `tpad` freeze if short, trim
  to duration+0.5s.
- **Media persistence**: a scene whose `image_source` is `black_placeholder`
  and that follows a media scene reuses the most recent media scene's image
  (held for its own duration) instead of rendering black. The scene keeps its
  own narration timing and on-screen text.

Pass 2 — xfade chain (0.5s) + narration adelay (scene_start+0.4s) + amix +
aresample 48k stereo + optional subtitles burn-in + encode.
- libx264, preset medium, CRF 18, -pix_fmt yuv420p, AAC 160k, +faststart.

### Text burn-in flags
| Flag | Effect |
|------|--------|
| `--overlay` / `--no-overlay` | Per-scene `on_screen_text` headline (drawtext). Default **on**. |
| `--burn-narration` / `--no-burn-narration` | Narration captions (subtitles filter). Default **off**. |

Both are surfaced in the desktop UI as the "Burn overlays" and "Burn
narration" checkboxes. Narration *audio* is always muxed; the flag only
controls the burned text.

## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| MP4 | output/<stamp>_<slug>.mp4 | H.264/AAC, 1080x1920, 30fps |
| Filter graph | temp/filter_complex.txt | FFmpeg filter script |

Output is MP4-only: no SRT sidecar and no publishing kit.

## Checkpoint
None (QA is stage 06).

## Audit
- Render exits 0; output file exists.
- Duration == timeline (+/-0.25s).
- No FFmpeg errors in stderr.

## References
- _config/qa_thresholds.md
- scripts/assemble_video.py (MOTIONS, SUBTITLE_STYLE, scene_has_media)
