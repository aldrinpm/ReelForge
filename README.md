# ReelForge --- OpenCode Handoff

This folder contains Markdown context and task instructions for an
OpenCode coding agent.

## Files

-   `PROJECT_CONTEXT.md` --- hardware, software, paths, model selection,
    current assets, architecture, project status, and long-term plan.
-   `OPENCODE_TASK.md` --- constrained instructions for the next task:
    first live orchestrator run through LM Studio (Task 8 one-click
    pipeline is built and QA-tested).
-   `config.json` --- runtime config for LLM provider/model/endpoint and TTS
    voice/speed (gitignored; contains secrets). Edit or use the setup
    wizard.

## Quick start (one-click pipeline)

Drop `prompt.txt` + 6 images into `inbox\<video-name>\`, then
double-click `make_video.bat`. Full behavior and flags: `SETUP.md`
section 10.

## How to use

1.  Copy these files into your project documentation folder, for example
    `E:\\AI-Video-Production\\`.
2.  Open the project folder in OpenCode.
3.  Add `PROJECT_CONTEXT.md` and `OPENCODE_TASK.md` to the agent's
    context.
4.  Ask the agent to follow the **First action** in `PROJECT_CONTEXT.md`
    and the **Current task** in `OPENCODE_TASK.md`.
5.  Keep the Qwythos 9B V2 MTP model selected in OpenCode.

These documents do not configure OpenCode or modify files on your E:
drive. They are portable instructions for the agent to read.
