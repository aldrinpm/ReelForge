"""Write an Obsidian (PARA) run note for a completed video run.

Usage:
    python scripts\\write_run_note.py                 # most recent output MP4
    python scripts\\write_run_note.py --slug webdev1  # latest run for a slug
    python scripts\\write_run_note.py --mp4 output\\20261107_213642_webdev1.mp4

The note is written to vault/1. Projects/<slug>-<stamp>.md using
vault/templates/run_note.md. Plain markdown; Obsidian reads it as-is.
"""
import argparse
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(r"E:\AI-Video-Production")
OUTPUT_DIR = ROOT / "output"
VAULT_PROJECTS = ROOT / "vault" / "1. Projects"
TEMPLATE = ROOT / "vault" / "templates" / "run_note.md"


def latest_mp4(slug=None):
    candidates = sorted(OUTPUT_DIR.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
    if slug:
        candidates = [p for p in candidates if slug in p.stem]
    if not candidates:
        raise SystemExit("No matching MP4 found in output/.")
    return candidates[-1]


def main():
    parser = argparse.ArgumentParser(description="Write an Obsidian run note.")
    parser.add_argument("--mp4", default=None, help="MP4 path (default: latest)")
    parser.add_argument("--slug", default=None, help="Filter latest by slug")
    args = parser.parse_args()

    mp4 = Path(args.mp4) if args.mp4 else latest_mp4(args.slug)
    if not mp4.is_absolute():
        mp4 = ROOT / mp4
    if not mp4.exists():
        raise SystemExit(f"MP4 not found: {mp4}")

    stem = mp4.stem                      # e.g. 20261107_213642_webdev1
    parts = stem.split("_", 2)
    stamp = "_".join(parts[:2]) if len(parts) >= 2 else datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = parts[2] if len(parts) >= 3 else "run"

    manifest_path = ROOT / "images" / "approved_set.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    # Find the storyboard that matches this run's stamp (robust to stale manifests).
    storyboard_rel = manifest.get("storyboard", "")
    storyboard = {}
    candidates = sorted(OUTPUT_DIR.glob(f"{stamp}_*_storyboard.json"))
    if candidates:
        storyboard_rel = candidates[-1].relative_to(ROOT).as_posix()
    if storyboard_rel:
        sp = ROOT / storyboard_rel
        if sp.exists():
            storyboard = json.loads(sp.read_text(encoding="utf-8-sig"))

    kit_path = mp4.with_suffix(".publishing.json")
    kit = json.loads(kit_path.read_text(encoding="utf-8")) if kit_path.exists() else {}

    scenes = manifest.get("scenes", [])
    media_list = "\n".join(f"- {s.get('image', '?')} ({s.get('source_type', 'image')})" for s in scenes) or "- (none)"
    scenes_table = "| # | Duration | Narration |\n|---|---|---|\n" + "\n".join(
        f"| {s.get('scene_number')} | {s.get('duration_seconds')}s | {s.get('narration', '')[:60]} |"
        for s in scenes
    )
    fact_notes = "\n".join(f"- {n}" for n in storyboard.get("fact_check_notes", [])) or "- (none)"

    template = TEMPLATE.read_text(encoding="utf-8") if TEMPLATE.exists() else (
        "# {{title}}\n\n{{topic}}\n"
    )
    note = (template
            .replace("{{title}}", str(storyboard.get("title", slug)))
            .replace("{{date}}", datetime.now().strftime("%Y-%m-%d"))
            .replace("{{n}}", str(len(scenes)))
            .replace("{{duration}}", str(manifest.get("total_scene_duration_seconds", sum(s.get("duration_seconds", 0) for s in scenes))))
            .replace("{{mp4_path}}", str(mp4.relative_to(ROOT).as_posix()))
            .replace("{{kit_path}}", str(kit_path.relative_to(ROOT).as_posix()) if kit_path.exists() else "")
            .replace("{{topic}}", str(storyboard.get("topic", slug)))
            .replace("{{media_list}}", media_list)
            .replace("{{scenes_table}}", scenes_table)
            .replace("{{fact_check_notes}}", fact_notes)
            .replace("{{storyboard_path}}", storyboard_rel))

    VAULT_PROJECTS.mkdir(parents=True, exist_ok=True)
    out = VAULT_PROJECTS / f"{slug}-{stamp}.md"
    out.write_text(note, encoding="utf-8")
    print(f"Run note written: {out}")


if __name__ == "__main__":
    main()