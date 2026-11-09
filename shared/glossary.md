# Shared glossary (cross-stage reference)

- **Manifest**: images/approved_set.json — downstream source of truth for a run.
- **Scene**: one storyboard segment with narration, image_prompt, motion_direction, duration.
- **Checkpoint**: human approval gate (image set, voice, final MP4).
- **Audit**: automated quality check with an unambiguous pass condition.
- **Archive-first**: superseded artifacts are moved (never deleted) to */archive/ with a stamp prefix.
- **Auto-fit**: scene duration = max(storyboard, narration + 0.9s) rounded up to 0.5s; clips also respect clip length (cap 15s).