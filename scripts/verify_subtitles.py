"""Verify SRT structure: parse, check monotonic timing and cue count.

Exits with code 2 when the SRT is malformed or cues overlap, so the
orchestrator can use it as a hard QA gate.
"""
import argparse
import re
import sys
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows: piped or cp1252-console streams
# would otherwise die on Unicode narration characters (e.g. \u2011)
# when cue text is printed.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_SRT = r"E:\AI-Video-Production\subtitles\how_black_holes_work.srt"


def main():
    parser = argparse.ArgumentParser(description="Verify an SRT subtitle file.")
    parser.add_argument(
        "--srt", default=DEFAULT_SRT, help="SRT file to verify"
    )
    args = parser.parse_args()

    text = Path(args.srt).read_text(encoding="utf-8")
    pattern = re.compile(
        r"(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2}):(\d{2}):(\d{2}),(\d{3})"
    )
    blocks = [b for b in text.strip().split("\n\n") if b.strip()]

    if not blocks:
        print("NO CUES FOUND")
        sys.exit(2)

    prev_end = -1.0
    monotonic = True
    for block in blocks:
        lines = block.split("\n")
        match = pattern.match(lines[1])
        if not match:
            print(f"BAD TIMESTAMP at cue {lines[0]}: {lines[1]}")
            sys.exit(2)
        start = (
            int(match.group(1)) * 3600 + int(match.group(2)) * 60
            + int(match.group(3)) + int(match.group(4)) / 1000
        )
        end = (
            int(match.group(5)) * 3600 + int(match.group(6)) * 60
            + int(match.group(7)) + int(match.group(8)) / 1000
        )
        if start < prev_end:
            monotonic = False
            print("OVERLAP at cue", lines[0])
        prev_end = end
        truncated = lines[2][:60] + ("..." if len(lines[2]) > 60 else "")
        print(f"{lines[0]:>2} {start:7.2f} -> {end:7.2f}  {truncated}")

    print("cues:", len(blocks), "| monotonic:", monotonic, "| last end:", prev_end)

    if not monotonic:
        sys.exit(2)


if __name__ == "__main__":
    main()
