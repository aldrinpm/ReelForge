# Stage 01 — Storyboard (scene list)

## Inputs
| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Desktop UI | New Run panel | scene rows | Narration, on-screen text, duration, per-scene media |
| CLI | `--scenes <file.json>` | Full | Same scene list, on disk |

## Process (one-click path)
1. The desktop UI collects the scenes (narration, on-screen text, duration)
   and writes them to a temporary JSON file.
2. `scripts/run_video.py` renumbers scenes 1..N in order and validates each
   one: `narration_segment` and `duration_seconds` must be non-empty.
3. Scenes may carry their own `media_path` (per-scene "Attach Media");
   otherwise media is matched positionally from `--media`.
4. Scene count is 1..12 (`gate.yaml` `scene_count_max`); the QA stage
   enforces the limit.

## Process (standalone LLM path — NOT part of the one-click run)
`scripts/generate_video_idea.py` + `scripts/llm_client.py` can still produce a
storyboard JSON from a topic via LM Studio or any OpenAI-compatible endpoint.
The desktop UI's "Generate from AI" dialog calls the same endpoint directly
(`/ai/generate`). Neither path runs inside the one-click pipeline.

## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| Scene list | temp file written by the UI / `--scenes` file | JSON list of scenes |
| Manifest | images/approved_set.json | JSON (scene_number, image, duration_seconds, narration, on_screen_text, image_source, ...) |

## Checkpoint (human)
Fact-check the narration (claims, caveats, sources) in the New Run panel
before starting the run.

## Audit
- Exactly N scenes; N equals the media count when no scene carries its own
  `media_path`.
- Every scene has `narration_segment` and `duration_seconds`.
- Scene count within 1..12 (enforced at QA via `scripts/gates.py`).

## References
- pipeline/01-storyboard/references/system_prompt.md (standalone LLM path)
- _config/llm.md (standalone LLM path)
- `validate_storyboard()` in scripts/run_video.py
