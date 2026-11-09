# Anti-patterns — ReelForge

Things that have caused failures or must never be done. Referenced by gate.yaml
blockers. Sourced from SETUP.md gotchas + loop-engineering failure modes.

  concurrently. (VRAM rule.)
- Bundling FFmpeg or model weights into the installer (keeps bundle small; they
  live on E: / system PATH).
- Installing Pillow or other "just in case" packages (verification uses stdlib).
- Skipping verify_subtitles.py wording gate.
- Deleting superseded artifacts instead of archiving (archive-first, never delete).
- Assuming the manifest's scene count is 6 (now variable 1-12).
- Hardcoding LLM endpoint/model or TTS voice (use config.json + CLI flags).
- Running the pipeline with LM Studio down (preflight catches it, but don't bypass).
- Editing a previous run's artifacts in place instead of archiving first.
- Promoting a component to L3 before 5 consecutive passing runs.
- Loading the entire PROJECT_CONTEXT.md when only one stage is needed (use ICM
  layered loading).
- Committing config.json (contains secrets) or graphify-out/ (regenerated).