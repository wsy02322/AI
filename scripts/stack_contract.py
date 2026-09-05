"""Shared contract constants for Wave 0 apply + verify. Must match docs/SPEC.md."""

from __future__ import annotations

PIPE = "open_webui_openrouter_integration"

# New-chat default: single flagship; users opt into compare manually.
DEFAULT_MODEL_PRIMARY = f"{PIPE}.x-ai.grok-4.6"
DEFAULT_MODEL_SECONDARY = f"{PIPE}.anthropic.claude-opus-5"
DEFAULT_MODELS = DEFAULT_MODEL_PRIMARY
# Background tasks: same as default chat.
TASK_MODEL = DEFAULT_MODEL_PRIMARY

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

# Picker policy: kept families stay on the newest catalog id AND are public.
# New families do not join picker or public. Verify leftover * read on retired ids.
PUBLIC_MODEL_IDS = [
    f"{PIPE}.anthropic.claude-fable-5.1",
    f"{PIPE}.anthropic.claude-opus-5",
    f"{PIPE}.bytedance-seed.seedream-5-0-lite",
    f"{PIPE}.bytedance-seed.seedream-5-0-pro",
    f"{PIPE}.deepseek.deepseek-v4-pro-0813",
    f"{PIPE}.google.gemini-3-pro-image",
    f"{PIPE}.google.gemini-3.1-flash-image",
    f"{PIPE}.google.gemini-3.1-pro-preview",
    f"{PIPE}.google.gemini-3.8-flash",
    f"{PIPE}.microsoft.mai-image-2.5-pro",
    f"{PIPE}.moonshotai.kimi-k3",
    f"{PIPE}.openai.gpt-5.4-image-2",
    f"{PIPE}.openai.gpt-5.6-sol",
    f"{PIPE}.openai.gpt-5.6-sol-pro",
    f"{PIPE}.openai.gpt-image-2",
    f"{PIPE}.perplexity.sonar-deep-research",
    f"{PIPE}.perplexity.sonar-pro-search",
    f"{PIPE}.qwen.qwen-image-3-pro",
    f"{PIPE}.qwen.qwen3.8-max-0902",
    f"{PIPE}.x-ai.grok-4.6",
    f"{PIPE}.x-ai.grok-imagine-image-2.0",
]

# No admin-only extras: picker == public. Kept for strip/verify loops.
EXTRA_ACTIVE_MODEL_IDS: list[str] = []

# Previous latest ids of kept families. Stay inactive; strip leftover * read.
RETIRED_MODEL_IDS = [
    f"{PIPE}.anthropic.claude-fable-5",
    f"{PIPE}.google.gemini-3.7-flash",
    f"{PIPE}.qwen.qwen3.8-max",
]

# Runtime picker == public (21). Granite / Mercury / new families stay inactive.
ACTIVE_MODEL_IDS = PUBLIC_MODEL_IDS + EXTRA_ACTIVE_MODEL_IDS

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
    "COMPARE_CROSS_MODEL_REASONING_V1",
    "FABLE_UNSIGNED_SUMMARY_V1",
]

# Live UX (2026-09-01): one banner, no empty-chat chips, reply Follow-up off.
BANNER_IDS = ["usage-guide-v3"]
SUGGESTIONS_COUNT = 0
TASK_FOLLOW_UP_ENABLE = False

# P0-D Notebook / YouTube (N1)
NOTEBOOK_KNOWLEDGE_NAME = "YouTube Notebook"
RAG_EMBEDDING_ENGINE = "openai"
RAG_EMBEDDING_MODEL = "openai/text-embedding-3-small"
RAG_OPENAI_BASE_URL = "https://openrouter.ai/api/v1"
YOUTUBE_LOADER_LANGUAGES = ["en", "zh", "zh-Hans", "zh-Hant", "ja", "ko"]
NOTEBOOK_SMOKE_VIDEO = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
