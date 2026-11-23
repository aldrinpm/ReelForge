"""Generate per-scene narration WAVs in a cloned voice (Chatterbox TTS).

Zero-shot voice cloning: point `--reference` at any WAV (your own recording,
or another speaker's clip) and every scene's narration is spoken in that
voice. This is the clone alternative to the Kokoro preset voices in
generate_narration.py; both write the same artifacts so the rest of the
pipeline (subtitles, assembly, QA) is unchanged.

Runs in venv-clone (Chatterbox 0.5B, MIT licence, CPU only) - never in
venv-tts, which stays pinned to Kokoro. Weights download once to
models/huggingface (HF_HOME) and stay on drive E:.

The reference clip is used as a speaker prompt, not copied as audio:
- 5-20 s of clean, single-speaker speech works best
- anything longer is trimmed to the first 20 s
- any sample rate/channel layout is accepted (read via soundfile)

Output per scene is 24 kHz mono, peak-normalized to -1 dBFS (-0.89), with a
metadata sidecar matching the Kokoro sidecar fields plus the clone settings.
Chatterbox embeds its PerTh watermark in every generated WAV.
"""
import os

os.environ.setdefault(
    "HF_HOME", r"E:\AI-Video-Production\models\huggingface"
)

import argparse
import json
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg_mod

ROOT = Path(r"E:\AI-Video-Production")
MANIFEST = ROOT / "images" / "approved_set.json"
OUTPUT_DIR = ROOT / "audio"

SAMPLE_RATE = 24000
TARGET_PEAK = 0.89
MAX_REFERENCE_SECONDS = 20.0
MAX_CHUNK_CHARS = 220

PREVIEW_TEXT = "Hello! This is a preview of the cloned voice for your video narration."

AUDIO_EXTS = (".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aiff", ".aif")


def load_model(device="cpu"):
    from chatterbox.tts import ChatterboxTTS

    return ChatterboxTTS.from_pretrained(device=device)


def trim_at_silence(audio, sample_rate, limit_seconds):
    """Cut to `limit_seconds` without slicing a word in half.

    Steps back up to 0.5 s from the hard limit to the quietest 50 ms window
    (a pause between words); falls back to the hard limit when the clip has
    no usable gap there.
    """
    limit = int(limit_seconds * sample_rate)
    if len(audio) <= limit:
        return audio
    window = int(0.05 * sample_rate)
    floor = max(0, limit - int(0.5 * sample_rate))
    best_index, best_rms = limit, None
    for start in range(floor, limit - window + 1, window // 2):
        frame = audio[start:start + window]
        rms = float(np.sqrt(np.mean(frame.astype(np.float64) ** 2)))
        if best_rms is None or rms < best_rms:
            best_index, best_rms = start, rms
    return audio[:best_index]


def load_reference(path, out_path=None):
    """Decode the reference clip to 24 kHz mono and cap it at 20 s.

    Returns the path Chatterbox should read. Decoding goes through librosa,
    which resamples properly: the earlier soundfile path wrote 16 kHz samples
    into a file labelled 24 kHz, which played the speaker back 1.5x fast and
    cloned a higher voice (188 Hz -> 271 Hz median F0). When the clip is
    already 24 kHz mono and short enough, the original file is used as-is.
    """
    reference = Path(path)
    if not reference.is_file():
        raise SystemExit(f"Reference WAV not found: {reference}")
    if reference.suffix.lower() not in AUDIO_EXTS:
        raise SystemExit(
            f"Unsupported reference format '{reference.suffix}'. "
            f"Supported: {', '.join(AUDIO_EXTS)}"
        )

    try:
        import librosa

        info = sf.info(str(reference))
        duration = info.frames / float(info.samplerate)
        mono, _ = librosa.load(
            str(reference), sr=SAMPLE_RATE, mono=True, dtype="float32"
        )
    except Exception as error:  # noqa: BLE001 - surface the real reason
        raise SystemExit(f"Could not read reference audio: {error}")

    mono = trim_at_silence(mono, SAMPLE_RATE, MAX_REFERENCE_SECONDS)
    used_seconds = len(mono) / float(SAMPLE_RATE)
    needs_copy = (
        info.samplerate != SAMPLE_RATE
        or info.channels > 1
        or duration > MAX_REFERENCE_SECONDS
    )
    if not needs_copy:
        return str(reference), info.samplerate, duration

    out_path = Path(out_path) if out_path else (
        OUTPUT_DIR / f"reference_{reference.stem}_24k.wav"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_path), mono, SAMPLE_RATE)
    return str(out_path), info.samplerate, used_seconds


def chunk_text(text, limit=MAX_CHUNK_CHARS):
    """Split narration into sentence-sized chunks Chatterbox handles well."""
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return [text]
    pieces, current = [], ""
    for sentence in text.replace("? ", "?|").replace("! ", "!|").replace(". ", ".|").split("|"):
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(current) + len(sentence) + 1 <= limit or not current:
            current = f"{current} {sentence}".strip()
        else:
            pieces.append(current)
            current = sentence
    if current:
        pieces.append(current)
    return pieces


def synthesize(model, text, reference, exaggeration, cfg_weight):
    chunks = []
    for chunk in chunk_text(text):
        wav = model.generate(
            chunk,
            audio_prompt_path=reference,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
        )
        chunks.append(wav.squeeze(0).cpu().numpy())
        # Short breath between sentences so chunks do not butt together.
        if len(chunks) > 1:
            chunks.append(np.zeros(int(0.12 * SAMPLE_RATE), dtype=np.float32))
    if not chunks:
        raise RuntimeError(f"No audio produced for text: {text!r}")
    return np.concatenate(chunks)


def main():
    parser = argparse.ArgumentParser(
        description="Generate per-scene narration in a cloned voice (Chatterbox TTS)."
    )
    parser.add_argument("--reference", required=True,
                        help="Reference WAV of the voice to clone (5-20 s works best)")
    parser.add_argument("--exaggeration", type=float, default=None,
                        help="Emotion intensity, 0.0-1.0+ (default 0.5)")
    parser.add_argument("--cfg-weight", type=float, default=None, dest="cfg_weight",
                        help="Pace/adherence weight, 0.0-1.0 (default 0.5)")
    parser.add_argument("--device", default="cpu", help="Torch device (default cpu)")
    parser.add_argument("--preview", action="store_true",
                        help="Write a short preview WAV instead of all scenes")
    parser.add_argument("--manifest", default=str(MANIFEST),
                        help="Approved image-set manifest")
    args = parser.parse_args()

    cfg = cfg_mod.load_config()
    clone_cfg = cfg_mod.resolve_clone_config(
        cfg, {"exaggeration": args.exaggeration, "cfg_weight": args.cfg_weight}
    )
    exaggeration = clone_cfg["exaggeration"]
    cfg_weight = clone_cfg["cfg_weight"]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    reference, ref_sr, ref_seconds = load_reference(args.reference)

    start = time.time()
    model = load_model(args.device)
    print(
        f"Chatterbox ready in {time.time() - start:.1f}s "
        f"(device={args.device}, reference={Path(args.reference).name}, "
        f"{ref_seconds:.1f}s @ {ref_sr} Hz)"
    )
    print(f"Clone settings: exaggeration={exaggeration}, cfg_weight={cfg_weight}\n")

    if args.preview:
        preview_path = OUTPUT_DIR / "preview_clone.wav"
        audio = synthesize(model, PREVIEW_TEXT, reference, exaggeration, cfg_weight)
        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        gain = TARGET_PEAK / peak if peak > 0 else 1.0
        sf.write(str(preview_path), audio * gain, SAMPLE_RATE)
        print(f"Preview written: {preview_path}")
        return

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scenes = manifest.get("scenes", [])
    if len(scenes) < 1:
        raise SystemExit(f"Expected at least 1 scene in manifest, found {len(scenes)}.")

    total_target = sum(entry["duration_seconds"] for entry in scenes)
    total_seconds = 0.0

    for entry in scenes:
        scene_number = entry["scene_number"]
        narration = entry["narration"].strip()
        target = entry["duration_seconds"]

        start = time.time()
        audio = synthesize(model, narration, reference, exaggeration, cfg_weight)
        synth_seconds = time.time() - start

        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        gain = TARGET_PEAK / peak if peak > 0 else 1.0
        normalized = audio * gain

        duration = len(normalized) / SAMPLE_RATE
        total_seconds += duration

        wav_path = OUTPUT_DIR / f"scene_{scene_number:02d}.wav"
        meta_path = OUTPUT_DIR / f"scene_{scene_number:02d}_metadata.json"

        sf.write(str(wav_path), normalized, SAMPLE_RATE)

        meta_path.write_text(
            json.dumps(
                {
                    "scene_number": scene_number,
                    "source_image": entry.get("image", ""),
                    "narration": narration,
                    "on_screen_text": entry.get("on_screen_text", ""),
                    "engine": "chatterbox-tts (voice clone)",
                    "voice": f"clone:{Path(args.reference).name}",
                    "voice_reference": str(Path(args.reference).resolve()),
                    "exaggeration": exaggeration,
                    "cfg_weight": cfg_weight,
                    "language": "en",
                    "sample_rate": SAMPLE_RATE,
                    "synth_realtime_seconds": round(synth_seconds, 3),
                    "peak_before_normalize": round(peak, 6),
                    "gain_applied": round(gain, 6),
                    "target_peak": TARGET_PEAK,
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
            f"(target {target}s, synth {synth_seconds:.1f}s) [{flag}] -> {wav_path.name}"
        )

    print(f"\nTotal narration: {total_seconds:.2f}s (video timeline: {total_target}s)")
    print("===== CLONED NARRATION GENERATION COMPLETE =====")


if __name__ == "__main__":
    main()
