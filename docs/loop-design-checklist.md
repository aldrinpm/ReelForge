# Loop design checklist (adapted from loop-engineering)

Use this when adding a new feature (e.g. the desktop UI) or a new pipeline stage.

## Design
- [ ] Define the loop: discover work -> hand to agent -> verify -> persist state.
- [ ] Define the verifier (automated gates + human checkpoints) with unambiguous pass conditions.
- [ ] Define promotion criteria L1 -> L2 -> L3.
- [ ] Identify anti-patterns and failure modes (add to _core/anti-patterns.md).
- [ ] Set budget/risk constraints (loop-constraints.md).

## Build
- [ ] Implement the smallest change that satisfies the contract.
- [ ] Add a stage audit (scripts/verify_* or QA gate).
- [ ] Wire into run_video.py (archive-first, log to logs/).
- [ ] Add a --flag for opt-in behavior (default safe).

## Verify
- [ ] Syntax check (py_compile).
- [ ] Dry run on a fixture (qa_full_pipeline / qa_mixed_media).
- [ ] End-to-end run on a real topic.
- [ ] QA gates pass (resolution, codec, duration, volume).

## Promote
- [ ] Verifier correct on >= 5 consecutive runs (L3).
- [ ] Human checkpoint approved.
- [ ] Update STATE.md + loop-run-log.md.
- [ ] Mirror key state to vault/3. Resources/loop-state.md.
- [ ] Update _core/CONTEXT.md if a new stage was added.