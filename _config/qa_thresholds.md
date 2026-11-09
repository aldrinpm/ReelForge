# QA thresholds (canonical source)

Resolution: 1080x1920 (9:16).
Frame rate: 30 fps.
Codec: H.264, yuv420p.
Audio: AAC, 48 kHz, stereo.
CRF: 18. Preset: medium. +faststart.
Crossfade: 0.5s. Narration delay: 0.4s. Tail margin: 0.5s.
Subtitle: Arial 15, outline 2, MarginV 36, bottom-center.
Overlay: on-screen text (headline) burned per scene, top-center, bold Arial,
  52pt, white with black outline, shown for first 3s (configurable via
  --overlay / --no-overlay / --overlay-duration / --overlay-position).
Max volume: <= -0.3 dB (no clipping). Target -1.0 dB.
Duration: 30-90s (Reels) / <=60s (Shorts).
Per-scene: image Ken Burns; clip/gif trim+freeze (cap 15s/scene).
Media count: 1-12 per run.