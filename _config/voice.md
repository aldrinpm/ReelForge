# Voice configuration (canonical source)

Two engines, one contract: both write `audio/scene_XX.wav` (24 kHz mono,
peak-normalized to 0.89 = -1 dBFS) plus a metadata sidecar, so subtitles,
assembly and QA never care which one produced the voice.

## 1. Kokoro presets (default)

Engine: Kokoro-82M (CPU only, `venv-tts`). English only ('a' US, 'b' British).
No Filipino.

Default voice: af_heart (en-US, female).
Speed: 1.0. Sample rate: 24000 Hz. Target peak: 0.89 (-1 dBFS).

Available voices (probe at runtime; availability depends on installed kokoro):
US female: af_heart, af_alloy, af_aoede, af_bella, af_jessica, af_kore, af_nicole,
  af_nova, af_river, af_sarah, af_sky
US male: am_adam, am_echo, am_eric, am_fenrir, am_liam, am_michael, am_onyx, am_puck, am_santa
British female: bf_alice, bf_emma, bf_isabella, bf_lily
British male: bm_daniel, bm_fable, bm_george, bm_lewis

Override: `--voice <code>` on generate_narration.py / run_video.py, or config.json tts.voice.
Preview: `scripts/test_kokoro.py` or `generate_narration.py --preview`.
List: `generate_narration.py --list-voices`.

## 2. Voice cloning (your own voice, or any reference WAV)

Engine: Chatterbox TTS 0.5B (MIT licence), CPU only, in its own venv
(`venv-clone`). Kokoro's `venv-tts` is never touched, so presets keep working.

Script: `scripts/clone_narration.py` (run with `venv-clone/Scripts/python.exe`).
Zero-shot: the reference clip is a speaker prompt, not copied audio.

### Reference clip rules
- 5-20 s of clean, single-speaker speech. Longer clips are trimmed to the
  first 20 s; the original file is never modified (a 24 kHz mono copy is
  written to `audio/` when conversion is needed).
- Conversion resamples properly (librosa). Writing 16 kHz samples into a
  file labelled 24 kHz played the speaker 1.5x fast and cloned a higher
  voice (188 Hz -> 271 Hz median F0), so that path is gone.
- The 20 s cut backs off up to 0.5 s to the quietest 50 ms window, so the
  prompt never ends mid-word.
- Any sample rate / channel count is accepted (wav, mp3, flac, m4a, ogg, aiff).
- One speaker only, no music bed, low room noise.

### Knobs
- `--exaggeration` 0.0-1.0+ (default 0.5): emotion intensity.
- `--cfg-weight` 0.0-1.0 (default 0.5): lower = slower, more deliberate pace;
  higher = tighter adherence to the reference delivery.
- No speed control: pace comes from `--cfg-weight` (Kokoro's `--tts-speed`
  is ignored in clone mode).

### Commands
```
# preview a clone before committing to a run
venv-clone\Scripts\python.exe scripts\clone_narration.py --reference "E:\path\my_voice.wav" --preview

# full run with a cloned voice (UI: Voice source -> Cloned voice)
python scripts\run_video.py --name <slug> --scenes <scenes.json> --media <files> --voice-ref "E:\path\my_voice.wav"
```

Config keys (config.json `tts`): `clone_ref` (reference WAV path; empty = use
Kokoro), `clone_exaggeration`, `clone_cfg_weight`.

### Cost and speed
CPU inference. Expect roughly 1-4x real time per scene on the Ryzen 7 5700X,
so a 6-scene 60 s video takes a few minutes; narration is unattended.
No VRAM is used, so Stable Diffusion / Qwythos contention never applies.
Every generated WAV carries Chatterbox's PerTh watermark.

### Installation (one-time)
```
E:\ai\AirLLM\py3.11.9\python.exe -m venv venv-clone
venv-clone\Scripts\python.exe -m pip install chatterbox-tts "setuptools<81"
```
The `setuptools<81` pin is required: Chatterbox's watermarker (`resemble-perth`)
imports `pkg_resources`, which setuptools 81+ removed.
Weights (`ResembleAI/chatterbox`) download once into `HF_HOME`
(`models/huggingface`) — about 2 GB, kept on E:.

### Consent
Clone only voices you have the right to use. Chatterbox is MIT-licensed, but
the voice in the reference clip is not: get permission before narrating a
public video in someone else's voice.
