# Anti-patterns — ReelForge

Things that have caused failures or must never be done. Referenced by gate.yaml
blockers. Sourced from SETUP.md gotchas + loop-engineering failure modes.

- Running Qwythos (LM Studio) and Stable Diffusion concurrently on the 8 GB GPU.
- Bundling FFmpeg or model weights into the installer (keeps bundle small; they
  live on E: / system PATH).
- Installing Pillow or other "just in case" packages (verification uses stdlib).
- Skipping verify_subtitles.py wording gate.
- Skipping verify_docs.py after changing code or docs.
- Deleting superseded artifacts instead of archiving (archive-first, never delete).
- Assuming the manifest's scene count is 6 (now variable 1-12).
- Hardcoding LLM endpoint/model or TTS voice (use config.json + CLI flags).
- Requiring LM Studio for a pipeline run (the pipeline is LLM-free; LM Studio
  is only needed for the standalone "Generate from AI" path).
- Editing a previous run's artifacts in place instead of archiving first.
- Promoting a component to L3 before 5 consecutive passing runs.
- Loading the entire PROJECT_CONTEXT.md when only one stage is needed (use ICM
  layered loading).
- Committing config.json (contains secrets) or graphify-out/ (regenerated).

## Doc/code drift (the recurring one)

- Changing a stage's inputs, outputs, script or flags **without** updating
  that stage's `CONTEXT.md` in the same change. The ICM layers are a
  contract, not a wish list.
- Leaving a doc describing a feature, script or artifact that was removed.
  A retired feature must stay retired in the docs too.
- Updating a doc to describe behaviour the code does not have. The code is
  the truth; the doc follows.
- Declaring a threshold in `gate.yaml` (or `_config/qa_thresholds.md`) and
  not enforcing it in code. Thresholds that are not enforced are wishes:
  `scripts/gates.py` enforces them at QA.
- Shipping dead code that references removed features (e.g. a reader for an
  artifact the pipeline no longer writes).
