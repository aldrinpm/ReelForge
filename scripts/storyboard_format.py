"""Storyboard text format — the single parser and validator.

Canonical plain-text storyboard structure (the format the application
reads from a text file, and the format the AI Storyboard Generator is
asked to produce):

    Title: <one-line video title>
    Description: <social post description>
    Hashtags: <#tag1 #tag2 #tag3>

    Scene 1
    Overlay: <on-screen headline, max 35 chars>
    Narration: <spoken narration for this scene>

    Scene 2
    Overlay: <on-screen headline>
    Narration: <spoken narration>

Rules the parser follows:
  - ``Title:`` / ``Description:`` / ``Hashtags:`` are optional in position
    but must appear before the first scene for the header to be read.
  - A scene header is ``Scene <number>`` (a trailing colon is allowed, and
    any text after it becomes that scene's overlay).
  - ``Overlay:`` / ``Narration:`` (a number may follow the word) set the
    current field; following non-empty lines are appended to it.
  - Everything is case-insensitive on the field names.

This module is the ONLY implementation of the format. The UI calls it via
the backend for both the text-file path and the AI path, so the two can
never drift apart.
"""
import re

MAX_OVERLAY_CHARS = 35

_TITLE_RE = re.compile(r"^Title:\s*(.*)$", re.IGNORECASE)
_DESC_RE = re.compile(r"^Description:\s*(.*)$", re.IGNORECASE)
_HASH_RE = re.compile(r"^Hashtags:\s*(.*)$", re.IGNORECASE)
_SCENE_RE = re.compile(r"^Scene\s+(\d+)\s*:?", re.IGNORECASE)
_OVERLAY_RE = re.compile(r"^Overlay\s*(?:\d+)?:\s*(.*)$", re.IGNORECASE)
_NARRATION_RE = re.compile(r"^Narration\s*(?:\d+)?:\s*(.*)$", re.IGNORECASE)


def parse_storyboard(text):
    """Parse storyboard text into a dict.

    Returns:
        {
            "title": str,
            "description": str,
            "hashtags": str,
            "hashtags_present": bool,
            "scenes": [{"num": int, "overlay": str, "narration": str}, ...],
        }
    Never raises: malformed input yields empty fields, and
    ``validate_storyboard`` reports what is missing.
    """
    title = ""
    description = ""
    hashtags = ""
    hashtags_present = False
    scenes = []
    current = None
    current_field = None

    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        match = _TITLE_RE.match(line)
        if match:
            title = match.group(1).strip()
            continue

        match = _DESC_RE.match(line)
        if match:
            description = match.group(1).strip()
            continue

        match = _HASH_RE.match(line)
        if match:
            hashtags = match.group(1).strip()
            hashtags_present = True
            continue

        match = _SCENE_RE.match(line)
        if match:
            current = {"num": int(match.group(1)), "overlay": "", "narration": ""}
            current_field = None
            # Text after the scene header (e.g. "Scene 1: HEADLINE") is the
            # overlay for that scene.
            after = line[match.end():].strip()
            if after:
                current["overlay"] = after
            scenes.append(current)
            continue

        match = _OVERLAY_RE.match(line)
        if match and current is not None:
            current["overlay"] = match.group(1).strip()
            current_field = "overlay"
            continue

        match = _NARRATION_RE.match(line)
        if match and current is not None:
            current["narration"] = match.group(1).strip()
            current_field = "narration"
            continue

        # Continuation of the previous field.
        if current is not None and current_field == "overlay":
            current["overlay"] = (current["overlay"] + " " + line).strip()
        elif current is not None and current_field == "narration":
            current["narration"] = (current["narration"] + " " + line).strip()

    return {
        "title": title,
        "description": description,
        "hashtags": hashtags,
        "hashtags_present": hashtags_present,
        "scenes": scenes,
    }


def validate_storyboard(parsed):
    """Return a list of informative error strings (empty list = valid)."""
    errors = []
    if not (parsed.get("title") or "").strip():
        errors.append("Missing 'Title:' line.")
    if not (parsed.get("description") or "").strip():
        errors.append("Missing 'Description:' line.")
    if not parsed.get("hashtags_present"):
        errors.append("Missing 'Hashtags:' line.")

    scenes = parsed.get("scenes") or []
    if not scenes:
        errors.append("No scenes found - expected at least one 'Scene 1' block.")

    for index, scene in enumerate(scenes):
        num = scene.get("num", index + 1)
        if not (scene.get("overlay") or "").strip():
            errors.append(f"Scene {num}: missing 'Overlay:' line.")
        elif len(scene["overlay"].strip()) > MAX_OVERLAY_CHARS:
            errors.append(
                f"Scene {num}: overlay text is {len(scene['overlay'].strip())} "
                f"characters (maximum {MAX_OVERLAY_CHARS})."
            )
        if not (scene.get("narration") or "").strip():
            errors.append(f"Scene {num}: missing 'Narration:' line.")

    numbers = [s.get("num") for s in scenes]
    if numbers != sorted(numbers):
        errors.append("Scene numbers are not in ascending order.")
    if len(set(numbers)) != len(numbers):
        errors.append("Duplicate scene numbers found.")

    return errors
