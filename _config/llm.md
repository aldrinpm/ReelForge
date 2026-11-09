# LLM configuration (canonical source)

Default provider: lmstudio (local). Default model: Qwythos 9B V2 MTP GGUF.
Endpoint: http://127.0.0.1:1234/v1 (OpenAI-compatible).
Temperature: 0.4. Max tokens: 4500. Timeout: 300s.

Supported providers (OpenAI-compatible): lmstudio, ollama, vllm, llama.cpp,
openai, openrouter, groq, together, custom.

Cloud providers are OPT-IN only (cost + data-leaves-machine warning). Local is default.

Override: --llm, --llm-url, --llm-model, --llm-key flags, or config.json llm.*.
Model discovery: generate_video_idea.py --list-models.
System prompt override (advanced): --system-prompt-file.