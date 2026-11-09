# Loop constraints — ReelForge

Risk/budget constraints for loop-engineering. Referenced by gate.yaml and
_core/loop-audit.md. These constrain what the agent may do unattended.

## Hardware
- Kokoro TTS is CPU-only (never GPU).
- All models/assets/artifacts stay on drive E:.

## Platform limits
- Facebook Reels: <= 90s. YouTube Shorts: <= 60s.
- Resolution 1080x1920, 9:16. H.264 yuv420p, AAC 48kHz stereo.
- Max volume <= -0.3 dB (no clipping).

## Cost / budget
- No paid APIs or cloud services by default. Cloud LLM is opt-in only.
- Graphify: local OSS mode default (--code-only); semantic doc pass costs LLM credits.
- Per-run token/time recorded in Obsidian run note; no standalone budget tool.

## Data
- API keys via env vars (OPENAI_API_KEY etc.), never committed, never logged.
- config.json is gitignored.

## Promotion
- L3 requires verifier correct on >= 5 consecutive runs.
- UI features promote to "shipped" only after 2 passing end-to-end runs on real topics.