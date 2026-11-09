"""One-click end-to-end video pipeline (Task 8 orchestrator).

Usage:
    python run_video.py <run-name> [--storyboard PATH] [--no-open]

Input contract (created by you):
    inbox/<run-name>/prompt.txt        one-paragraph topic description
    inbox/<run-name>/<6 images>        png/jpg/jpeg/webp, in scene order

What it does (fully automatic, no review stops):
    1. Preflight: validates the inbox folder.
    2. Storyboard: generates scene breakdown locally from the prompt
       (no LLM required), or uses the provided --storyboard path.
    3. Workspace staging: archives current images/, audio/, subtitles/
       files (moved, never deleted), then normalizes the 6 supplied
       images to 512x768 (fit + pad â€” the whole asset is visible, never
       stretched or cropped) and builds the approved_set.json manifest
       + contact sheet.
    4. Narration: Kokoro af_heart via venv-tts; measured durations are
       then auto-fitted into the manifest (scene = narration + 0.9 s,
       rounded up to 0.5 s).
    5. Subtitles: generated and hard-verified (wording gate).
    6. Assembly: Ken Burns + crossfades + burned captions -> MP4.
    7. QA: ffprobe/volumedetect gates, publishing kit JSON, SRT copied
       next to the MP4. Ready to upload.

In this mode images come from user media (mixed media): your
attached images ARE the scene images. All previous project rules hold
(archive-first, no deletions;
at all). Logs land in logs/<stamp>_<run-name>.log.
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import urllib.request
from datetime import datetime
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows to handle Unicode from LLM/FFmpeg output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg_mod

ROOT = Path(r"E:\AI-Video-Production")
INBOX = ROOT / "inbox"
SCRIPTS = ROOT / "scripts"
IMAGES_DIR = ROOT / "images"
AUDIO_DIR = ROOT / "audio"
SUBTITLES_DIR = ROOT / "subtitles"
OUTPUT_DIR = ROOT / "output"
LOGS_DIR = ROOT / "logs"

BASE_PY = r"E:\ai\AirLLM\py3.11.9\python.exe"
VENV_PY = ROOT / "venv-tts" / "Scripts" / "python.exe"
MANIFEST = IMAGES_DIR / "approved_set.json"

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
CLIP_EXTS = (".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v",
             ".mpg", ".mpeg", ".flv", ".wmv")
GIF_EXTS = (".gif",)
MUSIC_EXTS = (".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac",
              ".opus", ".aiff", ".wma")
MEDIA_EXTS = IMAGE_EXTS + CLIP_EXTS + GIF_EXTS


def probe_duration(path):
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


# Fit (never crop) normalization: the whole asset is scaled to fit the
# 2:3 stage box and centered on black bars, so no left/top/right/bottom
# detail is ever lost. Downstream stages keep the same no-crop rule.
NORMALIZE_FILTER = (
    "scale=512:768:force_original_aspect_ratio=decrease,"
    "pad=512:768:(ow-iw)/2:(oh-ih)/2:black"
)


def media_type(path):
    ext = path.suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in GIF_EXTS:
        return "gif"
    if ext in CLIP_EXTS:
        return "clip"
    return None
NARRATION_LEAD = 0.4   # narration delay inside a scene (assembly matches)
TAIL_MARGIN = 0.5      # quiet tail before the next scene
DURATION_WARN = (45, 60)

# Generic words kept out of auto-generated publishing hashtags.
STOPWORDS = {
    "a", "an", "the", "of", "and", "or", "to", "in", "on", "how", "why",
    "what", "is", "are", "it", "its", "with", "for", "from", "that",
    "this", "work", "works", "video", "explain", "explained", "simple",
    "simply", "about", "into",
}


class PipelineError(Exception):
    """A stage failed; message should contain the fix."""


def slugify(name):
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
    if not slug:
        raise PipelineError(
            "Run name must contain letters or numbers "
            f"(got: {name!r})."
        )
    return slug


class Log:
    def __init__(self, path):
        self.path = path

    def __call__(self, message="", indent=False):
        line = ("    " if indent else "") + str(message)
        safe_console_print(line)
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def safe_console_print(text):
    """Print to this (cp1252) console without dying on Unicode."""
    try:
        sys.stdout.write(str(text).rstrip("\n") + "\n")
        sys.stdout.flush()
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        converted = (
            str(text).encode(encoding, errors="replace")
            .decode(encoding, errors="replace")
        )
        sys.stdout.write(converted.rstrip("\n") + "\n")
        sys.stdout.flush()


def run_step(cmd, label, cwd=None, timeout=None):
    """Run a subprocess; print its stdout; fail loudly on errors."""
    # Child scripts print file-derived text (LLM narration, SRT cues,
    # filenames) that can contain characters cp1252 cannot encode. When
    # stdout is a pipe, Python on Windows defaults to the ANSI codepage
    # and dies with UnicodeEncodeError; force UTF-8 to match the utf-8
    # decoding below.
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    result = subprocess.run(
        cmd, cwd=str(cwd) if cwd else None, capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=timeout,
        env=env, creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if result.stdout.strip():
        safe_console_print(result.stdout.rstrip())
    if result.returncode != 0:
        tail = (result.stderr or "").strip()[-1500:]
        raise PipelineError(
            f"{label} failed (exit {result.returncode}).\n"
            f"    stderr tail: {tail or '<empty>'}"
        )
    return result


def generate_storyboard_locally(topic, num_scenes):
    """Build a simple storyboard from the prompt without any LLM.

    Splits the topic into sentences and distributes them across scenes.
    Each scene maps 1:1 to a media file provided in the inbox.
    """
    total_duration = max(20, num_scenes * 8)
    total_duration = min(total_duration, 120)

    # Split topic into sentences for per-scene narration
    sentences = re.split(r"(?<=[.!?])\s+", topic.strip())
    sentences = [s for s in sentences if s]
    if not sentences:
        sentences = [topic]

    base_duration = total_duration // num_scenes
    remainder = total_duration % num_scenes

    scenes = []
    for i in range(num_scenes):
        scene_num = i + 1
        duration = base_duration + (1 if i < remainder else 0)
        narration = sentences[i] if i < len(sentences) else f"Continuing about {topic}."
        scenes.append({
            "scene_number": scene_num,
            "duration_seconds": duration,
            "narration_segment": narration,
            "on_screen_text": f"Scene {scene_num}: {topic[:40]}",
            "image_prompt": f"{topic}, educational illustration, scene {scene_num}, clear simple visuals",
            "motion_direction": "Slow zoom in",
        })

    return {
        "title": topic[:80],
        "topic": topic,
        "target_duration_seconds": total_duration,
        "scenes": scenes,
        "fact_check_notes": [],
        "source_suggestions": [],
        "narration": " ".join(sentences),
        "generated_locally": True,
    }

def validate_storyboard(storyboard, source):
    scenes = storyboard.get("scenes", [])
    if len(scenes) < 1:
        raise PipelineError(
            f"{source}: expected at least 1 scene, found {len(scenes)}."
        )
    numbers = sorted(int(s["scene_number"]) for s in scenes)
    n = len(scenes)
    if numbers != list(range(1, n + 1)):
        raise PipelineError(
            f"{source}: scene numbers are {numbers}; expected 1..{n}."
        )
    for scene in scenes:
        for key in ("narration_segment", "image_prompt", "duration_seconds"):
            if not str(scene.get(key, "")).strip():
                raise PipelineError(
                    f"{source}: scene {scene['scene_number']} "
                    f"is missing '{key}'."
                )
    total = sum(float(s["duration_seconds"]) for s in scenes)
    n = len(scenes)
    lo, hi = max(20, n * 3), min(120, n * 15)
    if not lo <= total <= hi:
        log(f"  WARNING: storyboard timeline is {total}s "
            f"(target {lo}-{hi}s); continuing.")
    return sorted(scenes, key=lambda s: int(s["scene_number"]))


def read_inbox(run_dir, slug):
    prompt_path = run_dir / "prompt.txt"
    if not prompt_path.exists():
        raise PipelineError(
            f"Missing prompt.txt in {run_dir}\n"
            "    FIX: create inbox/" + slug + "/prompt.txt containing the "
            "video topic/story you want."
        )
    topic = re.sub(r"\s+", " ", prompt_path.read_text(encoding="utf-8")).strip()
    if not topic:
        raise PipelineError(f"prompt.txt in {run_dir} is empty.")
    if len(topic) > 20000:
        raise PipelineError("prompt.txt is too long (>20000 chars).")

    sources = sorted(
        (
            item for item in run_dir.iterdir()
            if item.is_file() and item.suffix.lower() in MEDIA_EXTS
        ),
        key=lambda p: p.name.lower(),
    )
    if len(sources) < 1:
        raise PipelineError(
            f"{run_dir}: expected at least 1 media file, found 0.\n"
            "    FIX: add images (png/jpg/jpeg/webp) and/or video clips "
            "(mp4/mov/mkv/avi/webm/m4v/mpg/mpeg/flv/wmv) and/or GIFs."
        )
    if len(sources) > 12:
        raise PipelineError(
            f"{run_dir}: too many media files ({len(sources)}); max 12."
        )

    types = [media_type(p) for p in sources]
    if any(t is None for t in types):
        raise PipelineError(f"{run_dir}: unsupported file type in "
                            f"{[p.name for p in sources]}.")

    return topic, sources, types


def archive_workspace(stamp):
    """Move current working files into their archive/ folders (never delete)."""
    moved = []
    for directory in (IMAGES_DIR, AUDIO_DIR, SUBTITLES_DIR):
        if not directory.exists():
            continue
        archive_dir = directory / "archive"
        archive_dir.mkdir(exist_ok=True)
        for item in sorted(directory.iterdir()):
            if item.is_file():
                shutil.move(str(item), str(archive_dir / f"{stamp}_{item.name}"))
                moved.append(item.name)
    log(f"Archived {len(moved)} previous working files "
        f"into their archive/ folders (prefix {stamp})", indent=True)


def ffmpeg_normalize(source, target):
    run_step(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(source), "-vf", NORMALIZE_FILTER, str(target)],
        f"normalize {source.name}",
    )


def build_contact_sheet(slug, count, media_types=None):
    """Adaptive grid (up to 3 columns); clips use a midpoint frame.

    Cosmetic only: any failure returns None and the run continues.
    """
    if media_types is None:
        media_types = ["image"] * count
    cols = min(count, 3) if count > 0 else 1
    rows = (count + cols - 1) // cols

    # Representative tile per scene (mid-frame for clips/GIFs).
    reps = []
    for i in range(count):
        matches = list(IMAGES_DIR.glob(f"scene_{i + 1:02d}.*"))
        src = matches[0] if matches else None
        if src is None:
            reps.append(None)
            continue
        rep = IMAGES_DIR / f"_cs_{i + 1:02d}.png"
        if media_types[i] == "image":
            cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                   "-i", str(src),
                   "-vf", "scale=320:480:force_original_aspect_ratio=decrease,"
                          "pad=320:480:(ow-iw)/2:(oh-ih)/2:black",
                   "-frames:v", "1", str(rep)]
        else:
            dur = probe_duration(src)
            mid = max(0.0, dur / 2.0)
            cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                   "-ss", f"{mid:.2f}", "-i", str(src),
                   "-vf", "scale=320:480:force_original_aspect_ratio=decrease,"
                          "pad=320:480:(ow-iw)/2:(oh-ih)/2:black",
                   "-frames:v", "1", str(rep)]
        result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True,
                                text=True, encoding="utf-8", errors="replace",
                                creationflags=subprocess.CREATE_NO_WINDOW)
        reps.append(rep if result.returncode == 0 else None)

    # Pad to a full grid with black tiles.
    total = cols * rows
    inputs = []
    for rep in reps:
        if rep is not None:
            inputs += ["-i", str(rep)]
        else:
            inputs += ["-f", "lavfi", "-i", "color=black:size=320x480:rate=1"]
    for _ in range(total - len(reps)):
        inputs += ["-f", "lavfi", "-i", "color=black:size=320x480:rate=1"]

    filter_parts = []
    row_labels = []
    for r in range(rows):
        idxs = [r * cols + c for c in range(cols)]
        label = f"row{r}"
        in_labels = "".join(f"[{i}:v]" for i in idxs)
        filter_parts.append(f"{in_labels}hstack=inputs={cols}[{label}]")
        row_labels.append(f"[{label}]")
    if rows > 1:
        filter_parts.append("".join(row_labels) + f"vstack=inputs={rows}[out]")
        out_label = "[out]"
    else:
        out_label = "[row0]"

    out_path = IMAGES_DIR / f"contact_sheet_{slug}.jpg"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs,
           "-filter_complex", ";".join(filter_parts),
           "-map", out_label, "-frames:v", "1", "-q:v", "2", str(out_path)]
    result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                            encoding="utf-8", errors="replace",
                            creationflags=subprocess.CREATE_NO_WINDOW)

    for rep in reps:
        if rep is not None:
            try:
                rep.unlink()
            except OSError:
                pass

    return out_path if result.returncode == 0 else None


def stage_images_and_manifest(scenes, sources, media_types, slug,
                              storyboard_rel, storyboard_title):
    """Stage user media (images/clips/gifs), write sidecars, build manifest."""
    entries = []
    for scene, source, mtype in zip(scenes, sources, media_types):
        number = int(scene["scene_number"])
        duration = float(scene["duration_seconds"])
        narration = str(scene["narration_segment"]).strip()
        on_screen = str(scene.get("on_screen_text", "")).strip()
        prompt = str(scene.get("image_prompt", "")).strip()

        if mtype == "image":
            image_name = f"scene_{number:02d}.png"
            target = IMAGES_DIR / image_name
            ffmpeg_normalize(source, target)
            clip_duration = 0.0
            width, height = 512, 768
            sidecar_extra = {"normalized_filter": NORMALIZE_FILTER}
        else:
            ext = source.suffix.lower()
            image_name = f"scene_{number:02d}{ext}"
            target = IMAGES_DIR / image_name
            shutil.copyfile(str(source), str(target))
            clip_duration = probe_duration(source)
            width, height = 0, 0
            sidecar_extra = {"clip_duration_seconds": round(clip_duration, 3)}

        sidecar = {
            "scene_number": number,
            "duration_seconds": duration,
            "narration": narration,
            "on_screen_text": on_screen,
            "prompt": prompt,
            "negative_prompt": "",
            "source": "user_inbox",
            "source_file": source.name,
            "source_type": mtype,
            "width": width,
            "height": height,
            **sidecar_extra,
        }
        (IMAGES_DIR / f"scene_{number:02d}_metadata.json").write_text(
            json.dumps(sidecar, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        entries.append({
            "scene_number": number,
            "image": image_name,
            "metadata": f"scene_{number:02d}_metadata.json",
            "width": width,
            "height": height,
            "duration_seconds": duration,
            "narration": narration,
            "on_screen_text": on_screen,
            "prompt": prompt,
            "negative_prompt": "",
            "motion_direction": str(scene.get("motion_direction", "")).strip(),
            "source_type": mtype,
            "clip_duration": round(clip_duration, 3),
            "image_source": "user_inbox:" + source.name,
        })

    contact_sheet = build_contact_sheet(slug, len(scenes), media_types)
    if contact_sheet is None:
        log("  WARNING: contact sheet could not be built (cosmetic only).")

    manifest = {
        "title": storyboard_title or slug,
        "storyboard": storyboard_rel,
        "contact_sheet": contact_sheet.name if contact_sheet else "",
        "approved_on": datetime.now().strftime("%Y-%m-%d"),
        "mode": "user_media_auto",
        "scenes": entries,
    }
    MANIFEST.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log(f"Manifest written: {MANIFEST}", indent=True)


def generate_narration_and_fit(scenes, tts_cfg=None):
    """Kokoro narration, then auto-fit scene durations in the manifest."""
    voice = (tts_cfg or {}).get("voice", "af_heart")
    speed = (tts_cfg or {}).get("speed", 1.0)
    run_step(
        [str(VENV_PY), str(SCRIPTS / "generate_narration.py"),
         "--voice", voice,
         "--speed", str(speed)],
        "narration generation",
        cwd=ROOT, timeout=600,
    )

    changed = []
    for scene in scenes:
        number = int(scene["scene_number"])
        sidecar_path = AUDIO_DIR / f"scene_{number:02d}_metadata.json"
        if not sidecar_path.exists():
            break  # fewer narrated wavs than scenes; stop extending
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        measured = float(sidecar["duration_seconds"])
        required = math.ceil((measured + NARRATION_LEAD + TAIL_MARGIN) * 2) / 2
        # Clips: also respect the source clip length (cap 15s per scene).
        manifest_entry = next(
            (s for s in json.loads(MANIFEST.read_text(encoding="utf-8"))["scenes"]
             if int(s["scene_number"]) == number),
            {},
        )
        clip_dur = float(manifest_entry.get("clip_duration", 0) or 0)
        if clip_dur > 0:
            clip_cap = min(clip_dur, 15.0)
            if clip_cap > required:
                required = math.ceil(clip_cap * 2) / 2
                log(
                    f"  Scene {number}: clip is {clip_dur:.2f}s; "
                    f"extending scene to {required}s to show more of it",
                    indent=True,
                )
        if required > float(scene["duration_seconds"]):
            if not (clip_dur > 0 and required > math.ceil((measured + NARRATION_LEAD + TAIL_MARGIN) * 2) / 2):
                log(
                    f"  Scene {number}: narration {measured:.2f}s needs "
                    f"{required}s; extending scene "
                    f"{scene['duration_seconds']} -> {required}s",
                    indent=True,
                )
            scene["duration_seconds"] = required
            changed.append(number)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["scenes"] = sorted(
        manifest["scenes"], key=lambda s: s["scene_number"]
    )
    for scene in manifest["scenes"]:
        match = next(
            s for s in scenes
            if int(s["scene_number"]) == int(scene["scene_number"])
        )
        scene["duration_seconds"] = match["duration_seconds"]
    MANIFEST.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    total = sum(float(s["duration_seconds"]) for s in manifest["scenes"])
    narration_total = 0.0
    for scene in manifest["scenes"]:
        number = int(scene["scene_number"])
        sidecar = json.loads(
            (AUDIO_DIR / f"scene_{number:02d}_metadata.json").read_text(
                encoding="utf-8"
            )
        )
        narration_total += float(sidecar["duration_seconds"])
    n = len(manifest["scenes"])
    lo, hi = max(20, n * 3), min(120, n * 15)
    log(f"Narration total: {narration_total:.2f}s | "
        f"timeline: {total:.1f}s (extended scenes: "
        f"{changed or 'none'})", indent=True)
    if not lo <= total <= hi:
        log(
            f"  WARNING: timeline {total:.1f}s is outside "
            f"{lo}-{hi}s. Platforms accept up to 90s (Reels) / 60s (Shorts).",
            indent=True,
        )


def qa_check(mp4_path, timeline_seconds):
    probe = run_step(
        ["ffprobe", "-v", "error",
         "-show_entries",
         "stream=codec_name,codec_type,pix_fmt,width,height,avg_frame_rate:"
         "format=duration",
         "-of", "json", str(mp4_path)],
        "ffprobe",
    )
    data = json.loads(probe.stdout)
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if video is None or audio is None:
        raise PipelineError("QA: MP4 is missing a video or audio stream.")

    problems = []
    if (video.get("width"), video.get("height")) != (1080, 1920):
        problems.append(f"resolution {video.get('width')}x{video.get('height')}")
    if video.get("pix_fmt") != "yuv420p":
        problems.append(f"pix_fmt {video.get('pix_fmt')}")
    if video.get("codec_name") != "h264":
        problems.append(f"video codec {video.get('codec_name')}")
    if audio.get("codec_name") != "aac":
        problems.append(f"audio codec {audio.get('codec_name')}")
    duration = float(data.get("format", {}).get("duration", 0))
    if abs(duration - timeline_seconds) > 0.25:
        problems.append(
            f"duration {duration:.2f}s vs timeline {timeline_seconds:.2f}s"
        )

    volume = run_step(
        ["ffmpeg", "-hide_banner", "-i", str(mp4_path),
         "-map", "0:a:0", "-af", "volumedetect", "-f", "null", "-"],
        "volumedetect",
    )
    match = re.search(r"max_volume:\s*(-?[\d.]+)\s*dB", volume.stderr or "")
    max_volume = float(match.group(1)) if match else -99.0
    if max_volume > -0.3:
        problems.append(f"max_volume {max_volume} dB (clipping risk)")

    if problems:
        raise PipelineError("QA FAILED: " + "; ".join(problems))

    log(f"QA passed: {duration:.2f}s, {video.get('width')}x{video.get('height')}, "
        f"{video.get('codec_name')}/{video.get('pix_fmt')}, "
        f"{audio.get('codec_name')}, max_volume {max_volume} dB", indent=True)


def build_publishing_kit(storyboard, manifest, mp4_path, srt_path, stamp, slug):
    title = str(storyboard.get("title", slug)).strip()
    topic = str(storyboard.get("topic", slug)).strip()
    narration = " ".join(
        str(scene["narration"]).strip() for scene in manifest["scenes"]
    )
    sentences = re.split(r"(?<=[.!?]) +", narration)
    lead = " ".join(sentences[:2]).strip()

    caveat_list = []
    for note in storyboard.get("fact_check_notes", [])[:3]:
        note = re.sub(r"[.\s]+$", "", str(note).strip())
        if note:
            caveat_list.append(note + ".")
    caveats = " ".join(caveat_list)
    sources = "; ".join(
        str(entry.get("source_name", "")).strip()
        for entry in storyboard.get("source_suggestions", [])[:4]
    ).rstrip("; ")

    words = re.findall(r"[A-Za-z]{5,}", f"{title} {topic}")
    seen = set()
    topic_tags = []
    for word in words:
        lowered = word.lower()
        if lowered in STOPWORDS:
            continue
        tag = "#" + lowered
        if tag not in seen:
            seen.add(tag)
            topic_tags.append(tag)
    topic_tags = topic_tags[:6]

    total = round(sum(float(s["duration_seconds"]) for s in manifest["scenes"]))
    duration_str = f"{total}-second" if total != 1 else "1-second"

    fb_tags = (topic_tags + ["#reels", "#learn", "#science"])[:9]
    yt_tags = (["#Shorts"] + topic_tags)[:9]

    kit = {
        "video_file": mp4_path.relative_to(ROOT).as_posix(),
        "subtitle_file": srt_path.relative_to(ROOT).as_posix(),
        "duration_seconds": total,
        "resolution": "1080x1920",
        "aspect_ratio": "9:16",
        "platforms": {
            "facebook_reels": {
                "title": f"{title} â€” {total}-Second Explainer",
                "description": (
                    f"{lead} Runtime: {total}s. Visuals: custom scene images."
                    + (f" Facts kept responsible: {caveats}" if caveats else "")
                    + (f" Sources: {sources}" if sources else "")
                ),
                "hashtags": fb_tags,
                "notes": (
                    "Captions are burned into the video; Reels may also "
                    "auto-generate captions. Keep the burned-in captions "
                    "as primary."
                ),
            },
            "youtube_shorts": {
                "title": f"{title} â€” in {total} Seconds",
                "description": (
                    f"{lead} In under a minute: {title.lower()}."
                    + (f" Caveats: {caveats}" if caveats else "")
                    + (f" Sources: {sources}" if sources else "")
                    + " " + " ".join(yt_tags)
                ),
                "hashtags": yt_tags,
                "notes": (
                    f"Upload '{srt_path.name}' as the video's caption track "
                    "(timing matches the timeline). Vertical 9:16 and "
                    f"{total}s already qualify for Shorts."
                ),
            },
        },
        "pin_comment_suggestion": (
            caveat_list[0].rstrip(".") if caveat_list else ""
        ),
        "generated_for": f"{stamp}_{slug} via run_video.py (user images)",
    }

    kit_path = mp4_path.with_suffix(".publishing.json")
    kit_path.write_text(
        json.dumps(kit, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return kit_path


def pipeline(run_name, storyboard_arg, no_open, write_run_note=False, args=None):
    slug = slugify(run_name)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    args = args or argparse.Namespace()
    cfg = cfg_mod.load_config()
    tts_overrides = {
        "voice": getattr(args, "voice", None),
        "speed": getattr(args, "tts_speed", None),
    }
    tts_cfg = cfg_mod.resolve_tts_config(cfg, tts_overrides)
    LOGS_DIR.mkdir(exist_ok=True)
    global log
    log = Log(LOGS_DIR / f"{stamp}_{slug}.log")

    log(f"=== run_video.py | {slug} | {stamp} ===")
    run_dir = INBOX / run_name
    if not run_dir.is_dir():
        raise PipelineError(
            f"Inbox folder not found: {run_dir}\n"
            f"    FIX: create {run_dir} with prompt.txt + 6 images."
        )

    # 0. Preflight
    log("[1/7] Preflight")
    topic, sources, media_types = read_inbox(run_dir, slug)
    log(f"  Topic: {topic[:120]}{'â€¦' if len(topic) > 120 else ''}", indent=True)
    log(f"  Media ({len(sources)}): "
        f"{[(p.name, t) for p, t in zip(sources, media_types)]}", indent=True)

    # 1. Storyboard
    if storyboard_arg:
        storyboard_path = Path(storyboard_arg)
        if not storyboard_path.exists():
            raise PipelineError(f"Storyboard not found: {storyboard_path}")
        storyboard = json.loads(
            storyboard_path.read_text(encoding="utf-8-sig")
        )
        storyboard_rel = (
            storyboard_path.relative_to(ROOT).as_posix()
            if storyboard_path.is_relative_to(ROOT)
            else str(storyboard_path)
        )
        log("[2/7] Storyboard: using provided "
            f"{storyboard_path.name} (LM Studio not needed)")
    else:
        log("[2/7] Storyboard: generating locally from prompt")
        storyboard = generate_storyboard_locally(topic, len(sources))
        storyboard_name = f"{stamp}_{slug}_storyboard.json"
        storyboard_path = OUTPUT_DIR / storyboard_name
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        storyboard_path.write_text(
            json.dumps(storyboard, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        storyboard_rel = storyboard_name
        total_dur = sum(float(s["duration_seconds"]) for s in storyboard["scenes"])
        log(f"  Storyboard ready: {len(storyboard['scenes'])} scenes, "
            f"{total_dur}s total", indent=True)

    scenes = validate_storyboard(storyboard, storyboard_path.name)
    n = len(sources)
    if n == 0:
        raise PipelineError("No images found in inbox.")
    if len(scenes) > n:
        # More scenes than images: keep only first N to match staged images
        scenes = scenes[:n]
        # renumber
        for idx, sc in enumerate(scenes, start=1):
            sc['scene_number'] = idx
    if len(scenes) != n:
        # fallback: repeat scenes? no. fail with actionable message
        raise PipelineError(
            f"Storyboard has {len(scenes)} scenes but inbox has "
            f"{n} images. Add {n+len(scenes)}? Add {n} more images or change "
            f"topic to request {n} scenes."
        )
    storyboard_title = str(storyboard.get("title", "")).strip() or slug

    # 2. Stage workspace
    log("[3/7] Staging images + manifest (archiving previous run first)")
    archive_workspace(stamp)
    if not IMAGES_DIR.exists():
        IMAGES_DIR.mkdir()
    stage_images_and_manifest(scenes, sources, media_types, slug,
                              storyboard_rel, storyboard_title)

    # 3. Narration + auto-fit
    log("[4/7] Narration (Kokoro, CPU) + auto-fit scene durations")
    generate_narration_and_fit(scenes, tts_cfg)

    # 4. Subtitles + verification gate
    log("[5/7] Subtitles + verification")
    srt_path = SUBTITLES_DIR / f"{slug}.srt"
    run_step(
        [BASE_PY, str(SCRIPTS / "generate_subtitles.py"),
         "--out", str(srt_path)],
        "subtitle generation", cwd=ROOT,
    )
    run_step(
        [BASE_PY, str(SCRIPTS / "verify_subtitles.py"), "--srt", str(srt_path)],
        "subtitle verification", cwd=ROOT,
    )

    # 5. Assembly
    log("[6/7] Assembly (crossfades + burned captions)")
    mp4_path = OUTPUT_DIR / f"{stamp}_{slug}.mp4"
    assemble_cmd = [
        str(VENV_PY), str(SCRIPTS / "assemble_video.py"),
        "--srt", str(srt_path), "--out", str(mp4_path),
        ("--no-overlay" if not getattr(args, "overlay", True) else "--overlay"),
        "--overlay-duration", str(getattr(args, "overlay_duration", 3.0)),
        "--overlay-position", getattr(args, "overlay_position", "top"),
        "--overlay-fontsize", str(getattr(args, "overlay_fontsize", 52)),
    ]
    if getattr(args, "music", None):
        music_file = Path(args.music)
        if not music_file.is_file():
            raise PipelineError(f"Background music file not found: {music_file}")
        if music_file.suffix.lower() not in MUSIC_EXTS:
            raise PipelineError(
                f"Unsupported music format '{music_file.suffix}'.\n"
                f"    Supported: {', '.join(MUSIC_EXTS)}"
            )
        log(f"Background music: {music_file.name}", indent=True)
        assemble_cmd += ["--music", str(music_file)]
    run_step(assemble_cmd, "assembly", cwd=ROOT, timeout=600)
    if not mp4_path.exists():
        raise PipelineError("Assembly reported success but no MP4 exists.")

    # 6. QA + publishing kit
    log("[7/7] QA + publishing kit")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    timeline_seconds = sum(
        float(scene["duration_seconds"]) for scene in manifest["scenes"]
    )
    qa_check(mp4_path, timeline_seconds)

    sidecar_srt = mp4_path.with_suffix(".srt")
    shutil.copyfile(str(srt_path), str(sidecar_srt))
    kit_path = build_publishing_kit(
        storyboard, manifest, mp4_path, srt_path, stamp, slug
    )

    log("")
    log("=" * 60)
    log("=" * 60)
    log("READY TO UPLOAD:")
    log(f"  video:    {mp4_path.name} ({mp4_path.stat().st_size / 1_048_576:.1f} MB)")
    log(f"  captions: {sidecar_srt.name} (+ burned in)")
    log(f"  kit:      {kit_path.name}")
    log(f"  log:      {log.path}")
    log("  storyboard: " + storyboard_rel)
    if write_run_note:
        try:
            run_step(
                [BASE_PY, str(SCRIPTS / "write_run_note.py"), "--mp4", str(mp4_path)],
                "run note (Obsidian)", cwd=ROOT,
            )
        except PipelineError as note_err:
            log(f"  WARNING: run note failed (non-fatal): {note_err}", indent=True)

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="One-click video pipeline: inbox/<name> -> finished MP4."
    )
    parser.add_argument("run_name", help="Folder name under inbox/")
    parser.add_argument(
        "--storyboard", default=None,
        help="Use an existing storyboard JSON instead of LM Studio",
    )
    parser.add_argument("--no-open", action="store_true",
                        help="Do not open the output folder at the end")
    parser.add_argument("--write-run-note", action="store_true",
                        help="Write an Obsidian (PARA) run note to vault/1. Projects/")
    parser.add_argument("--voice", default=None, help="TTS voice (e.g. af_heart)")
    parser.add_argument("--tts-speed", type=float, default=None, dest="tts_speed")
    parser.add_argument("--overlay", dest="overlay", action="store_true", default=True,
                        help="Burn on-screen headline text per scene (default on)")
    parser.add_argument("--no-overlay", dest="overlay", action="store_false",
                        help="Disable on-screen headline text")
    parser.add_argument("--overlay-duration", type=float, default=3.0,
                        help="Seconds each headline is shown (0 = whole scene)")
    parser.add_argument("--overlay-position", default="top", choices=("top", "center", "bottom"),
                        help="Headline position (default top)")
    parser.add_argument("--overlay-fontsize", type=int, default=52,
                        help="Headline font size (default 52)")
    parser.add_argument(
        "--music", default=None,
        help="Background music track (mp3/wav/m4a/...); mixed under "
             "the narration with fades"
    )
    args = parser.parse_args()

    global log
    # Provisional logger before the real one exists (pre-slug failures).
    LOGS_DIR.mkdir(exist_ok=True)
    log = Log(LOGS_DIR / "boot.log")

    try:
        return pipeline(args.run_name, args.storyboard, args.no_open,
                        args.write_run_note, args)
    except PipelineError as error:
        log("PIPELINE FAILED â€” " + str(error))
        return 1
    except Exception:  # noqa: BLE001 - log everything, fail loudly
        log("PIPELINE FAILED â€” unexpected error:\n"
            + traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())

