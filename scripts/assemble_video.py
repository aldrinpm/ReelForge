"""Assemble the final MP4 for a multi-scene vertical video.

Reads the approved image manifest and narration audio, renders each scene
as a normalized 1080x1920 clip, crossfades between scenes, delays each
narration segment to its scene slot, burns in subtitles (SRT kept
separately for platform uploads), and encodes a 1080x1920 30 FPS
H.264/AAC MP4 on the manifest timeline.

Full-asset presentation: every source (still, clip, GIF) is *fit* into
the 9:16 frame and centered on black bars — nothing is stretched,
cropped, or cut off at any edge. Stills are held static (no Ken Burns
zoom, since any zoom crops frame edges).

Supports any number of scenes (N) and mixed image/clip/GIF sources.
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows to handle Unicode from FFmpeg/LLM output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"E:\AI-Video-Production")
MANIFEST = ROOT / "images" / "approved_set.json"
AUDIO_DIR = ROOT / "audio"
SUBTITLE_FILE = ROOT / "subtitles" / "how_black_holes_work.srt"
TEMP_DIR = ROOT / "temp"
OUTPUT_DIR = ROOT / "output"

FPS = 30
SIZE = "1080x1920"
FADE = 0.5           # crossfade duration at scene boundaries
NARRATION_DELAY = 0.4  # narration offset within each scene
# Background-music mix design (when --music is provided). A fixed
# multiplier buried tracks 15-19 dB under the voice ("added but cannot
# be heard"). Instead, the music file AND the narration segments are
# measured with volumedetect, and the music gain is computed so the bed
# sits BED_OFFSET_DB under the loudest narration segment, whatever the
# track's own mastering level was.
BED_OFFSET_DB = 6.0            # bed level below the narration (changed from 9.0 to make music audible)
NARRATION_FALLBACK_DB = -20.0  # used if no narration wav can be measured
PEAK_ROOM_DB = -3.0            # ceiling for the music branch's own peaks
MUSIC_FALLBACK_GAIN_DB = -6.0  # used if the music file can't be measured
ALIMIT_DB = -2.0               # soft ceiling on the final mix (music runs)
PEAK_ROOM_DB = ALIMIT_DB       # defined locally (was missing); limit music peaks
# Full-asset presentation
# frame with black bars. Scenes are stills held static; clips/GIFs play
# as-is. SUPERSAMPLE = 2x input resolution feeding zoompan for a
# high-quality final downscale.
SUPERSAMPLE_W, SUPERSAMPLE_H = 2160, 3840

# Per-scene presentation. Any zoompan zoom above 1.0 crops frame edges
# with every frame past 1, which is exactly the "too zoomed in, missing
# edge detail" problem — so all motions are pinned to z=1 (whole frame,
# no crop, no motion; pans have no room to move at z=1 anyway). The
# storyboard's motion_direction remains read (choose_motion) but is
# presentational only. If motion is ever wanted again, keep the zoom
# ceiling below the padding margins so content edges stay visible.
MOTIONS = {
    1: "1",
    2: "1",
    3: "1",
    4: "1",
    5: "1",
    6: "1",
}

MOTION_PRESETS = {
    "zoom_in": "1",
    "pan_left": "1",
    "zoom_out": "1",
    "pan_right": "1",
}


def choose_motion(scene, number):
    """Map a storyboard motion_direction to a Ken Burns preset."""
    text = (scene.get("motion_direction") or "").lower()
    if not text:
        return MOTIONS.get(number, MOTION_PRESETS["zoom_in"])

    if "zoom out" in text or "zoom-out" in text:
        return MOTION_PRESETS["zoom_out"]
    if "zoom" in text or "push" in text:
        return MOTION_PRESETS["zoom_in"]
    if "pan left" in text or "left" in text:
        return MOTION_PRESETS["pan_left"]
    if "pan right" in text or "right" in text:
        return MOTION_PRESETS["pan_right"]
    if ("pan" in text or "across" in text or "sweep" in text
            or "drift" in text):
        return MOTION_PRESETS["pan_right" if number % 2 else "pan_left"]

    cycle = ("zoom_in", "pan_right", "zoom_out", "pan_left")
    return MOTION_PRESETS[cycle[number % 4]]


SUBTITLE_STYLE = (
    "force_style='FontName=Arial,FontSize=15,Bold=0,"
    "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
    "Outline=2,Shadow=0,Alignment=2,MarginV=36'"
)


def prefilter_subtitles(subtitle_file):
    """Check that this ffmpeg build supports the subtitles filter."""
    probe = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "color=black:size=320x240:rate=30",
            "-frames:v", "1",
            "-vf", f"subtitles=filename=subtitles/{subtitle_file.name}",
            "-f", "null", "-",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return probe.returncode == 0


def probe_duration(path):
    """Return media duration in seconds (0.0 on failure)."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return float((result.stdout or "0").strip())
    except (ValueError, OSError):
        return 0.0


def parse_volumedetect(stderr_text):
    """Extract (mean_volume, max_volume) dB floats from volumedetect output."""
    mean = peak = None
    for line in (stderr_text or "").splitlines():
        try:
            if "mean_volume:" in line:
                mean = float(
                    line.split("mean_volume:")[1].replace("dB", "").strip()
                )
            elif "max_volume:" in line:
                peak = float(
                    line.split("max_volume:")[1].replace("dB", "").strip()
                )
        except ValueError:
            continue
    return mean, peak


def audio_levels(path):
    """Measure a file's audio levels; returns (mean_volume, max_volume) dB."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-i", str(path),
             "-map", "0:a:0", "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except OSError:
        return None, None
    return parse_volumedetect(result.stderr)


def compute_music_gain(music_path, scenes):
    """Gain (dB) that parks the music bed BED_OFFSET_DB under the loudest
    narration segment, regardless of how the source track was mastered.
    Falls back to a fixed gain when levels can't be measured.

    Uses the narration's *peak* volume as reference (not mean), because
    speech has high dynamic range (mean ~ -20 dB, peak ~ -1 dB), while
    music has low dynamic range (mean ≈ peak). Using mean would bury
    the music 20+ dB too low.
    """
    music_mean, music_max = audio_levels(music_path)
    if music_mean is None:
        print(f"WARNING: could not measure '{music_path.name}'; "
              f"using fixed gain {MUSIC_FALLBACK_GAIN_DB:+g} dB")
        return MUSIC_FALLBACK_GAIN_DB
    narr_peak = None
    for scene in scenes:
        wav = AUDIO_DIR / f"scene_{scene['scene_number']:02d}.wav"
        if not wav.exists():
            continue
        _, seg_max = audio_levels(wav)
        if seg_max is not None and (narr_peak is None or seg_max > narr_peak):
            narr_peak = seg_max
    if narr_peak is None:
        narr_peak = NARRATION_FALLBACK_DB + 6.0  # fallback: assume ~6 dB crest
    # Target: music peak should be BED_OFFSET_DB below narration peak
    gain = (narr_peak - BED_OFFSET_DB) - music_max
    # Safety: keep music peaks out of the red
    if music_max is not None and music_max + gain > PEAK_ROOM_DB:
        gain = PEAK_ROOM_DB - music_max
    return round(max(gain, -30.0), 1)     # but never strangle the track


def run_ffmpeg(cmd, label):
    result = subprocess.run(
        cmd, cwd=str(ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if result.returncode != 0:
        tail = (result.stderr or "").strip()[-2000:]
        raise RuntimeError(f"{label} failed (exit {result.returncode}): {tail}")
    return result


def write_overlay_text(scene_number, text):
    """Write on_screen_text to a file for FFmpeg drawtext textfile mode."""
    path = TEMP_DIR / f"overlay_{scene_number:02d}.txt"
    path.write_text(text, encoding="utf-8")
    return path


def overlay_drawtext(scene, duration, settings):
    """Return a drawtext filter fragment (or '') for the scene's on_screen_text."""
    if not settings.get("enabled", True):
        return ""
    text = (scene.get("on_screen_text") or "").strip()
    if not text:
        return ""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    txt_path = write_overlay_text(scene["scene_number"], text)
    # FFmpeg path with forward slashes
    txt_ff = str(txt_path).replace("\\", "/").replace(":", "\\:")

    dur = settings.get("duration", 3.0)
    if dur <= 0:
        dur = duration
    start = 0.3
    end = min(duration, start + dur)

    pos = settings.get("position", "top")
    if pos == "top":
        y_expr = "80"
    elif pos == "center":
        y_expr = "(h-text_h)/2"
    else:  # bottom
        y_expr = "h-text_h-120"

    fontsize = settings.get("fontsize", 52)
    _font_path = "C:/Windows/Fonts/arialbd.ttf"
    if not Path(_font_path).exists():
        _font_path = "C:/Windows/Fonts/arial.ttf"
    fontfile = _font_path.replace(":", "\\:")

    # Split text into individual lines (preserve newlines from textarea).
    # Each line gets its own drawtext filter so every line is centered
    # independently and never cropped at either frame edge.
    lines = text.split("\n")
    filters = []
    for i, line in enumerate(lines):
        # Escape single quotes and backslashes for FFmpeg drawtext text= option
        safe_line = line.replace("\\", "\\\\").replace("'", "\\'")
        # Offset each line by fontsize + line_spacing so they stack vertically
        line_y = f"({y_base}) + {i} * ({fontsize} + 10)"
        filters.append(
            f",drawtext=fontfile='{fontfile}':text='{safe_line}'"
            f":expansion=none:"
            f"fontsize={fontsize}:fontcolor=white:borderw=3:bordercolor=black:"
            f"box=1:boxcolor=black@0.35:boxborderw=12:"
            f"x=(w-text_w)/2:y={line_y}:"
            f"enable='between(t,{start:.2f},{end:.2f})'"
        )
    return "".join(filters)
def normalize_image(scene, src, out, target_len, overlay_settings=None):
    """Image -> 1080x1920 full-frame static clip of target_len seconds.

    The whole image is fit (never cropped) into the 9:16 frame and
    centered on black bars; motion is pinned to z=1 so no frame edges
    are ever lost.
    """
    number = scene["scene_number"]
    frames = round(target_len * FPS)
    zoom = choose_motion(scene, number)
    overlay = overlay_drawtext(scene, target_len, overlay_settings or {})
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-loop", "1", "-i", str(src),
        "-vf",
        f"scale={SUPERSAMPLE_W}:{SUPERSAMPLE_H}:"
        f"force_original_aspect_ratio=decrease:flags=lanczos,"
        f"pad={SUPERSAMPLE_W}:{SUPERSAMPLE_H}:(ow-iw)/2:(oh-ih)/2:black,"
        f"zoompan=z='{zoom}':"
        f"x='iw/2-(iw/zoom)/2':"
        f"y='ih/2-(ih/zoom)/2':"
        f"d={frames}:s={SIZE}:fps={FPS},"
        f"format=yuv420p,setsar=1" + overlay,
        "-t", f"{target_len:.2f}",
        "-r", str(FPS),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an",
        str(out),
    ]
    run_ffmpeg(cmd, f"normalize image scene {number}")


def normalize_clip(scene, src, out, target_len, clip_duration, overlay_settings=None):
    """Video clip/GIF -> 1080x1920 clip of target_len seconds (trim or freeze).

    The clip frame is fit (never cropped) into 9:16 and centered on
    black bars, so edge detail is preserved.
    """
    number = scene["scene_number"]
    effective = min(clip_duration, target_len)
    pad = max(0.0, target_len - effective)
    overlay = overlay_drawtext(scene, target_len, overlay_settings or {})
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning"]
    if src.suffix.lower() == ".gif":
        cmd += ["-ignore_loop", "1"]
    cmd += [
        "-t", f"{target_len:.2f}", "-i", str(src),
        "-vf",
        f"scale=1080:1920:force_original_aspect_ratio=decrease,"
        f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,"
        f"fps={FPS},tpad=stop_mode=clone:stop_duration={pad:.2f},"
        f"format=yuv420p,setsar=1" + overlay,
        "-r", str(FPS),
        "-t", f"{target_len:.2f}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an",
        str(out),
    ]
    run_ffmpeg(cmd, f"normalize clip scene {number}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Assemble the final MP4 from the approved manifest."
    )
    parser.add_argument(
        "--manifest", default=str(MANIFEST),
        help="Approved image-set manifest",
    )
    parser.add_argument(
        "--srt", default=str(SUBTITLE_FILE),
        help="Subtitle file to burn in",
    )
    parser.add_argument(
        "--out", default=None,
        help="Output MP4 path (default: timestamped How_black_holes name)",
    )
    parser.add_argument(
        "--overlay", dest="overlay", action="store_true", default=True,
        help="Burn on-screen headline text per scene (default on)",
    )
    parser.add_argument(
        "--no-overlay", dest="overlay", action="store_false",
        help="Disable on-screen headline text",
    )
    parser.add_argument(
        "--overlay-duration", type=float, default=3.0,
        help="Seconds each headline is shown (0 = whole scene)",
    )
    parser.add_argument(
        "--overlay-position", default="top", choices=("top", "center", "bottom"),
        help="Headline position (default top)",
    )
    parser.add_argument(
        "--overlay-fontsize", type=int, default=52,
        help="Headline font size (default 52)",
    )
    parser.add_argument(
        "--music", default=None,
        help="Optional background music track; looped under the narration, "
             "auto-leveled below the voice with fade-in/out on the timeline",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        sys.exit(f"Manifest not found: {manifest_path}")

    subtitle_file = Path(args.srt)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scenes = sorted(manifest["scenes"], key=lambda s: s["scene_number"])
    N = len(scenes)
    if N < 1:
        sys.exit(f"Expected at least 1 scene, found {N}.")

    for scene in scenes:
        image = ROOT / "images" / scene["image"]
        wav = AUDIO_DIR / f"scene_{scene['scene_number']:02d}.wav"
        if not image.exists():
            sys.exit(f"Missing media: {image}")
        if not wav.exists():
            sys.exit(f"Missing narration: {wav}")

    if not subtitle_file.exists():
        sys.exit(f"Subtitles not found: {subtitle_file}")

    burn = prefilter_subtitles(subtitle_file)
    print("Burn subtitles in:", burn)
    if not burn:
        print("WARNING: subtitles filter unavailable; "
              "rendering without burned captions.")

    music_path = Path(args.music) if args.music else None
    music_gain = None
    if music_path is not None and not music_path.exists():
        sys.exit(f"Music file not found: {music_path}")
    if music_path is not None:
        music_gain = compute_music_gain(music_path, scenes)
        print(f"Background music: {music_path.name} "
              f"({music_gain:+g} dB gain, bed ≈ {BED_OFFSET_DB:g} dB "
              f"under the narration, proportional fades)")

    durations = {s["scene_number"]: s["duration_seconds"] for s in scenes}
    timeline = sum(durations.values())
    print(f"Scenes: {N} | Timeline: {timeline} s")

    starts = {}
    position = 0.0
    for number in sorted(durations):
        starts[number] = position
        position += durations[number]

    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    overlay_settings = {
        "enabled": args.overlay,
        "duration": args.overlay_duration,
        "position": args.overlay_position,
        "fontsize": args.overlay_fontsize,
    }

    # Pass 1: normalize each scene to a 1080x1920 intermediate.
    intermediates = []
    for scene in scenes:
        number = scene["scene_number"]
        src = ROOT / "images" / scene["image"]
        out = TEMP_DIR / f"scene_{number:02d}_norm.mp4"
        target_len = durations[number] + FADE
        stype = scene.get("source_type", "image")
        if stype == "image":
            normalize_image(scene, src, out, target_len, overlay_settings)
        else:
            clip_dur = scene.get("clip_duration", durations[number])
            if not clip_dur or clip_dur <= 0:
                clip_dur = probe_duration(src)
            if clip_dur <= 0:
                clip_dur = durations[number]
            normalize_clip(scene, src, out, target_len, clip_dur, overlay_settings)
        intermediates.append(out)
        print(f"  Normalized scene {number} ({stype}) -> {out.name}")

    # Pass 2: xfade chain + audio + subtitles + encode.
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning"]
    for inter in intermediates:
        cmd += ["-i", str(inter)]
    for scene in scenes:
        cmd += ["-i", str(AUDIO_DIR / f"scene_{scene['scene_number']:02d}.wav")]
    if music_path is not None:
        # Loop the track for as long as the timeline requires; the final
        # -t below caps the output. Index becomes 2*N (after N scene
        # videos + N narration wavs).
        cmd += ["-stream_loop", "-1", "-i", str(music_path)]

    filters = []

    # xfade chain across N normalized clips.
    if N == 1:
        video_chain = "[0:v]"
    else:
        chained = "[0:v]"
        for i in range(1, N):
            out_label = f"x{i + 1}"
            next_scene = scenes[i]
            offset = starts[next_scene["scene_number"]]
            filters.append(
                f"{chained}[{i}:v]"
                f"xfade=transition=fade:duration={FADE}:offset={offset:.2f}"
                f"[{out_label}]"
            )
            chained = f"[{out_label}]"
        video_chain = chained

    closing = f"fade=t=in:st=0:d={FADE},fade=t=out:st={timeline - FADE:.2f}:d={FADE}"
    if burn:
        closing += (
            f",subtitles=filename=subtitles/{subtitle_file.name}:"
            f"{SUBTITLE_STYLE}"
        )
    filters.append(f"{video_chain}{closing}[vout]")

    # Narration: delay each segment to scene_start + NARRATION_DELAY.
    # Rate is pinned to 48 kHz BEFORE amix so the music branch can join
    # the same amix (amix requires identical input parameters).
    delayed = []
    for i, scene in enumerate(scenes):
        number = scene["scene_number"]
        delay_ms = round((starts[number] + NARRATION_DELAY) * 1000)
        audio_idx = N + i
        filters.append(
            f"[{audio_idx}:a]adelay={delay_ms}:all=1,aresample=48000[a{number}]"
        )
        delayed.append(f"[a{number}]")

    # Background music (optional): looped for the full timeline, made
    # mono 48 kHz, gain-set below the narration, with fades proportional
    # to the timeline (short videos must not spend most of their runtime
    # inside the fade ramps — that alone made the music inaudible).
    music_inputs = []
    if music_path is not None:
        music_idx = 2 * N  # after N intermediates + N narration inputs
        fade_in = min(0.5, timeline * 0.08)
        fade_out = min(1.0, timeline * 0.10)
        fade_out_start = timeline - fade_out
        filters.append(
            f"[{music_idx}:a]"
            f"volume={music_gain:+.1f}dB,"
            f"aformat=sample_rates=48000:channel_layouts=mono,"
            f"afade=t=in:st=0:d={fade_in:.2f},"
            f"afade=t=out:st={fade_out_start:.2f}:d={fade_out:.2f}[music]"
        )
        music_inputs.append("[music]")

    mix_tail = "aresample=48000,pan=stereo|c0=c0|c1=c0"
    if music_path is not None:
        # Speech + music peaks can coincide; keep the final mix under a
        # gentle ceiling so the QA volume gate never trips on clipping.
        limit_lin = round(10 ** (ALIMIT_DB / 20), 3)
        mix_tail += f",alimiter=limit={limit_lin}:level=false"
    filters.append(
        "".join(delayed)
        + "".join(music_inputs)
        + f"amix=inputs={N + len(music_inputs)}:normalize=0:duration=longest,"
        + mix_tail + "[aout]"
    )

    filter_script = TEMP_DIR / "filter_complex.txt"
    filter_script.write_text(";\n".join(filters) + "\n", encoding="utf-8")

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    if args.out:
        output_path = Path(args.out)
    else:
        output_path = OUTPUT_DIR / f"{stamp}_How_black_holes_work.mp4"

    cmd += [
        "-/filter_complex", str(filter_script),
        "-map", "[vout]", "-map", "[aout]",
        "-t", f"{timeline:.2f}",
        "-r", str(FPS),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart",
        str(output_path),
    ]

    print("Filter graph written to:", filter_script)
    start = time.time()
    result = subprocess.run(
        cmd, cwd=str(ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    elapsed = time.time() - start

    if result.returncode != 0:
        print("FFMPEG FAILED:")
        print(result.stderr[-4000:])
        sys.exit(result.returncode)

    print(f"Render took {elapsed:.1f}s")
    print("Output:", output_path)
    print(f"Size: {output_path.stat().st_size / 1_048_576:.1f} MB")


if __name__ == "__main__":
    main()
