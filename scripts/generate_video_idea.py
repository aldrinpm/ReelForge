"""Generate a 6-or-N-scene educational storyboard via a local or cloud LLM.

Reads config.json for the LLM provider/model/endpoint (overridable via CLI).
Uses an OpenAI-compatible chat endpoint (LM Studio, Ollama, vLLM, OpenAI, ...).
"""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows to handle Unicode from LLM responses
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg_mod
import llm_client

ROOT = Path(r"E:\AI-Video-Production")
OUTPUT_DIR = ROOT / "output"

SYSTEM_PROMPT = """
You are an educational short-form video producer and factual researcher.

Create a production-ready educational video project for Facebook Reels
and YouTube Shorts.

Requirements:
- Target duration: 1-180 seconds; preferred 15-120 seconds.
- Vertical 9:16 video format.
- General audience; explain technical concepts simply.
- Narration must be engaging, natural and factually responsible.
- Create 1 to 8 scenes (match supplied imagery/topic granularity; more images provided may imply more scenes).
- Each scene must have its own narration segment and image prompt.
- Scene durations must add up to the requested target duration.
- Image prompts must describe visually clear images suitable for
  Stable Diffusion 1.5.
- Motion directions must be achievable with FFmpeg pan, zoom or
  simple transitions.
- Avoid requiring real video footage or complex animation.
- Do not invent scientific facts, statistics, quotations or sources.
- Distinguish established facts from hypotheses or uncertainties.
- Do not invent source URLs. Give reputable source names and
  search queries when exact URLs cannot be verified.

Return ONLY valid JSON. Do not use Markdown fences.

Use this exact structure:
{
  "title": "Video title",
  "topic": "Main topic",
  "target_duration_seconds": 54,
  "audience": "General audience",
  "narration": "Complete narration",
  "scenes": [
    {
      "scene_number": 1,
      "duration_seconds": 9,
      "narration_segment": "Narration for this scene",
      "on_screen_text": "Short text overlay",
      "image_prompt": "Detailed Stable Diffusion image prompt",
      "motion_direction": "Simple camera movement or transition"
    }
  ],
  "fact_check_notes": [
    "Claims that require verification"
  ],
  "source_suggestions": [
    {
      "source_name": "Reputable institution or publication",
      "search_query": "Specific search query to verify the claim"
    }
  ]
}
"""


def extract_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("The model did not return a JSON object.")

    candidate = text[start:end + 1]
    candidate = re.sub(r",(\s*[}\]])", r"\1", candidate)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return json.loads(text[start:end + 1])


def main():
    parser = argparse.ArgumentParser(
        description="Generate an educational storyboard via a local or cloud LLM."
    )
    parser.add_argument(
        "topic", nargs="?", default=None,
        help="Educational video topic (interactive prompt if omitted)",
    )
    parser.add_argument(
        "--scenes", type=int, default=None,
        help="Exact number of scenes to generate (default: let the model choose 1-8)",
    )
    parser.add_argument(
        "--out", default=None,
        help="Explicit output JSON path (default: timestamped file in output/)",
    )
    parser.add_argument(
        "--llm", default=None, help="LLM provider name (lmstudio, ollama, openai, ...)",
    )
    parser.add_argument("--llm-url", default=None, help="LLM base URL (overrides provider)")
    parser.add_argument("--llm-model", default=None, help="LLM model id")
    parser.add_argument("--llm-key", default=None, help="LLM API key (prefer env var)")
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--max-tokens", type=int, default=None, dest="max_tokens")
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument(
        "--list-models", action="store_true",
        help="List models from the configured LLM endpoint and exit",
    )
    parser.add_argument(
        "--system-prompt-file", default=None,
        help="Override the system prompt with a file (advanced)",
    )
    args = parser.parse_args()

    cfg = cfg_mod.load_config()
    llm_cfg = cfg_mod.resolve_llm_config(cfg, {
        "provider": args.llm,
        "base_url": args.llm_url,
        "model": args.llm_model,
        "api_key": args.llm_key,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "timeout": args.timeout,
    })

    if args.list_models:
        try:
            models = llm_client.list_models(
                llm_cfg["base_url"], llm_cfg["api_key"], llm_cfg.get("timeout", 30),
            )
        except Exception as e:
            print(f"ERROR listing models: {e}")
            sys.exit(1)
        print("Available models:")
        for m in models:
            print(f"  {m}")
        sys.exit(0)

    topic = (args.topic or "").strip()
    if not topic:
        topic = input("Enter your educational video topic: ").strip()

    if not topic:
        print("ERROR: A topic is required.")
        sys.exit(2)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    system_prompt = SYSTEM_PROMPT
    if args.system_prompt_file:
        sp = Path(args.system_prompt_file)
        if sp.exists():
            system_prompt = sp.read_text(encoding="utf-8")
    if args.scenes:
        system_prompt = system_prompt.replace(
            "- Create 1 to 8 scenes (match supplied imagery/topic granularity; more images provided may imply more scenes).",
            f"- Create exactly {args.scenes} scenes.",
        )
        system_prompt = system_prompt.replace(
            "- Target duration: 1-180 seconds; preferred 15-120 seconds.",
            f"- Target duration: {args.scenes * 8}-{args.scenes * 12} seconds "
            f"(about {args.scenes * 9}s total).",
        )

    print(f"\nGenerating video project for: {topic}")
    print(f"Using local model: {llm_cfg.get('model', '')}")
    print("Waiting for the local model...\n")

    try:
        content = llm_client.chat(system_prompt, f"Create a complete educational video project about: {topic}", llm_cfg)
        project = extract_json(content)
    except (ConnectionError, RuntimeError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"GENERATION OR VALIDATION ERROR: {error}")
        print("Check LLM endpoint/model and that the model returns JSON.")
        sys.exit(1)
    except Exception as error:
        print(f"UNEXPECTED ERROR: {error}")
        sys.exit(1)

    scenes = project.get("scenes", [])

    if args.scenes:
        if len(scenes) != args.scenes:
            raise SystemExit(f"Expected {args.scenes} scenes, received {len(scenes)}.")
    elif len(scenes) < 1:
        raise SystemExit(f"Expected at least 1 scene, received {len(scenes)}.")

    total_duration = sum(int(scene["duration_seconds"]) for scene in scenes)

    if args.scenes:
        if not (args.scenes * 3 <= total_duration <= args.scenes * 15):
            raise SystemExit(
                f"Scene duration is {total_duration}s; expected between "
                f"{args.scenes * 3} and {args.scenes * 15}s."
            )
    elif not 0 <= total_duration <= 180:
        raise SystemExit(
            f"Scene duration is {total_duration}s; expected between 1 and 180s."
        )

    project["topic"] = topic
    project["generated_at"] = datetime.now().astimezone().isoformat()
    project["total_scene_duration_seconds"] = total_duration
    project["production_status"] = "script_generated"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = re.sub(r"[^a-zA-Z0-9_-]+", "_", topic).strip("_")

    if args.out:
        output_file = Path(args.out)
    else:
        output_file = OUTPUT_DIR / f"{timestamp}_{safe_topic[:45]}.json"

    output_file.parent.mkdir(parents=True, exist_ok=True)

    output_file.write_text(
        json.dumps(project, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("=" * 55)
    print("VIDEO PROJECT GENERATED SUCCESSFULLY")
    print("=" * 55)
    print(f"Title: {project.get('title', 'Untitled')}")
    print(f"Scenes: {len(scenes)}")
    print(f"Duration: {total_duration} seconds")
    print(f"Output: {output_file}")
    print("\nNarration:")
    print(project.get("narration", ""))


if __name__ == "__main__":
    main()