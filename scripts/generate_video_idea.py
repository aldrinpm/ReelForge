"""Generate a duration-aware educational video storyboard via a local or cloud LLM.

Reads config.json for the LLM provider/model/endpoint (overridable via CLI).
Uses an OpenAI-compatible chat endpoint (LM Studio, Ollama, vLLM, OpenAI, ...).

Duration can be supplied with --duration (seconds) or detected from the topic,
for example: "a 5-minute video about ...". If neither is present, the default
runtime is 60 seconds. --scenes remains an optional exact scene-count override.
"""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows to handle Unicode from LLM responses.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg_mod
import llm_client

ROOT = Path(r"E:\AI-Video-Production")
OUTPUT_DIR = ROOT / "output"

DEFAULT_DURATION_SECONDS = 60
WORDS_PER_MINUTE_MIN = 120
WORDS_PER_MINUTE_MAX = 140
WORDS_PER_MINUTE_TARGET = 130
SCENE_SECONDS_MIN = 15
SCENE_SECONDS_MAX = 30
MAX_EXPANSION_ATTEMPTS = 2

SYSTEM_PROMPT = r"""
You are an educational video producer, scriptwriter, and factual researcher.

Create a complete, production-ready educational video project for Facebook
Reels and YouTube Shorts, or longer educational videos when requested.

DURATION AND NARRATION REQUIREMENTS:
- The exact requested runtime will be supplied in the user instruction.
- Treat that runtime as a hard requirement, not a vague suggestion.
- Write approximately 120-140 spoken narration words per minute (target 130).
- The complete narration must be long enough to fill the requested runtime.
- Do not shorten the script merely to keep the scene count low.
- Divide the narration into a dynamic number of scenes, normally about
  15-30 seconds of narration per scene. There is NO fixed scene-count cap.
- Choose scene count based on runtime, topic structure, and meaningful visual
  changes. A longer video must receive proportionally more scenes.
- Each scene must have its own narration segment and image prompt.
- The complete top-level narration must contain the same spoken content as
  the scene narration segments, in the same order. Do not omit paragraphs.
- Scene durations must add up to the requested target duration.
- If an exact scene count is explicitly requested, use exactly that count and
  distribute the requested runtime across those scenes.

CONTENT REQUIREMENTS:
- Use a vertical 9:16 format unless the user specifies otherwise.
- Address a general audience; explain technical concepts simply.
- Make narration engaging, natural, coherent, and factually responsible.
- Develop each major point with explanation, context, and relevant examples.
- Avoid repetition and filler added solely to increase word count.
- Distinguish established facts from allegations, predictions, hypotheses,
  opinions, and uncertainties.
- For current affairs, avoid presenting developing or disputed claims as facts.
- Do not invent scientific facts, statistics, quotations, legal provisions,
  events, or sources.
- Image prompts must describe visually clear images suitable for
  Stable Diffusion 1.5. Avoid relying on legible text inside generated images.
- Motion directions must be achievable with FFmpeg pan, zoom, or simple
  transitions. Do not require real video footage or complex animation.
- Do not invent source URLs. Give reputable source names and search queries
  when exact URLs cannot be verified.

Return ONLY valid JSON. Do not use Markdown fences or explanatory text.
Use this exact structure and preserve these field names:
{
  "title": "Video title",
  "topic": "Main topic",
  "target_duration_seconds": 300,
  "audience": "General audience",
  "narration": "Complete narration, at the required length",
  "scenes": [
    {
      "scene_number": 1,
      "duration_seconds": 20,
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
    """Extract a JSON object from a response, tolerating Markdown fences."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("The model did not return a JSON object.")
    candidate = text[start:end + 1]
    candidate = re.sub(r",(\s*[}\]])", r"\1", candidate)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError(f"The model returned invalid JSON: {exc}") from exc


def detect_duration_seconds(text):
    """Detect an explicitly stated runtime in a topic/prompt."""
    patterns = [
        (r"\b(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|hr)\b", 3600),
        (r"\b(\d+(?:\.\d+)?)\s*(?:minutes?|mins?|min)\b", 60),
        (r"\b(\d+(?:\.\d+)?)\s*(?:seconds?|secs?|sec)\b", 1),
    ]
    for pattern, multiplier in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            seconds = int(round(float(match.group(1)) * multiplier))
            if seconds < 1:
                raise ValueError("Requested video duration must be at least 1 second.")
            return seconds
    return None


def count_words(text):
    """Count spoken words, including contractions and hyphenated terms."""
    return len(re.findall(r"\b[\w]+(?:['’\-][\w]+)*\b", str(text or ""), flags=re.UNICODE))


def expected_word_range(duration_seconds):
    minutes = duration_seconds / 60.0
    return (
        int(round(minutes * WORDS_PER_MINUTE_MIN)),
        int(round(minutes * WORDS_PER_MINUTE_MAX)),
    )


def suggested_scene_count(duration_seconds):
    """Suggest a dynamic count at roughly 22 seconds per scene."""
    return max(1, int(round(duration_seconds / 22.0)))


def validate_project(project, target_duration, exact_scenes=None):
    if not isinstance(project, dict):
        raise ValueError("The model response must be a JSON object.")

    scenes = project.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("The project must contain at least one scene.")
    if exact_scenes is not None and len(scenes) != exact_scenes:
        raise ValueError(f"Expected exactly {exact_scenes} scenes, received {len(scenes)}.")

    total_duration = 0
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            raise ValueError(f"Scene {index} is not a JSON object.")
        try:
            duration = int(scene["duration_seconds"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Scene {index} has an invalid duration_seconds value.") from exc
        if duration < 1:
            raise ValueError(f"Scene {index} duration must be at least 1 second.")
        if not str(scene.get("narration_segment", "")).strip():
            raise ValueError(f"Scene {index} is missing narration_segment.")
        total_duration += duration

    # Permit only a small rounding difference; do not silently rewrite timings.
    duration_tolerance = max(2, int(round(target_duration * 0.01)))
    if abs(total_duration - target_duration) > duration_tolerance:
        raise ValueError(
            f"Scene durations total {total_duration}s, but requested runtime is "
            f"{target_duration}s (allowed difference: {duration_tolerance}s)."
        )

    narration = str(project.get("narration", "")).strip()
    words = count_words(narration)
    min_words, max_words = expected_word_range(target_duration)
    minimum_acceptable = int(min_words * 0.90)
    if words < minimum_acceptable:
        raise ValueError(
            f"Narration is too short: {words} words; expected approximately "
            f"{min_words}-{max_words} words (minimum acceptance: {minimum_acceptable})."
        )

    return total_duration, words, (min_words, max_words)


def build_user_prompt(topic, target_duration, exact_scenes=None):
    min_words, max_words = expected_word_range(target_duration)
    minutes = target_duration / 60.0
    scene_guidance = (
        f"Create exactly {exact_scenes} scenes, distributing the runtime across them."
        if exact_scenes is not None
        else (
            f"Choose the scene count dynamically; approximately "
            f"{suggested_scene_count(target_duration)} scenes is a useful starting point, "
            f"but adjust it to the topic and do not impose a fixed cap."
        )
    )
    return (
        f"Create a complete educational video project about: {topic}\n\n"
        f"REQUIRED RUNTIME: exactly {target_duration} seconds ({minutes:.2f} minutes).\n"
        f"NARRATION TARGET: approximately {min_words}-{max_words} spoken words, "
        f"aiming for {WORDS_PER_MINUTE_TARGET} words per minute.\n"
        f"SCENE COUNT: {scene_guidance}\n"
        "The narration must genuinely fill the requested runtime. Do not return "
        "a short-form script for a longer requested video. Ensure scene durations "
        "sum to the required runtime and the top-level narration matches the scene "
        "narration segments in order."
    )


def expand_underlength_project(project, topic, target_duration, llm_cfg, exact_scenes=None):
    """Ask the model to repair an underlength or structurally invalid storyboard."""
    min_words, max_words = expected_word_range(target_duration)
    last_error = None
    for attempt in range(1, MAX_EXPANSION_ATTEMPTS + 1):
        try:
            validate_project(project, target_duration, exact_scenes)
            return project
        except ValueError as error:
            last_error = error

        correction_prompt = (
            f"The previous storyboard for '{topic}' failed validation: {last_error}\n\n"
            f"Revise the supplied JSON project. The required runtime is {target_duration} "
            f"seconds and the narration target is {min_words}-{max_words} words. "
            "Expand the actual educational explanation with useful context, examples, "
            "causes, consequences, and transitions; do not add filler or repeat points. "
            "Maintain the existing JSON schema and all required fields. The complete "
            "top-level narration must match the scene narration segments in order. "
            "Scene durations must sum to the requested runtime. "
            + (f"Use exactly {exact_scenes} scenes. " if exact_scenes is not None else
               "Choose a suitable dynamic scene count with no fixed upper cap. ")
            + "Return ONLY the complete corrected JSON object.\n\n"
            "PREVIOUS PROJECT JSON:\n"
            + json.dumps(project, ensure_ascii=False)
        )
        print(f"Validation/length check failed; requesting correction ({attempt}/{MAX_EXPANSION_ATTEMPTS})...")
        response = llm_client.chat(
            "You are revising an existing storyboard. Follow the correction request exactly. "
            "Return only valid JSON and preserve the established schema.",
            correction_prompt,
            llm_cfg,
        )
        project = extract_json(response)

    # Final validation provides a precise error instead of silently saving a short script.
    validate_project(project, target_duration, exact_scenes)
    return project


def main():
    parser = argparse.ArgumentParser(
        description="Generate a duration-aware educational storyboard via a local or cloud LLM."
    )
    parser.add_argument(
        "topic", nargs="?", default=None,
        help="Educational video topic; runtime can be included, e.g. 'a 5-minute video about ...'",
    )
    parser.add_argument(
        "--scenes", type=int, default=None,
        help="Exact number of scenes (default: choose dynamically from video duration)",
    )
    parser.add_argument(
        "--duration", type=int, default=None, metavar="SECONDS",
        help="Target video duration in seconds; overrides duration detected in the topic",
    )
    parser.add_argument("--out", default=None, help="Explicit output JSON path")
    parser.add_argument("--llm", default=None, help="LLM provider name (lmstudio, ollama, openai, ...)")
    parser.add_argument("--llm-url", default=None, help="LLM base URL (overrides provider)")
    parser.add_argument("--llm-model", default=None, help="LLM model id")
    parser.add_argument("--llm-key", default=None, help="LLM API key (prefer env var)")
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--max-tokens", type=int, default=None, dest="max_tokens")
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--list-models", action="store_true", help="List models and exit")
    parser.add_argument("--system-prompt-file", default=None, help="Override the system prompt with a file")
    args = parser.parse_args()

    if args.scenes is not None and args.scenes < 1:
        parser.error("--scenes must be at least 1")
    if args.duration is not None and args.duration < 1:
        parser.error("--duration must be at least 1 second")

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
        except Exception as error:
            print(f"ERROR listing models: {error}")
            sys.exit(1)
        print("Available models:")
        for model in models:
            print(f"  {model}")
        return

    topic = (args.topic or "").strip()
    if not topic:
        topic = input("Enter your educational video topic: ").strip()
    if not topic:
        print("ERROR: A topic is required.")
        sys.exit(2)

    detected_duration = detect_duration_seconds(topic)
    target_duration = args.duration or detected_duration or DEFAULT_DURATION_SECONDS
    if target_duration < 1:
        parser.error("Target duration must be at least 1 second")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    system_prompt = SYSTEM_PROMPT
    if args.system_prompt_file:
        prompt_path = Path(args.system_prompt_file)
        if not prompt_path.exists():
            print(f"ERROR: System prompt file not found: {prompt_path}")
            sys.exit(2)
        system_prompt = prompt_path.read_text(encoding="utf-8")

    min_words, max_words = expected_word_range(target_duration)
    print(f"\nGenerating video project for: {topic}")
    print(f"Using model: {llm_cfg.get('model', '')}")
    print(f"Target duration: {target_duration} seconds ({target_duration / 60:.2f} minutes)")
    print(f"Narration target: {min_words}-{max_words} words")
    print(f"Scene count: {'exactly ' + str(args.scenes) if args.scenes else 'dynamic (no fixed cap)'}")
    print("Waiting for the model...\n")

    try:
        user_prompt = build_user_prompt(topic, target_duration, args.scenes)
        content = llm_client.chat(system_prompt, user_prompt, llm_cfg)
        project = extract_json(content)
        project = expand_underlength_project(
            project, topic, target_duration, llm_cfg, args.scenes
        )
    except (ConnectionError, RuntimeError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"GENERATION OR VALIDATION ERROR: {error}")
        print("Check the LLM endpoint/model, output-token limit, and whether the model returns the required JSON.")
        sys.exit(1)
    except Exception as error:
        print(f"UNEXPECTED ERROR: {error}")
        sys.exit(1)

    scenes = project["scenes"]
    total_duration, narration_words, word_range = validate_project(
        project, target_duration, args.scenes
    )

    project["topic"] = topic
    project["target_duration_seconds"] = target_duration
    project["generated_at"] = datetime.now().astimezone().isoformat()
    project["total_scene_duration_seconds"] = total_duration
    project["narration_word_count"] = narration_words
    project["production_status"] = "script_generated"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = re.sub(r"[^a-zA-Z0-9_-]+", "_", topic).strip("_")
    output_file = Path(args.out) if args.out else OUTPUT_DIR / f"{timestamp}_{safe_topic[:45]}.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(project, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("=" * 55)
    print("VIDEO PROJECT GENERATED SUCCESSFULLY")
    print("=" * 55)
    print(f"Title: {project.get('title', 'Untitled')}")
    print(f"Scenes: {len(scenes)}")
    print(f"Duration: {total_duration} seconds")
    print(f"Narration: {narration_words} words (target range: {word_range[0]}-{word_range[1]})")
    print(f"Output: {output_file}")
    print("\nNarration:")
    print(project.get("narration", ""))


if __name__ == "__main__":
    main()
