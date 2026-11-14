"""ICM doc/code drift audit.

The ICM layers are the project's contract: `_core/CONTEXT.md`, the
per-stage `pipeline/NN-*/CONTEXT.md`, `_config/*.md`, and `CLAUDE.md`.
They used to drift silently from the code (docs promised a publishing
kit, an `inbox/` workflow and scripts that no longer existed). This audit
makes that drift *mechanically detectable* instead of relying on memory.

Checks (stdlib only, no third-party packages):
  1. Every file path referenced in the ICM docs exists on disk.
  2. Retired features/scripts never reappear in the docs.
  3. Every stage CONTEXT.md keeps the required section structure.
  4. gate.yaml components match the known pipeline components.

Exit code 0 = no drift. Non-zero = drift found (each line says what to fix).

Run it after any change to the code or the docs:
    python scripts/verify_docs.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(r"E:\AI-Video-Production")

# The ICM layers proper. The transitional/historical documents
# (PROJECT_CONTEXT.md, OPENCODE_TASK.md) are NOT audited: they are
# snapshots of the past and are expected to describe retired features.
ICM_DOCS = [
    ROOT / "CLAUDE.md",
    ROOT / "_core" / "CONTEXT.md",
    ROOT / "_core" / "CONVENTIONS.md",
    ROOT / "_core" / "anti-patterns.md",
    ROOT / "_core" / "loop-audit.md",
]
ICM_DOCS += sorted((ROOT / "_config").glob("*.md"))
ICM_DOCS += sorted((ROOT / "pipeline").glob("*/CONTEXT.md"))

# Current (non-historical) docs that must also stay in sync.
CURRENT_DOCS = [
    ROOT / "README.md",
    ROOT / "SETUP.md",
    ROOT / "gate.yaml",
]

# Identifiers of features/scripts that were removed. If any of these
# reappear in a current doc, the doc is describing something that does
# not exist. These are unambiguous machine-artifact strings, so ordinary
# prose that merely says a feature does NOT exist (e.g. "no publishing
# kit") does not trip the check.
RETIRED_IDENTIFIERS = [
    "publishing.json",
    "publishing_kit",
    "generate_scene_images",
    "subtitle_style.md",
    "make_video.bat",
]

# Files that must not exist anymore.
RETIRED_PATHS = [
    "make_video.bat",
    "scripts/generate_scene_images.py",
    "_config/subtitle_style.md",
]

# Required sections in every stage contract.
REQUIRED_STAGE_SECTIONS = ["## Inputs", "## Process", "## Outputs",
                           "## Checkpoint", "## Audit"]

# gate.yaml component names that the pipeline actually has.
KNOWN_COMPONENTS = {
    "scene_authoring", "image_staging", "narration", "subtitles",
    "assembly", "qa_gates", "obsidian_run_note", "desktop_ui",
}

PATH_EXTENSIONS = (
    ".md", ".py", ".json", ".yaml", ".yml", ".bat", ".srt", ".wav",
    ".png", ".jpg", ".jpeg", ".gif", ".mp4", ".txt", ".toml", ".cfg",
)

# Template markers used in this repo (scene_XX, YYYYMMDD_HHMMSS, <stamp>...).
PLACEHOLDER_RE = re.compile(r"XX|YYYY|<[^>]*>|\*|\{[^}]*\}|\?")


def is_placeholder(token):
    """True for glob/template tokens that cannot be resolved literally."""
    return bool(PLACEHOLDER_RE.search(token))


def iter_doc_tokens(text):
    """Yield every backticked token in a markdown document."""
    for match in re.finditer(r"`([^`\n]+)`", text):
        yield match.group(1).strip()


def rel(path):
    """Path relative to ROOT when possible, else the absolute path."""
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return path


def path_like(token):
    """True if the token looks like a repo path to a real file/dir."""
    if is_placeholder(token):
        return False
    if token.startswith("/"):
        return False               # API route (e.g. /ai/generate), not a file
    if " " in token:
        return False               # a shell command, not a path
    if token.startswith(("http://", "https://", "--")):
        return False
    if token.endswith(("/", "\\")):
        return True                # directory reference
    if "/" not in token and "\\" not in token:
        return False               # bare filename: not a repo path
    return token.lower().endswith(PATH_EXTENSIONS)


def check_paths(docs, problems):
    """1. Every referenced path must exist."""
    for doc in docs:
        if not doc.exists():
            continue
        text = doc.read_text(encoding="utf-8-sig")
        for token in iter_doc_tokens(text):
            if not path_like(token):
                continue
            rel_path = token.replace("\\", "/").strip("/")
            # Strip trailing punctuation that markdown may have picked up.
            rel_path = rel_path.rstrip(".,;:")
            if not rel_path or is_placeholder(rel_path):
                continue
            target = ROOT / rel_path
            if target.exists():
                continue
            # A bare directory reference such as "images/archive/" is fine
            # only if it exists; anything else is drift.
            problems.append(
                f"{rel(doc)}: referenced path does not exist "
                f"-> '{token}'"
            )


def check_retired(docs, problems):
    """2. Retired features must not reappear."""
    for doc in docs:
        if not doc.exists():
            continue
        text = doc.read_text(encoding="utf-8-sig").lower()
        for identifier in RETIRED_IDENTIFIERS:
            if identifier.lower() in text:
                problems.append(
                    f"{rel(doc)}: mentions retired identifier "
                    f"'{identifier}' — remove or describe it as removed"
                )
    for retired_rel in RETIRED_PATHS:
        if (ROOT / retired_rel).exists():
            problems.append(
                f"retired path still exists on disk -> '{retired_rel}' "
                f"(remove it and update the docs)"
            )


def check_stage_sections(problems):
    """3. Stage contracts keep their required structure."""
    for ctx in sorted((ROOT / "pipeline").glob("*/CONTEXT.md")):
        text = ctx.read_text(encoding="utf-8-sig")
        for section in REQUIRED_STAGE_SECTIONS:
            if section not in text:
                problems.append(
                    f"{rel(ctx)}: missing required section "
                    f"'{section}'"
                )


def check_gate_components(problems):
    """4. gate.yaml components must be known."""
    gate = ROOT / "gate.yaml"
    if not gate.exists():
        problems.append("gate.yaml is missing")
        return
    text = gate.read_text(encoding="utf-8-sig")
    in_components = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("components:"):
            in_components = True
            continue
        if in_components:
            if not stripped or stripped.startswith("#"):
                continue
            if not line.startswith(" "):
                break
            name = stripped.split(":")[0].strip()
            if name and name not in KNOWN_COMPONENTS:
                problems.append(
                    f"gate.yaml: unknown component '{name}' "
                    f"(known: {', '.join(sorted(KNOWN_COMPONENTS))})"
                )


def main():
    problems = []
    # Path existence is enforced for the ICM layers (they are contracts).
    # Current prose docs may legitimately cite example outputs, so only the
    # retired-feature check applies to them.
    check_paths(ICM_DOCS, problems)
    check_retired(ICM_DOCS + CURRENT_DOCS, problems)
    check_stage_sections(problems)
    check_gate_components(problems)

    print("=== ICM doc/code drift audit ===")
    print(f"ICM docs audited : {len(ICM_DOCS)}")
    print(f"Current docs      : {len(CURRENT_DOCS)} (retired-feature check only)")
    if problems:
        print()
        for problem in problems:
            print(f"  FAIL  {problem}")
        print(f"\n{len(problems)} drift problem(s) found.")
        return 1
    print("\nNo drift: docs match the code.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
