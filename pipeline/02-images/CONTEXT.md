# Stage 02 — Scene Images

## Inputs
| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| User media | `--media <files>` or per-scene `media_path` | Full | The scene visuals |
| Scene list | desktop UI / `--scenes` file | scene_number, duration, narration | Which media maps to which scene |

## Process (one-click path — the only path)
1. `scripts/run_video.py` normalizes each supplied media file to 512x768 via
   `scale + pad` (fit, never cropped or stretched).
2. Clips/GIFs are probed for duration (`clip_duration`); images get a static
   `scene_XX.png`.
3. A scene with no media gets a black placeholder PNG.
4. Per-scene metadata sidecars are written (`images/scene_XX_metadata.json`).
5. `images/approved_set.json` is written as the manifest — the downstream
   source of truth.
6. A contact sheet (`images/contact_sheet_<slug>.jpg`) is built for review.
   Cosmetic only; failure is non-fatal.

## Media persistence rule
A scene flagged `black_placeholder` (no attached media) does **not** render as
black when a previous scene had media: the assembly stage carries the most
recent media scene's image forward, so attached media persists across
black-backdrop scenes instead of being overridden by black. Genuine black is
only visible at the very start, when the first scene has no media yet.

## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| Scene images | images/scene_XX*.png | PNG 512x768 |
| Metadata | images/scene_XX*_metadata.json | JSON |
| Manifest | images/approved_set.json | JSON (scene_number, image, duration_seconds, narration, on_screen_text, image_source, source_type, clip_duration) |
| Contact sheet | images/contact_sheet*.jpg | JPG |

## Checkpoint (human)
Review the contact sheet. Approve before narration.

## Audit
- scripts/verify_images.py passes (stdlib only, no Pillow).
- All images 512x768.
- Manifest entries match files on disk.

## References
- _config/paths.md
- pipeline/02-images/references/sd_prompt_rules.md — historical prompt rules
  for local Stable Diffusion. No SD image generation runs in the pipeline
  today; scene visuals come from user-supplied media.
