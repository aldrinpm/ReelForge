# Conventions — ReelForge (ICM layer)

These conventions adapt the ICM (Interpretable Context Methodology) patterns to this
pipeline. Full source: https://github.com/RinDig/Interpretable-Context-Methodology

## Architecture

1. **One stage, one job.** Each stage handles a single step. A stage that researches
   does not also write; a stage that writes does not also build.
2. **Plain text as the interface.** Stages communicate through markdown/JSON files.
   No binary formats, no database. Any tool that reads text can participate; any human
   with a text editor can inspect or modify any artifact.
3. **Layered context loading.** Agents load only the context needed for the current stage.
   Less irrelevant context = better model performance. This is prevention, not compression.
4. **Every output is an edit surface.** The intermediate output of each stage is a file a
   human can open, read, edit, and save before the next stage runs. The system picks up
   whatever the human left there.
5. **Configure the factory, not the product.** A workspace is set up once with the user's
   preferences (voice, LLM, paths, style). After that, each run produces a new deliverable
   using the same configuration.
6. **Stage contracts.** Every stage CONTEXT.md has Inputs, Process, and Outputs sections.
   Inputs table specifies exactly which files/sections to load and why.
7. **Stage handoffs.** Output folders connect stages. Edit any output and the next stage
   picks up your changes.
8. **One-way references.** If A references B, B does not reference A. Prevents circular
   dependencies; scales linearly.
9. **Selective section routing.** CONTEXT.md tables specify which sections of which files
   to load — not the whole file.
10. **Canonical sources.** Every piece of information has one home. Other files point there.
    The moment the same rule exists in two files, they drift.

## Quality

11. **Specs are contracts.** Specification stages define WHAT and WHEN. They do not prescribe
    HOW. Build stages have creative freedom within the quality floor defined by references.
12. **Checkpoints.** Creative stages pause for human steering between steps. The agent completes
    a unit of work, presents options, and the human redirects before the next unit begins.
13. **Stage audits.** Quality checklists the agent runs after completing a stage but before
    writing output. Each check has an unambiguous pass condition.
14. **Docs over outputs.** Reference docs are the authoritative source for how to build.
    Agents do not read previous outputs to learn patterns.

## Onboarding

15. **Questionnaire design.** Flat, all-at-once, system-level only. Configure the factory,
    not the product. Voice questions extract concrete examples, not descriptions.

## This pipeline's stages

| # | Stage | Script | Artifact dir |
|---|-------|--------|--------------|
| 01 | Storyboard | scripts/generate_video_idea.py | output/ |
| 02 | Images | scripts/generate_scene_images.py | images/ |
| 03 | Narration | scripts/generate_narration.py | audio/ |
| 04 | Subtitles | scripts/generate_subtitles.py + verify_subtitles.py | subtitles/ |
| 05 | Assembly | scripts/assemble_video.py | output/ + temp/ |
| 06 | QA | (ffprobe / volumedetect / frame grabs) | output/ + logs/ |

Stage scripts remain in scripts/ (documentation-only layer; no relocation).
Human checkpoints: image contact sheet, narration voice, final MP4.