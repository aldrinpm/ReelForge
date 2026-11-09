"""Kokoro-82M feasibility test: synthesize one narration segment.

Downloads the model on first run into models/huggingface (HF_HOME on E:)
and writes a single test WAV using the af_heart voice.
"""
import os

os.environ["HF_HOME"] = r"E:\AI-Video-Production\models\huggingface"

import time

import numpy as np
import soundfile as sf
from kokoro import KPipeline

TEXT = (
    "Black holes are regions where gravity is so strong that nothing, "
    "not even light, can escape."
)
VOICE = "af_heart"
SAMPLE_RATE = 24000
OUTPUT = r"E:\AI-Video-Production\audio\test_kokoro_af_heart.wav"


def main():
    start = time.time()
    pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    print(f"Pipeline ready in {time.time() - start:.1f}s")

    start = time.time()
    chunks = []
    for gs, ps, audio in pipeline(TEXT, voice=VOICE, speed=1.0):
        chunks.append(audio)
        print("  segment:", gs)

    full = np.concatenate(chunks)
    synth_seconds = time.time() - start
    duration = len(full) / SAMPLE_RATE

    OUTPUT_DIR = os.path.dirname(OUTPUT)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    sf.write(OUTPUT, full, SAMPLE_RATE)

    print(f"Synthesized {duration:.2f}s of audio in {synth_seconds:.2f}s (CPU)")
    print("Wrote:", OUTPUT)


if __name__ == "__main__":
    main()
