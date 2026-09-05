#!/usr/bin/env python3
"""Live canary for Gemini Flash: search, fetch, zero-search, and image isolation."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import IMAGE_MODEL_IDS, TEXT_WEB_SEARCH_CANARY_MODEL_ID, TEXT_WEB_SEARCH_FILTER
from text_web_search_ops import OPENWEBUI_URL, headers, signin

IMAGE_SMOKE_MODEL = next(mid for mid in IMAGE_MODEL_IDS if mid.endswith("gpt-image-2"))


def _collect_stream(h: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(
        f"{OPENWEBUI_URL}/api/chat/completions",
        headers=h,
        json=payload,
        timeout=240,
        stream=True,
    )
    raw = response.text if response.status_code != 200 else ""
    events: list[dict[str, Any]] = []
    text_parts: list[str] = []
    if response.status_code == 200:
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            events.append(chunk)
            choices = chunk.get("choices") or []
            if choices:
                delta = (choices[0].get("delta") or {}).get("content")
                message = (choices[0].get("message") or {}).get("content")
                if isinstance(delta, str):
                    text_parts.append(delta)
                elif isinstance(message, str):
                    text_parts.append(message)
    blob = json.dumps(events, ensure_ascii=False)
    return {
        "status": response.status_code,
        "error": raw[:600],
        "events": events,
        "text": "".join(text_parts),
        "blob": blob,
        "usage": next((e.get("usage") for e in reversed(events) if isinstance(e, dict) and e.get("usage")), {}),
    }


def _chat(h: dict[str, str], model_id: str, messages: list[dict[str, str]], *, enable_search: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model_id,
        "messages": messages,
        "stream": True,
        "features": {"web_search": False},
    }
    if enable_search:
        payload["filter_ids"] = [TEXT_WEB_SEARCH_FILTER]
        payload["metadata"] = {"filter_ids": [TEXT_WEB_SEARCH_FILTER]}
    return _collect_stream(h, payload)


def _has_tool(blob: str, *needles: str) -> bool:
    lowered = blob.lower()
    return any(needle.lower() in lowered for needle in needles)


def main() -> int:
    h = headers(signin())
    errors: list[str] = []

    search = _chat(
        h,
        TEXT_WEB_SEARCH_CANARY_MODEL_ID,
        [{"role": "user", "content": "What official product news did OpenAI announce this week? Cite at least two source URLs."}],
        enable_search=True,
    )
    print(f"search status={search['status']} usage={search['usage']}")
    if search["status"] != 200:
        errors.append(f"search {search['status']} {search['error']}")
    elif "No endpoints found that support tool use" in search["blob"] + search["error"]:
        errors.append("search tool-use 404")
    elif not _has_tool(search["blob"] + search["text"], "openrouter:web_search", "web_search", "url_citation", "http://", "https://"):
        errors.append("search produced no tool/citation evidence")
        print(search["text"][:400])
    else:
        print("OK search evidence present")
        print(search["text"][:300])

    fetch = _chat(
        h,
        TEXT_WEB_SEARCH_CANARY_MODEL_ID,
        [
            {
                "role": "user",
                "content": (
                    "Read https://openrouter.ai/docs/guides/features/server-tools/web-search "
                    "and quote the sentence that says the :online variant is deprecated."
                ),
            }
        ],
        enable_search=True,
    )
    print(f"fetch status={fetch['status']}")
    if fetch["status"] != 200:
        errors.append(f"fetch {fetch['status']} {fetch['error']}")
    elif not _has_tool(fetch["blob"] + fetch["text"], "openrouter:web_fetch", "web_fetch", "deprecated", ":online"):
        errors.append("fetch produced no page-read evidence")
        print(fetch["text"][:400])
    else:
        print("OK fetch evidence present")
        print(fetch["text"][:300])

    idle = _chat(
        h,
        TEXT_WEB_SEARCH_CANARY_MODEL_ID,
        [{"role": "user", "content": "Reply with only the word OK. Do not search the web and do not fetch any URL."}],
        enable_search=True,
    )
    print(f"idle status={idle['status']} usage={idle['usage']}")
    if idle["status"] != 200:
        errors.append(f"idle {idle['status']} {idle['error']}")
    elif _has_tool(idle["blob"], "openrouter:web_search", "web_search_call", "web_search_requests"):
        usage = idle["usage"] or {}
        requests_count = ((usage.get("server_tool_use") or {}).get("web_search_requests"))
        if requests_count:
            errors.append(f"idle unexpectedly searched ({requests_count})")
        else:
            print("WARN idle blob mentioned search tokens but no request count; inspect manually")
            print(idle["text"][:200])
    else:
        print("OK idle had no search tool events")

    image = _chat(
        h,
        IMAGE_SMOKE_MODEL,
        [{"role": "user", "content": "Generate a tiny red square, nothing else."}],
        enable_search=False,
    )
    print(f"image status={image['status']}")
    if image["status"] != 200:
        errors.append(f"image {image['status']} {image['error']}")
    elif "No endpoints found that support tool use" in image["blob"] + image["error"] + image["text"]:
        errors.append("image tool-use 404")
    else:
        print("OK image smoke had no tool-use 404")

    print(f"canary live: {4 - len(errors)} ok, {len(errors)} err")
    for error in errors:
        print(f"  - {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
