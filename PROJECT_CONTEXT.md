# ReelForge --- Project Context

> ⚠️ **HISTORICAL SNAPSHOT — superseded by the ICM layers.**
> This file records the project as of **2026-11-07** (pre-desktop-UI,
> pre-MP4-only). Several things described below no longer exist:
> the `inbox/` + `prompt.txt` workflow, `scripts/generate_scene_images.py`,
> the publishing kit (`.publishing.json`), the SRT sidecar, and the LLM
> inside the pipeline.
>
> **The live context is:** `CLAUDE.md` (Layer 0) → `_core/CONTEXT.md`
> (Layer 1) → `pipeline/NN-<stage>/CONTEXT.md` (Layer 2) → `_config/`.
> When this file and the ICM layers disagree, **the ICM layers and the
> code win**. Read `CLAUDE.md` and `_core/CONTEXT.md` first; come back
> here only for history.

**Last updated:** 2026-11-07 (after narration and TTS milestones)\
**Purpose:** Handoff context for an OpenCode AI coding agent using the
local Qwythos 9B V2 MTP GGUF model.

## 1. Mission

Build a reusable, locally operated AI video-production pipeline for
educational short-form videos published to Facebook Reels and YouTube
Shorts.

The eventual workflow accepts a topic and produces a publish-ready
vertical MP4 containing a fact-checked storyboard, AI-generated scene
images, local narration, synchronized subtitles, animated scenes,
transitions, mixed audio, and quality checks.

### Constraints

-   Prefer free, locally hosted models and open-source software.
-   No paid APIs or cloud video-generation subscriptions.
-   Keep models, assets, and outputs on drive `E:`.
-   Avoid unnecessary installations and downloads.
-   Work incrementally: inspect, change one component, test, then
    continue.
-   Do not assume a command succeeded without checking its output.
-   Use exact Windows PowerShell commands and paths.
-   Do not reinstall components already working.
-   Do not benchmark models unless specifically requested.

## 2. Target video specification

  Property         Target
  ---------------- -----------------------------------
  Platforms        Facebook Reels and YouTube Shorts
  Duration         45--60 seconds
  Current sample   54 seconds
  Aspect ratio     9:16
  Resolution       1080 × 1920
  Frame rate       30 FPS
  Video codec      H.264
  Audio codec      AAC
  Container        MP4
  Visuals          AI-generated stills with motion
  Narration        Local TTS
  Subtitles        Generated and synchronized

Use aspect-aware scaling/cropping. Never stretch source images or crop
away important subjects.

## 3. Machine and software environment

### Hardware

-   Windows 11 Pro, build 22631
-   AMD Ryzen 7 5700X, 8 cores / 16 threads
-   NVIDIA RTX 4060, 8 GB VRAM
-   32 GB RAM
-   NVIDIA driver 616.92

### Installed software

-   LM Studio --- local LLM server
-   Stable Diffusion 1.5 checkpoint --- installed and working
-   FFmpeg 9.0.2 --- installed and working
-   Python 3.11.9, 3.13.7, and 3.15.2
-   eSpeak NG 1.52.0 at `C:\Program Files\eSpeak NG\` (system PATH;
    OpenCode shells started before the PATH update must append the
    directory to process PATH manually)

### Important Python paths

-   Python 3.11.9: `E:\\ai\\AirLLM\\py3.11.9\\python.exe`
-   Python 3.13.7: `E:\\Program Files\\Python313\\python.exe`
-   Python 3.15.2:
    `C:\\Users\\Cromite\\AppData\\Local\\Python\\pythoncore-3.15-64\\python.exe`

Packages installed in one Python environment are not necessarily
available in another.

## 4. Local LLM and MTP model

Selected storyboard model:

`empero-ai/qwythos-9b-v2-gguf/qwythos-9b-v2-mtp-q4_k_m.gguf`

The user refers to this as the **Qwythos 9B V2 GGUF MTP
model/architecture**.

-   LM Studio API: `http://127.0.0.1:1234/v1`

Operational constraints: - Unload Qwythos from GPU while generating
Stable Diffusion images to reduce VRAM contention. - RTX 4060 has 8 GB
VRAM; generate images sequentially with conservative settings. - The
successful storyboard was generated using the Qwythos MTP model. Do not
attribute it to another model. - One script may cosmetically print
"Qwen" while configured for Qwythos; correct the label when convenient,
but it is not a functional blocker. - The user intends to use OpenCode
with the local Qwythos 9B V2 MTP model as the coding agent. Do not
assume OpenCode's provider configuration is complete without checking.

## 5. Project workspace

Root: `E:\\AI-Video-Production\\`

Directories: - `models\\` - `scripts\\` - `audio\\` - `images\\` -
`clips\\` - `subtitles\\` - `output\\` - `temp\\` - `logs\\` -
`workflows\\`

## 6. Completed components

### 6.1 Storyboard generation

Script: `E:\\AI-Video-Production\\scripts\\generate_video_idea.py`

It calls LM Studio `/v1/chat/completions` and requests structured JSON
containing: - Title, topic, target duration, audience - Narration -
Exactly six scenes - Per-scene duration - Narration segment - On-screen
text - Image prompt - Motion direction - Fact-check notes - Source
suggestions

It validates six scenes and a total duration between 45 and 60 seconds.

**Status: Working and tested.**

### 6.2 Current storyboard

File:
`E:\\AI-Video-Production\\output\\20261107_123353_How_black_holes_work.json`

-   Title: `How Black Holes Work`
-   Topic: `How black holes work`
-   Audience: `General audience`
-   Duration: `56` seconds (scene durations 9, 9, 9.5, 10, 9, 9.5 s;
    extended from 9 s each so revised narration fits each scene with
    >= 0.5 s padding; still inside the 45--60 s spec)
-   Scenes: `6`
-   Status: `narration_revised` (production_status field)

Narration (revised 2026-11-07 for scientific accuracy and scene pacing;
original text preserved in
`output\archive\20261107_123353_How_black_holes_work.original.json`):
1.  "Black holes are regions of space where gravity is so strong that
    nothing can escape --- not matter, and not even light itself."
2.  "One way they form is when a massive star runs out of fuel and
    collapses under its own weight into an extremely dense core."
3.  "The boundary where escape becomes impossible is the event
    horizon --- the point of no return, where the black hole's pull
    always wins."
4.  "Inside lies the singularity, a point of infinite density predicted
    by classical general relativity --- where known physics breaks
    down."
5.  "Near black holes, spacetime curves dramatically --- bending light
    into arcs, distorting time, and warping space all around them."
6.  "Theoretical physics also predicts Hawking radiation --- black holes
    may slowly evaporate over eons through faint quantum effects."

Revision addresses the required caveats: stellar collapse is framed as
one formation pathway, the singularity as a prediction of classical
GR, and Hawking radiation as theoretical.

Scientific review required: - Not all black holes form from massive
stars. - "Infinite density" is a prediction of classical general
relativity, not an established physical description. - Hawking radiation
is theoretically predicted and has not been directly observed from
astrophysical black holes. - Keep caveats accurate without making the
short video too technical. - Background references previously
identified: NASA black holes overview
(`https://science.nasa.gov/universe/black-holes/`) and LIGO
(`https://www.ligo.caltech.edu/`). Verify source details if needed.


Installation: `E:\\ai\\Stable Diffusion\\webui`

Checkpoint:
`E:\\ai\\Stable Diffusion\\webui\\models\\Stable-diffusion\\v1-5-pruned-emaonly.safetensors`

Startup file: `E:\\ai\\Stable Diffusion\\webui\\webui-user.bat`

Current configuration:

``` bat
@echo off

set PYTHON=E:\ai\AirLLM\py3.11.9\python.exe
set GIT=
set VENV_DIR=E:\ai\Stable Diffusion\webui\venv
set COMMANDLINE_ARGS=--api --medvram

call webui.bat
```


PyTorch: - `torch==2.1.2+cu121` - `torchvision==0.16.2+cu121` - CUDA
availability verified; RTX 4060 detected. - `--medvram` enabled. -
xformers is not installed; it is optional and not currently required.

Python 3.11.9 is not the originally recommended version for this
change Python versions without a demonstrated compatibility issue.

### 6.4 Image generation

Script: `E:\\AI-Video-Production\\scripts\\generate_scene_images.py`

generates one image at a time, and saves PNG images plus JSON metadata
sidecars. It now accepts CLI arguments (added 2026-11-07):

-   `--scenes` --- single number, range (`3-6`), or comma list
    (default: `3-6`, same as the original behavior)
-   `--suffix` --- output filename suffix (default: `v2`)
-   `--seed` --- optional seed override (default: `BASE_SEED + scene
    number`, i.e. `12345 + index`)

Prompt overrides exist for scenes 3--6; scene 5 also has a
scene-specific negative override (`NEGATIVE_OVERRIDES`) that blocks
"bright glowing center, sun, bright star surface, lens flare". The
scene-5 prompt explicitly uses "black hole silhouette ... Einstein
ring ... warped starlight" phrasing. Metadata sidecars record the
actual negative prompt used.

Final approved images (user approved 2026-11-07):

-   Scene 1: `images\\scene_01.png`
-   Scene 2: `images\\scene_02.png`
-   Scene 3: `images\\scene_03_v2.png`
-   Scene 4: `images\\scene_04_v2.png`
-   Scene 5: `images\\scene_05_v3b.png` (seed 52350; alternate candidates
    v3a/v3c in `images\\archive\\`)
-   Scene 6: `images\\scene_06_v2.png`

The mapping with full generation metadata is stored in
`images\\approved_set.json`; downstream scripts must read scenes from
this manifest, not by globbing file names.

Pillow (`PIL`) is not installed in Python 3.11. Do not install it just
for PNG verification; standard-library verification already succeeded.
If Pillow becomes genuinely necessary, first check whether another
installed Python environment has it.

### 6.5 Contact sheet and visual review

Contact sheet: `E:\\AI-Video-Production\\images\\contact_sheet_v3.jpg`
(1536 × 1536, 3-column × 2-row layout of the approved set; built with
FFmpeg `hstack`+`vstack`). Older sheets are in `images\\archive\\`.

Review history: the first-pass images for scenes 3--6 were judged
unusable/weak. Replacement passes produced the approved set above.
Rejected candidates are preserved in `images\\archive\\` and must not
be used downstream.

Visual style: - Deep navy/black space background - Orange/gold and blue
highlights - Cinematic science-documentary look - Vertical composition -
No text, labels, logos, or watermarks

Scientific image constraints honored in the approved set: - No
singularity portrayed as a visible white dot (scene 4 is an abstract
warp grid with a dark focal region). - Nothing escapes from inside the
event horizon (scene 6 shows only a subtle glow outside it). - Scene 5
shows light visibly bending around dark bodies with a warped
background galaxy.

### 6.6 TTS (Kokoro-82M) --- installed and validated

-   Engine: Kokoro-82M v1.0 (`hexgrad/Kokoro-82M`), voice `af_heart`
    (US female), language code `a` (en-US), speed 1.0.
-   Environment: dedicated venv `E:\\AI-Video-Production\\venv-tts`
    (Python 3.11.9). User approved the installation explicitly.
-   Model weights: downloaded into
    `E:\\AI-Video-Production\\models\\huggingface` via `HF_HOME` --- no
    cache on C: (project rule honored).
-   espeak-ng 1.52.0 (installed by the user) plus the bundled
    `espeakng-loader` package serve as phonemization fallback.
-   Runs on CPU at ~1.7x real time (5.9 s audio in 3.5 s); no GPU
    needed, leaving the RTX 4060 free for image work.
-   Scripts: `scripts\\test_kokoro.py` (single-segment test) and
    `scripts\\generate_narration.py` (per-scene generation).
-   Output: `audio\\scene_01.wav` ... `audio\\scene_06.wav` --- mono,
    16-bit PCM, 24000 Hz, peak-normalized to 0.89 (~ -1 dBFS) for
    music-mixing headroom; per-scene duration stored in
    `audio\\scene_XX_metadata.json`.
-   Measured narration durations: 7.92, 7.92, 8.78, 9.00, 8.25, 8.60 s
    (total 50.48 s inside the 56 s timeline). Kokoro synthesis is
    deterministic for fixed text/voice/speed.
-   First-pass (short) narration WAVs are archived in
    `audio\\archive\\`.
-   Note: Kokoro does NOT support Filipino/Tagalog; user chose English
    narration for this video.

### 6.7 One-click orchestrator (Task 8) --- built and QA-tested

`scripts/run_video.py` + `make_video.bat` (2026-11-07):

-   Input contract: `inbox/<name>/prompt.txt` + 1--12 media files
    (images png/jpg/jpeg/webp, video clips
    mp4/mov/mkv/avi/webm/m4v/mpg/mpeg/flv/wmv, or animated GIFs;
    filename order = scene order).
-   Fully automatic: storyboard (LM Studio) -> archive-first staging of
    images/audio/subtitles -> normalize user media (images to 512x768,
    clips/GIFs probed for duration) -> manifest rebuild -> Kokoro
    narration -> auto-fit scene durations (narration + 0.9 s, or clip
    length up to 15 s/scene, rounded up to 0.5 s) -> subtitles (auto
    two-cue splits) with hard verification -> assembly (images keep Ken
    Burns; clips/GIFs trimmed or frozen; crossfades between scenes) ->
    QA gates -> publishing kit + SRT sidecar.
-   `--storyboard <path>` reuses an existing storyboard (LM Studio not
    needed); `--no-open` suppresses Explorer; logs land in
    `logs/<stamp>_<name>.log`.
    so the VRAM rule is respected by construction.
-   Offline end-to-end QA test passed 2026-11-07 16:55: 57.0 s MP4
    (auto-fit extended scenes 3/5), 1080x1920, h264/yuv420p, aac,
    max volume -0.9 dB, kit + sidecar SRT correct. Run-1 working files
    fully restored afterward; test artifacts kept in the archives and
    `output/` (20261107_165512_qa_full_pipeline.mp4).
-   Still to validate live: the LM Studio storyboard generation path
    inside the orchestrator (needs LM Studio + Qwythos running).

## 7. Current status

  Component                                Status
  ---------------------------------------- -----------
  Hardware/environment assessment          Complete
  Qwythos model selection for storyboard   Complete
  LM Studio local API                      Working
  Storyboard generation                    Working
  Storyboard narration revision            Complete (56 s timeline)
  SD 1.5 checkpoint                        Working
  Image-generation API                     Working
  Final six images                         Approved (approved_set.json)
  PNG integrity validation                 Passed
  Contact sheet v3                         Created
  eSpeak NG install                        Complete (system PATH)
  TTS selection/install (Kokoro-82M)       Complete (venv-tts)
  Narration audio (6 segments)             Complete and verified
  Subtitles (SRT, 12 cues)                 Complete and verified
  FFmpeg animation                         Complete (assemble_video.py)
  Final MP4 (20261107_1552)                Approved by user (2026-11-07)
  Optional background music                Not requested yet
  Quality assurance                        Technical checks passed;
                                           video approved by user
  Publishing kit (FB Reels/YT Shorts)      Complete
                                           (output\\...publishing.json)
  End-to-end automation                    Complete (Task 8:
                                           run_video.py + make_video.bat;
                                           QA test OK)
  Mixed media (images/clips/GIFs)          Complete + QA-tested
                                           (20261107_204748)

## 8. Immediate next tasks

Completed in the 2026-11-07 session (details in sections 6.2, 6.4,
6.5, 6.6):

-   Task 1 (images): scenes 3--6 replaced and approved; scenes 1--2
    preserved. Final set mapped in `images\\approved_set.json`.
-   Task 2 (narration revision): revised lines applied to the
    storyboard JSON and the manifest; scene durations set to
    9/9/9.5/10/9/9.5 s (56 s total). Original storyboard preserved in
    `output\\archive\\`.
-   Task 3 (language/voice): user chose English and voice `af_heart`;
    Kokoro-82M installed and validated (see 6.6).
-   Task 4 (narration audio): six per-scene WAVs generated,
    peak-normalized to 0.89, verified with the Python standard
    library; per-scene durations in metadata sidecars.

### Task 5 --- Subtitles (DONE)

Generate SRT first, then optionally ASS for styling. Use readable,
high-contrast subtitles in a mobile-safe region (roughly the middle
band, lower third above platform UI), avoiding platform UI overlays.

Implementation notes:

-   Scene start offsets on the 56 s timeline: scene 1 at 0.0, scene 2
    at 9.0, scene 3 at 18.0, scene 4 at 27.5, scene 5 at 37.5, scene 6
    at 46.5 s.
-   Each scene's subtitle window should match its narration within the
    scene (start ~0.3--0.5 s after scene start), using the measured
    duration from `audio\\scene_XX_metadata.json`.
-   Long lines may need to be split into two subtitle cues for
    readability; keep wording identical to the narration text.
-   Write to `subtitles\\` (e.g. `subtitles\\narration.srt`).

### Task 6 --- FFmpeg animation and assembly (DONE)

`scripts\\assemble_video.py` renders the final MP4 via a single
`-/filter_complex` graph (FFmpeg 9 removed `-filter_complex_script`):

-   Per scene: 512x768 still -> lanczos upscale to 2560x3840 ->
    center-crop 2160x3840 (9:16) -> `zoompan` Ken Burns motion ->
    1080x1920. Never stretches anything.
-   Motions match storyboard `motion_direction`: 1 zoom-in, 2 pan-left,
    3 zoom-out, 4 pan-right, 5 slow pan, 6 zoom-out.
-   Scene durations 9/9/9.5/10/9/9.5 s with 0.5 s crossfades at
    boundaries (xfade offsets = scene starts), 0.5 s fade-in/out,
    exactly 56 s.
-   Audio: per-scene WAV delayed to scene_start+0.4 s, `amix`
    (normalize=0), resampled to 48 kHz stereo, AAC 160k.
-   Subtitles burned in via `subtitles` filter (Arial 15, white with
    black outline, bottom-center, MarginV=36 --- above platform UI);
    SRT also kept in `subtitles\\` for platform-native uploads.
-   Encoder: libx264, preset medium, CRF 18, forced `-pix_fmt yuv420p`.
-   QA verified: 1080x1920, 30 FPS (1680 frames), 56.000 s, H.264 High,
    AAC-LC stereo, mean -19 dB / max -1.0 dB (no clipping), frame
    grabs checked for composition and caption placement.
-   Current output: `output\\20261107_1552_How_black_holes_work.mp4`
    (24.8 MB). Superseded render in `output\\archive\\`.

### Task 7 --- Quality assurance and user review (DONE)

User reviewed and approved the final MP4 on 2026-11-07. Technical QA:
1080×1920, 30 FPS (1680 frames), 56.000 s, H.264 High yuv420p,
AAC-LC stereo 48 kHz, mean −19 dB / max −1.0 dB (no clipping), frame
grabs verified for composition and caption placement.

Publishing kit: `output\\20261107_1552_How_black_holes_work.publishing.json`
--- per-platform titles, descriptions, hashtags, caption-upload notes
(burned-in captions primary; SRT also side-loaded on YouTube).

### Task 8 --- Reusable automation (DONE 2026-11-07)

Built and QA-tested; see section 6.7. Priorities preserved: per-run
archive-first staging, existing narration/subtitle/assembly standards
reused unchanged, logs in `logs/`, nothing ever deleted. Completed validation: LM Studio storyboard path ran live on a real topic (stamp 20261108_030815, slug webdev21; QA passed, 21.0s mixed media).

## 9. Architecture

``` text
TOPIC
  |
  v
QWYTHOS 9B MTP via LM Studio
  |
  v
STORYBOARD JSON
  |
  v
FACT-CHECK / NARRATION REVIEW
  |
  v
IMAGE PROMPTS
  |
  v
  |
  v
APPROVED SCENE IMAGES
  |
  v
LOCAL TTS
  |
  v
NARRATION AUDIO
  |
  v
SUBTITLE GENERATION
  |
  v
FFMPEG PAN / ZOOM / TRANSITIONS / MIX
  |
  v
FINAL MP4
  |
  v
QUALITY ASSURANCE
  |
  +----> FACEBOOK REELS
  |
  +----> YOUTUBE SHORTS
```

## 10. Instructions to the OpenCode agent

Treat this document as project context, not permission for broad
changes.

1.  Inspect current files before modifying them.
2.  Preserve working scripts and assets.
3.  Do not overwrite scenes 1 and 2.
4.  Make the smallest change that accomplishes the current task.
5.  Explain nontrivial changes before applying them.
6.  Verify paths if the workspace differs.
7.  Do not install packages or download models without demonstrating why
    they are needed.
8.  Do not switch Python environments casually.
9.  Do not run Qwythos and SD image generation concurrently on the 8 GB
    GPU unless resource usage is checked.
10. Run syntax checks and focused tests after code changes.
11. Report exact changed files, commands, and test results.
12. Do not claim completion until outputs are verified.
13. Keep generated artifacts on drive E:.
14. Do not refactor the entire pipeline before the first video is
    complete and validated.
15. Ask the user only when a decision is genuinely required.

### First action

ICM integration (documentation-only layer + Obsidian vault + Graphify) is now in place.
See `_core/CONTEXT.md` for the layered entry point and `CLAUDE.md` for Layer 0.

Next steps (updated 2026-11-08):
1. Live storyboard path validated (webdev21); publish/refresh tasks waived by user.
2. Optional: run `scripts/graph_rebuild.bat` after code changes to refresh `graphify-out/`.
3. Open `vault/` as an Obsidian vault to browse run notes and resources.
4. Desktop UI implementation approved and in progress.

`PROJECT_CONTEXT.md` and `OPENCODE_TASK.md` are kept for one transition cycle; their
content is being migrated into the ICM layers (`_core/`, `_config/`, `pipeline/*/CONTEXT.md`).
