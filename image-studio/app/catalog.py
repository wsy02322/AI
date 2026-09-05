"""IS0 capability table. UI only shows controls a model actually supports."""

from __future__ import annotations

from typing import Any

MASK_MODEL_ID = "openai:gpt-image-2"

# Direct APIs first. OpenRouter is fallback / long-tail only.
MODELS: list[dict[str, Any]] = [
    {
        "id": "openai:gpt-image-2",
        "label": "GPT Image 2",
        "provider": "openai",
        "upstream": "gpt-image-2",
        "edit": "mask",
        "refs_max": 16,
        "n_max": 1,
        "stream": True,
        "aspects": ["1:1", "3:2", "2:3", "4:3", "3:4", "16:9", "9:16"],
        "qualities": ["auto", "low", "medium", "high"],
        "resolutions": [],
        "backgrounds": ["auto", "opaque"],
        "default_aspect": "1:1",
    },
    {
        "id": "google:gemini-3-pro-image",
        "label": "Nano Banana Pro",
        "provider": "google",
        "upstream": "gemini-3-pro-image-preview",
        "edit": "semantic",
        "refs_max": 14,
        "n_max": 1,
        "stream": False,
        "aspects": ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"],
        "qualities": [],
        "resolutions": ["1K", "2K", "4K"],
        "backgrounds": [],
        "default_aspect": "1:1",
        "default_resolution": "1K",
    },
    {
        "id": "google:gemini-3.1-flash-image",
        "label": "Nano Banana 2",
        "provider": "google",
        "upstream": "gemini-3.1-flash-image-preview",
        "edit": "semantic",
        "refs_max": 14,
        "n_max": 1,
        "stream": False,
        "aspects": ["1:1", "2:3", "3:2", "3:4", "4:3", "9:16", "16:9"],
        "qualities": [],
        "resolutions": ["512", "1K", "2K", "4K"],
        "backgrounds": [],
        "default_aspect": "1:1",
        "default_resolution": "1K",
    },
    {
        "id": "xai:grok-imagine-image-2.0",
        "label": "Grok Imagine 2.0",
        "provider": "xai",
        "upstream": "grok-imagine-image-2.0",
        "edit": "semantic",
        "refs_max": 5,
        "n_max": 1,
        "stream": False,
        "aspects": ["1:1", "3:4", "4:3", "9:16", "16:9", "2:3", "3:2"],
        "qualities": ["low", "medium"],
        "resolutions": ["1K", "2K"],
        "backgrounds": [],
        "default_aspect": "1:1",
        "default_resolution": "1K",
    },
    {
        "id": "openrouter:bytedance-seed/seedream-5-0-pro",
        "label": "Seedream 5.0 Pro",
        "provider": "openrouter",
        "upstream": "bytedance-seed/seedream-5-0-pro",
        "edit": "semantic",
        "refs_max": 14,
        "n_max": 1,
        "stream": False,
        "aspects": ["1:1", "2:3", "3:2", "3:4", "4:3", "9:16", "16:9"],
        "qualities": [],
        "resolutions": ["1K", "2K"],
        "backgrounds": [],
        "default_aspect": "1:1",
        "default_resolution": "1K",
    },
    {
        "id": "openrouter:bytedance-seed/seedream-5-0-lite",
        "label": "Seedream 5.0 Lite",
        "provider": "openrouter",
        "upstream": "bytedance-seed/seedream-5-0-lite",
        "edit": "semantic",
        "refs_max": 14,
        "n_max": 1,
        "stream": False,
        "aspects": ["1:1", "2:3", "3:2", "3:4", "4:3", "9:16", "16:9"],
        "qualities": [],
        "resolutions": ["2K", "4K"],
        "backgrounds": [],
        "default_aspect": "1:1",
        "default_resolution": "2K",
    },
    {
        "id": "openrouter:qwen/qwen-image-3-pro",
        "label": "Qwen Image 3 Pro",
        "provider": "openrouter",
        "upstream": "qwen/qwen-image-3-pro",
        "edit": "semantic",
        "refs_max": 4,
        "n_max": 1,
        "stream": False,
        "aspects": ["1:1", "2:3", "3:2", "3:4", "4:3", "9:16", "16:9"],
        "qualities": [],
        "resolutions": ["1K", "2K"],
        "backgrounds": [],
        "default_aspect": "1:1",
        "default_resolution": "1K",
    },
    {
        "id": "openrouter:microsoft/mai-image-2.5-pro",
        "label": "MAI Image 2.5 Pro",
        "provider": "openrouter",
        "upstream": "microsoft/mai-image-2.5-pro",
        "edit": "semantic",
        "refs_max": 1,
        "n_max": 1,
        "stream": False,
        "aspects": ["1:1", "4:3", "3:4", "16:9", "9:16", "3:2", "2:3"],
        "qualities": [],
        "resolutions": [],
        "backgrounds": [],
        "default_aspect": "1:1",
    },
]


def get_model(model_id: str) -> dict[str, Any]:
    for row in MODELS:
        if row["id"] == model_id:
            return row
    raise KeyError(model_id)


def public_models() -> list[dict[str, Any]]:
    from . import config

    keys = config.key_status()
    out: list[dict[str, Any]] = []
    for row in MODELS:
        item = dict(row)
        item["available"] = bool(keys.get(row["provider"], False))
        out.append(item)
    return out


def list_models() -> list[dict[str, Any]]:
    return public_models()


# OpenAI Images size map (gpt-image-2 documented canvas sizes).
OPENAI_SIZE = {
    "1:1": "1024x1024",
    "3:2": "1536x1024",
    "2:3": "1024x1536",
    "4:3": "1536x1024",
    "3:4": "1024x1536",
    "16:9": "1536x1024",
    "9:16": "1024x1536",
}


def openai_size(aspect: str) -> str:
    return OPENAI_SIZE.get(aspect) or "1024x1024"
