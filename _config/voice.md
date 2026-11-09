# Voice configuration (canonical source)

Engine: Kokoro-82M (CPU only). English only ('a' US, 'b' British). No Filipino.

Default voice: af_heart (en-US, female).
Speed: 1.0. Sample rate: 24000 Hz. Target peak: 0.89 (-1 dBFS).

Available voices (probe at runtime; availability depends on installed kokoro):
US female: af_heart, af_alloy, af_aoede, af_bella, af_jessica, af_kore, af_nicole,
  af_nova, af_river, af_sarah, af_sky
US male: am_adam, am_echo, am_eric, am_fenrir, am_liam, am_michael, am_onyx, am_puck, am_santa
British female: bf_alice, bf_emma, bf_isabella, bf_lily
British male: bm_daniel, bm_fable, bm_george, bm_lewis

Override: --voice <code> on generate_narration.py / run_video.py, or config.json tts.voice.
Preview: scripts/test_kokoro.py or generate_narration.py --preview.
List: generate_narration.py --list-voices.