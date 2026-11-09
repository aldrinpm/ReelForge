"""Shared configuration loader for the video pipeline.

Reads E:\\AI-Video-Production\\config.json (optional) and deep-merges it over
built-in defaults. CLI overrides are applied on top by callers.

No third-party dependencies (stdlib only) to keep the bundle small.
"""
import json
import os
from pathlib import Path

ROOT = Path(r"E:\AI-Video-Production")
CONFIG_PATH = ROOT / "config.json"

DEFAULT_PROVIDERS = {
    "lmstudio":   {"base_url": "http://127.0.0.1:1234/v1",  "api_key": "", "api_key_env": ""},
    "ollama":     {"base_url": "http://127.0.0.1:11434/v1", "api_key": "ollama", "api_key_env": ""},
    "vllm":       {"base_url": "http://127.0.0.1:8000/v1",  "api_key": "EMPTY", "api_key_env": ""},
    "llamacpp":   {"base_url": "http://127.0.0.1:8080/v1",  "api_key": "", "api_key_env": ""},
    "openai":     {"base_url": "https://api.openai.com/v1",  "api_key": "", "api_key_env": "OPENAI_API_KEY"},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1", "api_key": "", "api_key_env": "OPENROUTER_API_KEY"},
    "groq":       {"base_url": "https://api.groq.com/openai/v1", "api_key": "", "api_key_env": "GROQ_API_KEY"},
    "together":   {"base_url": "https://api.together.xyz/v1", "api_key": "", "api_key_env": "TOGETHER_API_KEY"},
    "custom":     {"base_url": "", "api_key": "", "api_key_env": ""},
}

DEFAULT_CONFIG = {
    "llm": {
        "provider": "lmstudio",
        "base_url": "",
        "model": "empero-ai/qwythos-9b-v2-gguf/qwythos-9b-v2-mtp-q4_k_m.gguf",
        "api_key": "",
        "api_key_env": "",
        "temperature": 0.4,
        "max_tokens": 4500,
        "timeout": 300,
    },
    "tts": {
        "engine": "kokoro",
        "voice": "af_heart",
        "speed": 1.0,
    },
    "providers": DEFAULT_PROVIDERS,
}


def _deep_merge(base, override):
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config():
    """Load config.json (if present) merged over defaults. Never raises on missing file."""
    cfg = _deep_merge(DEFAULT_CONFIG, {})
    if CONFIG_PATH.exists():
        try:
            user = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            cfg = _deep_merge(cfg, user)
        except (json.JSONDecodeError, OSError):
            pass
    # Merge provider presets (user can add/override).
    if "providers" not in cfg or not isinstance(cfg["providers"], dict):
        cfg["providers"] = {}
    for name, preset in DEFAULT_PROVIDERS.items():
        cfg["providers"].setdefault(name, {})
        cfg["providers"][name] = _deep_merge(preset, cfg["providers"][name])
    return cfg


def resolve_api_key(llm_cfg):
    """Resolve API key: explicit value, then env var, then provider preset."""
    key = (llm_cfg.get("api_key") or "").strip()
    if key:
        return key
    env_name = (llm_cfg.get("api_key_env") or "").strip()
    if env_name:
        val = os.environ.get(env_name, "").strip()
        if val:
            return val
    provider = llm_cfg.get("provider", "")
    preset = (llm_cfg.get("_providers", {}) or {}).get(provider, {})
    # providers stored separately in config; check there
    return ""


def resolve_llm_config(cfg, overrides=None):
    """Return a fully-resolved LLM config dict (base_url/model/key/temp/tokens/timeout).

    overrides: dict of CLI overrides (provider, base_url, model, api_key, temperature,
    max_tokens, timeout). Empty/None values are ignored.
    """
    overrides = overrides or {}
    llm = dict(cfg.get("llm", {}))
    providers = cfg.get("providers", {})

    provider = overrides.get("provider") or llm.get("provider") or "custom"
    llm["provider"] = provider

    preset = providers.get(provider, {})

    # base_url: override > config > preset
    base_url = (overrides.get("base_url") or llm.get("base_url") or preset.get("base_url") or "").strip()
    llm["base_url"] = base_url

    # model: override > config
    model = (overrides.get("model") or llm.get("model") or "").strip()
    llm["model"] = model

    # api_key: override > config > env (from config) > preset env > preset value
    api_key = (overrides.get("api_key") or llm.get("api_key") or "").strip()
    if not api_key:
        env_name = (llm.get("api_key_env") or preset.get("api_key_env") or "").strip()
        if env_name:
            api_key = os.environ.get(env_name, "").strip()
    if not api_key:
        api_key = (preset.get("api_key") or "").strip()
    llm["api_key"] = api_key
    llm["_providers"] = providers

    for field in ("temperature", "max_tokens", "timeout"):
        val = overrides.get(field)
        if val is None:
            val = llm.get(field)
        if val is not None:
            llm[field] = val

    return llm


def resolve_tts_config(cfg, overrides=None):
    overrides = overrides or {}
    tts = dict(cfg.get("tts", {}))
    voice = (overrides.get("voice") or tts.get("voice") or "af_heart").strip()
    speed = overrides.get("speed")
    if speed is None:
        speed = tts.get("speed", 1.0)
    tts["voice"] = voice
    tts["speed"] = float(speed)
    return tts


def redact_key(key):
    if not key:
        return "(not set)"
    if len(key) <= 8:
        return "***"
    return key[:4] + "..." + key[-4:]