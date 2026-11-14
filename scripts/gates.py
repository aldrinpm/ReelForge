"""Gate thresholds — the enforced contract for a publishable video.

Single source of truth: `gate.yaml` (machine-readable, at the repo root).
The ICM prose docs (`_config/qa_thresholds.md`, `_core/loop-audit.md`)
describe the same rules; this module is what actually ENFORCES them at
QA time so the declared thresholds cannot drift away from reality again.

PyYAML is used when available (it is present in the pipeline's Python at
E:\\ai\\AirLLM\\py3.11.9). If it is unavailable, the built-in defaults
below mirror gate.yaml so the pipeline never crashes on a missing
dependency — and the fallback is reported by `thresholds_source()`.
"""
from pathlib import Path

ROOT = Path(r"E:\AI-Video-Production")
GATE_FILE = ROOT / "gate.yaml"

# Mirrors gate.yaml "thresholds" — used when PyYAML is unavailable.
DEFAULT_THRESHOLDS = {
    "duration_min_s": 1,
    "duration_max_s": 90,        # Reels max (Shorts: 60)
    "scene_count_min": 1,
    "scene_count_max": 12,
    "max_volume_db": -0.3,       # no clipping (target -1.0)
}


def load_thresholds():
    """Return the enforced threshold dict (from gate.yaml, else defaults)."""
    thresholds = dict(DEFAULT_THRESHOLDS)
    try:
        import yaml
        data = yaml.safe_load(GATE_FILE.read_text(encoding="utf-8")) or {}
        declared = data.get("thresholds") or {}
        for key in thresholds:
            if key in declared:
                thresholds[key] = declared[key]
    except Exception:
        pass
    return thresholds


def thresholds_source():
    """Human-readable origin of the thresholds, for the QA log."""
    try:
        import yaml
        yaml.safe_load(GATE_FILE.read_text(encoding="utf-8"))
        return "gate.yaml"
    except Exception:
        return "built-in defaults (gate.yaml unreadable or PyYAML missing)"


def check_video(duration, scene_count, max_volume_db, thresholds=None):
    """Return a list of gate violations for a rendered video (empty = pass).

    Violations are returned, not raised, so the caller can decide whether
    a violation is fatal or an acknowledged override.
    """
    th = thresholds or load_thresholds()
    problems = []
    if scene_count < th["scene_count_min"]:
        problems.append(
            f"scene count {scene_count} below min {th['scene_count_min']}")
    if scene_count > th["scene_count_max"]:
        problems.append(
            f"scene count {scene_count} exceeds max {th['scene_count_max']}")
    if duration < th["duration_min_s"]:
        problems.append(
            f"duration {duration:.2f}s below min {th['duration_min_s']}s")
    if duration > th["duration_max_s"]:
        problems.append(
            f"duration {duration:.2f}s exceeds max {th['duration_max_s']}s")
    if max_volume_db > th["max_volume_db"]:
        problems.append(
            f"max_volume {max_volume_db} dB exceeds {th['max_volume_db']} dB")
    return problems


def check_content_gates(duration, scene_count, max_volume_db, thresholds=None):
    """Split violations into fatal (always) and overridable (long-form).

    Overridable = duration / scene-count limits, i.e. the platform-fit
    rules. A user may deliberately produce a long video; clipping and
    broken geometry never can.
    """
    th = thresholds or load_thresholds()
    fatal = []
    overridable = []
    for problem in check_video(duration, scene_count, max_volume_db, th):
        if "max_volume" in problem:
            fatal.append(problem)
        else:
            overridable.append(problem)
    return fatal, overridable
