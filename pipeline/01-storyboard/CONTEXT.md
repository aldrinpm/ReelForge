# Stage 01 — Storyboard

## Inputs
| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| User topic | inbox/<name>/prompt.txt | Full text | Drives the storyboard |
| Config | _config/llm.md | Model/endpoint | Which LLM to use |
| Prompt template | pipeline/01-storyboard/references/system_prompt.md | Full | System prompt sent to LLM |

## Process
1. Read prompt.txt and config.
2. Call scripts/generate_video_idea.py (LM Studio or cloud LLM, OpenAI-compatible).
3. Validate: N scenes (1-8), total duration 1-180s, each scene has narration_segment, image_prompt, motion_direction, duration_seconds.
4. Save storyboard JSON to output/<stamp>_<slug>_storyboard.json.
5. Human fact-checks narration (claims, caveats, sources).

## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| Storyboard | output/<stamp>_<slug>_storyboard.json | JSON (title, topic, scenes[], fact_check_notes, source_suggestions) |

## Checkpoint (human)
Fact-check narration. Revise lines in the JSON; adjust scene durations (9/9/9.5/10/9/9.5 was the first run). Archive the original if revised.

## Audit
- Exactly N scenes (matches media count in one-click mode).
- Total duration within 30-90s (Reels) preferred.
- Every scene has narration_segment, image_prompt, motion_direction, duration_seconds.
- Fact-check notes present for any scientific claim.

## References
- pipeline/01-storyboard/references/system_prompt.md
- _config/llm.md