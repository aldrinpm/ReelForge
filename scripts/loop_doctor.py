"""Loop doctor: prerequisite/health checker for the ReelForge pipeline.

Checks LM Studio, FFmpeg, eSpeak, venv-tts, config, graphify-out, disk.
Exit code 0 = Loop Ready. Non-zero = list of failures.

Usage:
    python scripts\\loop_doctor.py
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\AI-Video-Production")
PYTHON = Path(r"E:\ai\AirLLM\py3.11.9\python.exe")
VENV_PY = ROOT / "venv-tts" / "Scripts" / "python.exe"


def check(label, ok, detail="", optional=False):
    """Print a check result. `optional` checks report but never fail the run."""
    if optional:
        mark = "OK  " if ok else "WARN"
    else:
        mark = "OK " if ok else "FAIL"
    print(f"  [{mark}] {label}" + (f"  -- {detail}" if detail else ""))
    return ok or optional


def main():
    print("=== Loop Doctor — ReelForge ===\n")
    results = []

    # Python base
    results.append(check("Python 3.11.9 base", PYTHON.exists(), str(PYTHON)))

    # FFmpeg
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        ver = (r.stdout or "").splitlines()[0] if r.returncode == 0 else ""
        results.append(check("FFmpeg on PATH", r.returncode == 0, ver[:60]))
    except Exception as e:
        results.append(check("FFmpeg on PATH", False, str(e)))

    # ffprobe
    try:
        r = subprocess.run(["ffprobe", "-version"], capture_output=True, text=True, timeout=10,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        results.append(check("ffprobe on PATH", r.returncode == 0))
    except Exception as e:
        results.append(check("ffprobe on PATH", False, str(e)))

    # eSpeak NG
    espeak = Path(r"C:\Program Files\eSpeak NG\espeak-ng.exe")
    results.append(check("eSpeak NG", espeak.exists(), str(espeak)))

    # venv-tts
    results.append(check("venv-tts python", VENV_PY.exists(), str(VENV_PY)))

    # Kokoro import
    if VENV_PY.exists():
        try:
            r = subprocess.run(
                [str(VENV_PY), "-c", "import kokoro, torch, soundfile; print('kokoro', kokoro.__version__)"],
                capture_output=True, text=True, timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            results.append(check("Kokoro importable", r.returncode == 0, (r.stdout or r.stderr).strip()[:60]))
        except Exception as e:
            results.append(check("Kokoro importable", False, str(e)))
    else:
        results.append(check("Kokoro importable", False, "venv missing"))

    # config.json
    cfg_path = ROOT / "config.json"
    cfg_ok = False
    if cfg_path.exists():
        try:
            import json
            json.loads(cfg_path.read_text(encoding="utf-8"))
            cfg_ok = True
        except Exception:
            cfg_ok = False
    results.append(check("config.json valid", cfg_ok, str(cfg_path)))

    # LLM (based on current Settings)
    try:
        import urllib.request, json as _j
        import sys as _sys

        _sys.path.insert(0, str(ROOT / "scripts"))
        import config as cfg_mod
        import llm_client as lc
        cfg = cfg_mod.load_config()
        llm = cfg_mod.resolve_llm_config(cfg, {})
        base_url = lc._normalize_base_url(llm.get("base_url", ""))
        model = (llm.get("model") or "").strip()
        provider = llm.get("provider", "custom")
        if not base_url:
            raise RuntimeError("base_url is empty")
        url = base_url.rstrip("/") + "/models"
        req = urllib.request.Request(url, headers=lc._headers(llm.get("api_key", "")), method="GET")
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = _j.loads(resp.read().decode("utf-8"))
        ids = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
        has_model = (not model) or (model in ids)
        ok = bool(ids) and has_model
        detail = f"{provider}: {', '.join(ids[:3]) or 'no models'}"
        if model:
            detail += f" (model={'yes' if has_model else 'NO'})"
        results.append(check(f"LLM endpoint ({provider})", ok, detail, optional=True))
    except Exception as e:
        results.append(check("LLM endpoint (config)", False,
                             f"not reachable ({e}) - only needed for the "
                             "standalone AI dialog, not for pipeline runs",
                             optional=True))

    # Graphify
    graph = ROOT / "graphify-out" / "graph.json"
    results.append(check("Graphify graph present", graph.exists(), str(graph)))

    # Disk space on E:
    try:
        usage = shutil.disk_usage(str(ROOT))
        free_gb = usage.free / (1024 ** 3)
        results.append(check("Disk free on E:", free_gb >= 5, f"{free_gb:.1f} GB free"))
    except Exception as e:
        results.append(check("Disk free on E:", False, str(e)))

    # ICM layers
    icm_ok = (ROOT / "_core" / "CONTEXT.md").exists() and (ROOT / "CLAUDE.md").exists()
    results.append(check("ICM layers present", icm_ok))

    # ICM doc/code drift (catches stale paths, retired features, broken
    # stage contracts). Stdlib only; must exit 0 for the project to be
    # considered in sync.
    try:
        r = subprocess.run(
            [str(PYTHON), str(ROOT / "scripts" / "verify_docs.py")],
            capture_output=True, text=True, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        lines = [ln for ln in (r.stdout or "").strip().splitlines() if ln.strip()]
        detail = lines[-1] if lines else ""
        results.append(check("ICM docs in sync with code", r.returncode == 0, detail))
    except Exception as e:
        results.append(check("ICM docs in sync with code", False, str(e)))

    print()
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"Result: {passed}/{total} checks passed.")
    if passed == total:
        print("Loop Ready.")
        sys.exit(0)
    else:
        print("Not ready — fix the FAIL items above.")
        sys.exit(1)


if __name__ == "__main__":
    main()