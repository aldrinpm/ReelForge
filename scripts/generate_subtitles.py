"""Generate SRT subtitles synchronized to the per-scene narration.

Timing model: each scene's narration plays 0.4 s after the scene's
start on the manifest timeline; cues mirror the narration windows.
Each scene is split into two cues at a natural pause point (a manual
SPLITS override first, if it exactly reproduces that scene's narration,
otherwise an automatic midpoint punctuation split), timed
proportionally by character count. The cue texts must reproduce the
narration wording exactly (validated in-script).
"""
import argparse
import json
from pathlib import Path

ROOT = Path(r"E:\AI-Video-Production")
MANIFEST = ROOT / "images" / "approved_set.json"
AUDIO_DIR = ROOT / "audio"
OUTPUT = ROOT / "subtitles" / "how_black_holes_work.srt"

NARRATION_DELAY = 0.4  # seconds from scene start to narration start

# Manual two-cue splits for specific narrations. An override is only
# used when its join reproduces the scene narration exactly; all other
# scenes fall back to the automatic split.
SPLITS = {
    1: (
        "Black holes are regions of space where gravity is so strong",
        "that nothing can escape \u2014 not matter, and not even light itself.",
    ),
    2: (
        "One way they form is when a massive star runs out of fuel",
        "and collapses under its own weight into an extremely dense core.",
    ),
    3: (
        "The boundary where escape becomes impossible is the event horizon",
        "\u2014 the point of no return, where the black hole\u2019s pull always wins.",
    ),
    4: (
        "Inside lies the singularity, a point of infinite density",
        "predicted by classical general relativity \u2014 where known physics breaks down.",
    ),
    5: (
        "Near black holes, spacetime curves dramatically \u2014 bending light",
        "into arcs, distorting time, and warping space all around them.",
    ),
    6: (
        "Theoretical physics also predicts Hawking radiation \u2014",
        "black holes may slowly evaporate over eons through faint quantum effects.",
    ),
}

# Boundary preference for automatic splits, in priority order. The
# split always happens at a real space so that
# f"{cue_a} {cue_b}" reproduces the narration text exactly.
SEPARATORS = (" \u2014 ", " \u2013 ", ": ", "; ", ", ", " ")


def format_timestamp(seconds):
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def auto_split(narration):
    """Split narration into two cues at the most natural boundary.

    Prefers punctuation (em dash, colon, semicolon, comma) near the
    midpoint, falling back to the nearest word gap. cue_a + " " + cue_b
    always reproduces the input text.
    """
    half = len(narration) / 2

    for sep in SEPARATORS:
        starts = [
            position
            for position in range(len(narration) - len(sep) + 1)
            if narration.startswith(sep, position)
        ]
        if not starts:
            continue

        # Candidate split indices are always a real space character:
        # cue_a ends before it, cue_b starts after it.
        candidates = [position + len(sep) - 1 for position in starts]
        best = min(candidates, key=lambda p: abs(p - half))
        if 4 <= best <= len(narration) - 5:
            return narration[:best].rstrip(), narration[best:].lstrip()

    spaces = [i for i, char in enumerate(narration) if char == " "]
    if spaces:
        best = min(spaces, key=lambda p: abs(p - half))
        return narration[:best].rstrip(), narration[best:].lstrip()

    # Degenerate: no space at all, emit a single cue.
    return narration, ""


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate scene-synchronized SRT subtitles."
    )
    parser.add_argument(
        "--manifest", default=str(MANIFEST),
        help="Approved image-set manifest (default: the production one)",
    )
    parser.add_argument(
        "--audio-dir", default=str(AUDIO_DIR),
        help="Directory holding scene_XX_metadata.json duration sidecars",
    )
    parser.add_argument(
        "--out", default=str(OUTPUT), help="Output SRT path"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    manifest_path = Path(args.manifest)
    audio_dir = Path(args.audio_dir)
    output = Path(args.out)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scenes = sorted(manifest["scenes"], key=lambda s: s["scene_number"])

    # Scene start offsets on the timeline come from the manifest durations.
    scene_starts = {}
    position = 0.0
    for scene in scenes:
        scene_starts[scene["scene_number"]] = position
        position += scene["duration_seconds"]
    total = position

    cue_list = []
    for scene in scenes:
        number = scene["scene_number"]
        narration = scene["narration"]
        duration = json.loads(
            (audio_dir / f"scene_{number:02d}_metadata.json").read_text(
                encoding="utf-8"
            )
        )["duration_seconds"]

        override = SPLITS.get(number)
        if override and f"{override[0]} {override[1]}" == narration:
            cue_a, cue_b = override
        else:
            cue_a, cue_b = auto_split(narration)

        if cue_b and f"{cue_a} {cue_b}" != narration:
            raise ValueError(
                f"Scene {number}: cue texts do not reproduce the narration text."
            )

        base = scene_starts[number] + NARRATION_DELAY
        if cue_b:
            split_t = duration * len(cue_a) / (len(cue_a) + len(cue_b))
            cue_list.append((base, base + split_t, cue_a, number))
            cue_list.append((base + split_t, base + duration, cue_b, number))
        else:
            cue_list.append((base, base + duration, cue_a, number))

    output.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for index, (start, end, text, _number) in enumerate(cue_list, start=1):
        lines.append(str(index))
        lines.append(f"{format_timestamp(start)} --> {format_timestamp(end)}")
        lines.append(text)
        lines.append("")

    output.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {len(cue_list)} cues to {output}")
    print(f"Timeline: {total:.1f}s, last cue ends "
          f"{format_timestamp(cue_list[-1][1])}")
    for number in sorted(scene_starts):
        count = sum(1 for c in cue_list if c[3] == number)
        print(
            f"  Scene {number}: start "
            f"{format_timestamp(scene_starts[number] + NARRATION_DELAY)}"
            f" ({count} cues)"
        )


if __name__ == "__main__":
    main()
