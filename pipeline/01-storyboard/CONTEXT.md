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
Neither path runs inside the one-click pipeline.

### AI Storyboard Generator (desktop UI)
1. The user writes a prompt in the "AI Storyboard Generator" dialog and sends it.
2. The backend sends a **prepared statement** (`STORYBOARD_SYSTEM_PROMPT` in
   `ui/ui_backend.py`) that pins the model to the canonical storyboard
   structure, plus the user's prompt as the user message.
3. The response is parsed and validated by `scripts/storyboard_format.py`.
4. If the structure is **not** met, the specific problems are written to the
   application console log (Console tab) and the "Proceed to New Run" button
   stays disabled.
5. If the structure **is** met, the "Proceed to New Run" button (below the
   response log window) is enabled. Clicking it fills the New Run form —
   title, description, hashtags and one scene row per scene — and closes the
   dialog.

## Storyboard text format (canonical)
```
Title: <one-line video title>
Description: <social post description>
Hashtags: <#tag1 #tag2 #tag3>

Scene 1
Overlay: <on-screen headline, max 35 chars>
Narration: <spoken narration for scene 1>
```
`scripts/storyboard_format.py` is the **only** implementation: it parses the
format and validates it (title/description/hashtags present, scenes present,
every scene has an overlay and narration, overlay <= 35 chars, ascending
unique scene numbers). The UI reaches it through `POST /parse/storyboard`;
"Generate from AI" and "Browse from text file" both use it, so the two
paths cannot drift apart.

## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| Scene list | temp file written by the UI / `--scenes` file | JSON list of scenes |
| Manifest | images/approved_set.json | JSON (scene_number, image, duration_seconds, narration, on_screen_text, image_source, ...) |
| Structure errors | application console log (Console tab) | Text |

## Checkpoint (human)
Fact-check the narration (claims, caveats, sources) in the New Run panel
before starting the run.

## Audit
- Exactly N scenes; N equals the media count when no scene carries its own
  `media_path`.
- Every scene has `narration_segment` and `duration_seconds`.
- Scene count within 1..12 (enforced at QA via `scripts/gates.py`).

## References
- scripts/storyboard_format.py — the canonical parser + validator
- scripts/run_video.py — `validate_storyboard()` (pipeline-side scene checks)
- pipeline/01-storyboard/references/system_prompt.md (standalone LLM path)
- _config/llm.md (standalone LLM path)
