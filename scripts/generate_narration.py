"""Generate per-scene narration WAVs with Kokoro-82M.

Reads the approved image set manifest for the narration text of each
scene, synthesizes one WAV per scene on CPU, peak-normalizes each
segment to -1 dBFS, and writes a metadata sidecar per scene containing
the synthesized duration for later subtitle scheduling.

Voice and speed are configurable via CLI or config.json (default af_heart).
"""
import os

os.environ["HF_HOME"] = r"E:\AI-Video-Production\models\huggingface"

import argparse
import json
import sys
import time
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows to handle Unicode from LLM responses
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import soundfile as sf
from kokoro import KPipeline

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg_mod

ROOT = Path(r"E:\AI-Video-Production")
MANIFEST = ROOT / "images" / "approved_set.json"
OUTPUT_DIR = ROOT / "audio"

KOKORO_VOICES = [
    "af_heart", "af_alloy", "af_aoede", "af_bella", "af_jessica", "af_kore",
    "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",
    "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam", "am_michael",
    "am_onyx", "am_puck", "am_santa",
    "bf_alice", "bf_emma", "bf_isabella", "bf_lily",
    "bm_daniel", "bm_fable", "bm_george", "bm_lewis",
]

SAMPLE_RATE = 24000
TARGET_PEAK = 0.89


def lang_code_for(voice):
    prefix = voice[:1].lower()
    if prefix not in ("a", "b"):
        raise ValueError(f"Unsupported voice prefix '{prefix}' (expected 'a' or 'b').")
    return prefix


def probe_voice(voice):
    try:
        pipeline = KPipeline(lang_code=lang_code_for(voice), repo_id="hexgrad/Kokoro-82M")
        chunks = list(pipeline("hi", voice=voice, speed=1.0))
        return bool(chunks)
    except Exception:
        return False


def synthesize_scene(pipeline, text, voice, speed):
    chunks = []
    for gs, ps, audio in pipeline(text, voice=voice, speed=speed):
        chunks.append(audio)
    if not chunks:
        raise RuntimeError(f"No audio produced for text: {text!r}")
    return np.concatenate(chunks)


def main():
    parser = argparse.ArgumentParser(description="Generate per-scene narration WAVs with Kokoro-82M.")
    parser.add_argument("--voice", default=None, help="Kokoro voice code (e.g. af_heart)")
    parser.add_argument("--speed", type=float, default=None, help="Speech speed (default 1.0)")
    parser.add_argument("--list-voices", action="store_true", help="List available voices and exit")
    parser.add_argument("--preview", action="store_true", help="Generate a preview WAV for the selected voice")
    parser.add_argument("--manifest", default=str(MANIFEST), help="Approved image-set manifest")
    args = parser.parse_args()

    cfg = cfg_mod.load_config()
    tts_cfg = cfg_mod.resolve_tts_config(cfg, {"voice": args.voice, "speed": args.speed})
    voice = tts_cfg["voice"]
    speed = tts_cfg["speed"]

    if args.list_voices:
        print("Probing Kokoro voices (this may take a moment)...")
        available = []
        for v in KOKORO_VOICES:
            ok = probe_voice(v)
            mark = "OK" if ok else "  "
            print(f"  [{mark}] {v}  (lang={v[:1]})")
            if ok:
                available.append(v)
        print(f"\n{len(available)}/{len(KOKORO_VOICES)} voices available.")
        sys.exit(0)

    lang_code = lang_code_for(voice)

    if args.preview:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        preview_path = OUTPUT_DIR / f"preview_{voice}.wav"
        pipeline = KPipeline(lang_code=lang_code, repo_id="hexgrad/Kokoro-82M")
        text = "Hello! This is a preview of the selected voice for your video narration."
        audio = synthesize_scene(pipeline, text, voice, speed)
        peak = float(np.max(np.abs(audio)))
        gain = 0.89 / peak if peak > 0 else 1.0
        sf.write(preview_path, audio * gain, SAMPLE_RATE)
        print(f"Preview written: {preview_path}")
        sys.exit(0)

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        sys.exit(f"Manifest not found: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scenes = manifest.get("scenes", [])
    if len(scenes) < 1:
        sys.exit(f"Expected at least 1 scene in manifest, found {len(scenes)}.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total_target = sum(entry["duration_seconds"] for entry in scenes)

    start = time.time()
    pipeline = KPipeline(lang_code=lang_code, repo_id="hexgrad/Kokoro-82M")
    print(f"Pipeline ready in {time.time() - start:.1f}s  (voice={voice}, lang={lang_code}, speed={speed})\n")

    total_seconds = 0.0

    for entry in scenes:
        scene_number = entry["scene_number"]
        narration = entry["narration"].strip()
        target = entry["duration_seconds"]

        start = time.time()
        audio = synthesize_scene(pipeline, narration, voice, speed)
        synth_seconds = time.time() - start

        peak = float(np.max(np.abs(audio)))
        gain = 0.89 / peak if peak > 0 else 1.0
        normalized = audio * gain

        duration = len(normalized) / SAMPLE_RATE
        total_seconds += duration

        wav_path = OUTPUT_DIR / f"scene_{scene_number:02d}.wav"
        meta_path = OUTPUT_DIR / f"scene_{scene_number:02d}_metadata.json"

        sf.write(wav_path, normalized, SAMPLE_RATE)

        meta_path.write_text(
            json.dumps(
                {
                    "scene_number": scene_number,
                    "source_image": entry["image"],
                    "narration": narration,
                    "on_screen_text": entry["on_screen_text"],
                    "engine": "kokoro-82m v1.0",
                    "voice": voice,
                    "language": lang_code,
                    "speed": speed,
                    "sample_rate": SAMPLE_RATE,
                    "synth_realtime_seconds": synth_seconds,
                    "peak_before_normalize": round(peak, 6),
                    "gain_applied": round(gain, 6),
                    "target_peak": 0.89,
                    "target_duration_seconds": target,
                    "duration_seconds": round(duration, 3),
                    "within_target": duration <= target - 0.5,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        flag = "OK" if duration <= target - 0.5 else "LONG"
        print(
            f"Scene {scene_number}: {duration:.2f}s "
            f"(target {target}s) [{flag}] -> {wav_path.name}"
        )

    print(f"\nTotal narration: {total_seconds:.2f}s (video timeline: {total_target}s)")
    print(f"===== NARRATION GENERATION COMPLETE =====")


if __name__ == "__main__":
    main()