# Stage 06 — Quality Assurance

## Inputs
| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| MP4 | output/<stamp>_<slug>.mp4 | Full | The deliverable |
| Manifest | images/approved_set.json | scenes[] | Timeline + scene count |
| Config | gate.yaml | thresholds | Enforced pass/fail criteria |
| Config | _config/qa_thresholds.md | thresholds | Prose mirror of the same numbers |

## Process
1. ffprobe: codec, pix_fmt, width, height, fps, duration.
2. volumedetect: max_volume <= -0.3 dB (no clipping).
3. Compare rendered duration against the manifest timeline (+/-0.25s).
4. Enforce the `gate.yaml` thresholds via `scripts/gates.py`:
   - `duration_min_s` / `duration_max_s` (90s = Reels max; Shorts 60s)
   - `scene_count_min` / `scene_count_max` (1..12)
   - `max_volume_db` (-0.3)
5. On failure the run stops with `QA FAILED: <reason>` and no
   "READY TO UPLOAD" block.

### Override
Duration and scene-count violations are platform-fit rules and can be
acknowledged with `--allow-overlong` (the desktop UI's "Allow overlong"
checkbox). Clipping and broken geometry are never overridable.

## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| QA verdict | console + logs/<stamp>_<slug>.log | Text |

Output is MP4-only: no publishing kit and no SRT sidecar are produced.

## Checkpoint (human)
Final MP4 review. Approve before upload.

## Audit (pass criteria)
- Resolution 1080x1920, 9:16.
- H.264, yuv420p, 30 fps.
- AAC stereo, 48 kHz.
- Duration within the gate.yaml limits (30-90s target; <=60s for Shorts).
- Scene count within 1..12.
- max_volume <= -0.3 dB.
- Captions readable, mobile-safe (MarginV 36).

## References
- gate.yaml (machine-readable, enforced)
- _config/qa_thresholds.md (prose mirror)
- scripts/gates.py (the enforcement code)
