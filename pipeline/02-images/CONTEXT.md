# Stage 02 — Scene Images

## Inputs
| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Storyboard | output/<stamp>_<slug>_storyboard.json | scenes[].image_prompt, motion_direction | Prompts + motion |
| Prompt rules | pipeline/02-images/references/sd_prompt_rules.md | Full | SD 1.5 prompt constraints |

## Process (manual path)
1. Run scripts/generate_scene_images.py (--scenes/--suffix/--seed).
3. Build contact sheet (3x2 or adaptive) for review.
4. Human approves/rejects. Rejected candidates -> images\archive\.
5. Write images\approved_set.json (manifest; downstream source of truth).

## Process (one-click path)
Images normalized to 512x768 via scale+crop. Clips/GIFs probed for duration.

## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| Scene images | images/scene_XX*.png | PNG 512x768 |
| Metadata | images/scene_XX*_metadata.json | JSON |
| Manifest | images/approved_set.json | JSON (scene_number, image, duration_seconds, narration, ...) |
| Contact sheet | images/contact_sheet*.jpg | JPG |

## Checkpoint (human)
Review contact sheet. Approve the final six (or N) images before narration.

## Audit
- scripts/verify_images.py passes (stdlib only, no Pillow).
- All images 512x768.
- Manifest entries match files on disk.

## References
- pipeline/02-images/references/sd_prompt_rules.md
- _config/paths.md