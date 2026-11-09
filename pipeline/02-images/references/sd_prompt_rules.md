# Stable Diffusion 1.5 prompt rules (Layer 3 reference)


## Generation params
- 512x768, 22 steps, CFG 6.5, sampler DPM++ 2M.
- One image at a time (VRAM rule).

## Prompt constraints
- Vertical composition; no text, captions, labels, watermark.
- Cinematic astrophysics documentary style (for science topics).
- Deep navy/black background, subtle orange/gold/blue highlights.
- Scientifically inspired visualization, photorealistic space environment.

## Negative prompt (base)
text, captions, letters, numbers, watermark, logo, cartoon, anime, low quality,
blurry, low resolution, oversaturated, distorted objects, duplicate objects,
unrealistic geometry, artificial borders.

## Scene-specific overrides
- Scene 3: recognizable black-hole silhouette, luminous accretion disk, gravitational lensing.
- Scene 4: warped spacetime geometry; no literal visible singularity, no bright white dot.
- Scene 5: Einstein ring, obvious lensing; negative adds: bright glowing center, sun, bright star surface, lens flare.

## Rejection criteria
- White-dot singularity, particles escaping the horizon, cartoon/anime style, text/watermarks.
- Rejected candidates -> images\archive\ (never delete).