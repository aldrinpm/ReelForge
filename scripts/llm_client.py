"""OpenAI-compatible LLM client (stdlib only).

Works with LM Studio, Ollama, vLLM, llama.cpp, OpenAI, OpenRouter, Groq,
Together, and any other OpenAI-compatible endpoint. No third-party deps.
"""
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

def _normalize_base_url(url):
    url = (url or "").rstrip("/")
    if not url:
        return url
    # Ensure OpenAI-compatible path suffix.
    from urllib.parse import urlparse
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    # Ollama-style native "/api" base is not OpenAI-compatible; the OpenAI
    # endpoints are served from the site root under /v1.
    if path == "/api":
        url = (parsed.scheme + "://" + parsed.netloc).rstrip("/")
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
    if path == "" or path == "/":
        url = url + "/v1"
    return url


def _headers(api_key):
    h = {"Content-Type": "application/json"}
    if api_key:
        h["Authorization"] = f"Bearer {api_key}"
    return h


def list_models(base_url, api_key="", timeout=30):
    """Return list of model id strings from GET {base_url}/models."""
    base_url = _normalize_base_url(base_url)
    url = base_url.rstrip("/") + "/models"
    req = urllib.request.Request(url, headers=_headers(api_key), method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return [m.get("id", "") for m in data.get("data", []) if m.get("id")]


def chat(system, user, cfg):
    """Send a chat completion request. Returns the assistant message text.

    cfg: dict with base_url, model, api_key, temperature, max_tokens, timeout.
    Retries up to 3 times on connection errors.
    """
    base_url = _normalize_base_url((cfg.get("base_url") or "").rstrip("/"))
    if not base_url:
        raise ValueError("LLM base_url is empty. Set it in config.json or --llm-url.")
    model = cfg.get("model", "")
    if not model:
        raise ValueError("LLM model is empty. Set it in config.json or --llm-model.")

    url = base_url + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": cfg.get("temperature", 0.4),
        "max_tokens": cfg.get("max_tokens", 4500),
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_headers(cfg.get("api_key", "")), method="POST")
    timeout = cfg.get("timeout", 300)

    max_retries = 3
    last_exception = None
    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            break  # success
        except urllib.error.URLError as e:
            last_exception = e
            if attempt < max_retries:
                time.sleep(1.5 * attempt)  # exponential backoff: 1.5s, 3s
                continue
            raise ConnectionError(f"Cannot reach LLM at {base_url} after {max_retries} attempts: {e}") from e
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            # Retry on 5xx server errors
            if 500 <= e.code < 600 and attempt < max_retries:
                time.sleep(1.5 * attempt)
                continue
            raise RuntimeError(f"LLM HTTP {e.code}: {body[:500]}") from e
    else:
        # This shouldn't be reached, but just in case
        raise ConnectionError(f"Cannot reach LLM at {base_url} after {max_retries} attempts: {last_exception}")

    choices = result.get("choices", [])
    if not choices:
        raise ValueError("LLM returned no choices.")
    return choices[0].get("message", {}).get("content", "")