# Stage 06 — Quality Assurance

## Inputs
| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| MP4 | output/<stamp>_<slug>.mp4 | Full | The deliverable |
| Subtitles | subtitles/<slug>.srt | Full | Side-load + burn-in parity |
| Config | _config/qa_thresholds.md | Thresholds | Pass/fail criteria |

## Process
1. ffprobe: codec, profile, pix_fmt, width, height, fps, duration.
2. volumedetect: max_volume <= -0.3 dB (no clipping).
3. Frame grabs at scene boundaries (composition + caption placement).
4. Generate publishing kit (output/<stamp>_<slug>.publishing.json): FB Reels + YT Shorts titles/descriptions/hashtags.
5. Copy SRT next to MP4.

## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| QA verdict | console + logs/<stamp>_<slug>.log | Text |
| Publishing kit | output/<stamp>_<slug>.publishing.json | JSON |
| Sidecar SRT | output/<stamp>_<slug>.srt | SRT |

## Checkpoint (human)
Final MP4 review. Approve before upload.

## Audit (pass criteria)
- Resolution 1080x1920, 9:16.
- H.264, yuv420p, 30 fps.
- AAC stereo, 48 kHz.
- Duration within 30-90s (Reels) / <=60s (Shorts).
- max_volume <= -0.3 dB.
- Captions readable, mobile-safe (MarginV 36).

## References
- _config/qa_thresholds.md