"""Shared contract constants for Wave 0 apply + verify. Must match docs/SPEC.md."""

from __future__ import annotations

PIPE = "open_webui_openrouter_integration"

DEFAULT_MODEL = f"{PIPE}.openai.gpt-5.6-sol-pro"
# Background tasks (title, autocomplete, tags): cheap Pipe model — not the default chat model.
TASK_MODEL = f"{PIPE}.x-ai.grok-4.6"

PINNED_MODELS = [
    f"{PIPE}.perplexity.sonar-pro-search",
    f"{PIPE}.perplexity.sonar-deep-research",
    f"{PIPE}.anthropic.claude-opus-5",
    f"{PIPE}.openai.gpt-5.6-sol-pro",
]

SONAR_MODEL_IDS = [
    f"{PIPE}.perplexity.sonar-pro-search",
    f"{PIPE}.perplexity.sonar-deep-research",
]

IMAGE_MODEL_IDS = [
    f"{PIPE}.google.gemini-3-pro-image",
    f"{PIPE}.google.gemini-3.1-flash-image",
    f"{PIPE}.openai.gpt-image-2",
    f"{PIPE}.openai.gpt-5.4-image-2",
    f"{PIPE}.bytedance-seed.seedream-5-0-pro",
    f"{PIPE}.bytedance-seed.seedream-5-0-lite",
    f"{PIPE}.microsoft.mai-image-2.5-pro",
    f"{PIPE}.qwen.qwen-image-3-pro",
    f"{PIPE}.x-ai.grok-imagine-image-2.0",
]

PUBLIC_MODEL_IDS = [
    f"{PIPE}.anthropic.claude-fable-5",
    f"{PIPE}.anthropic.claude-opus-5",
    f"{PIPE}.bytedance-seed.seedream-5-0-lite",
    f"{PIPE}.bytedance-seed.seedream-5-0-pro",
    f"{PIPE}.deepseek.deepseek-v4-pro-0813",
    f"{PIPE}.google.gemini-3-pro-image",
    f"{PIPE}.google.gemini-3.1-flash-image",
    f"{PIPE}.microsoft.mai-image-2.5-pro",
    f"{PIPE}.moonshotai.kimi-k3",
    f"{PIPE}.openai.gpt-5.4-image-2",
    f"{PIPE}.openai.gpt-5.6-sol",
    f"{PIPE}.openai.gpt-5.6-sol-pro",
    f"{PIPE}.openai.gpt-image-2",
    f"{PIPE}.perplexity.sonar-deep-research",
    f"{PIPE}.perplexity.sonar-pro-search",
    f"{PIPE}.qwen.qwen-image-3-pro",
    f"{PIPE}.qwen.qwen3.8-max",
    f"{PIPE}.x-ai.grok-4.6",
    f"{PIPE}.x-ai.grok-imagine-image-2.0",
]

CHAT_KEEP_CODE_INTERPRETER = [
    f"{PIPE}.openai.gpt-5.6-sol-pro",
    f"{PIPE}.anthropic.claude-opus-5",
]

GUARDS = [
    "openrouter_image_tool_guard",
    "openrouter_image_context_guard",
    "openrouter_search_native_tool_guard",
]

DISABLED_FILTERS = ["openrouter_web_tools", "openrouter_image_gen"]
DETACH_FILTERS = set(DISABLED_FILTERS)

PIPE_VALVES_FALSE = [
    "AUTO_ATTACH_WEB_TOOLS_FILTER",
    "AUTO_ATTACH_IMAGE_GEN_FILTER",
    "AUTO_INSTALL_WEB_TOOLS_FILTER",
    "AUTO_INSTALL_IMAGE_GEN_FILTER",
    "AUTO_DEFAULT_WEB_TOOLS_FILTER",
    "ENABLE_DATETIME",
    "ENABLE_WEB_SEARCH",
    "UPDATE_MODEL_CAPABILITIES",
]

PIPE_PATCH_MARKERS = [
    "_is_openrouter_images_api_model",
    "seedream-5",
    "middle-out",
    "apply_chat_context_transforms",
]

BANNER_IDS = ["usage-pick-model-v2", "usage-reasoning-depth-v2"]
SUGGESTIONS_COUNT = 4
