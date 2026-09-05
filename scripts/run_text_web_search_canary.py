#!/usr/bin/env python3
"""Live canary for Gemini Flash: search, fetch, zero-search, and image isolation.

Hard evidence is hosted-tool events / usage, not the model claiming it searched.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import IMAGE_MODEL_IDS, TEXT_WEB_SEARCH_CANARY_MODEL_ID
from text_web_search_ops import (
    chat_with_optional_search,
    has_source_urls,
    has_status_action,
    has_status_description,
    headers,
    signin,
    tool_calls_executed,
    web_search_requests,
)

IMAGE_SMOKE_MODEL = next(mid for mid in IMAGE_MODEL_IDS if mid.endswith("gpt-image-2"))


def _failed_tools(result: dict) -> bool:
    blob = result["blob"] + result["error"] + result["text"]
    return "No endpoints found that support tool use" in blob or "stream closed with reason: error" in blob


def main() -> int:
    h = headers(signin())
    errors: list[str] = []

    search = chat_with_optional_search(
        h,
        TEXT_WEB_SEARCH_CANARY_MODEL_ID,
        [{"role": "user", "content": "What official product news did OpenAI announce this week? Cite at least two source URLs."}],
        enable_search=True,
    )
    search_count = web_search_requests(search["usage"])
    print(f"search status={search['status']} web_search_requests={search_count} usage={search['usage']}")
    if search["status"] != 200:
        errors.append(f"search {search['status']} {search['error']}")
    elif _failed_tools(search):
        errors.append("search tool-use/stream error")
    elif search_count < 1 and not has_status_action(search["events"], "web_search"):
        errors.append("search produced no hosted web_search events/usage")
        print(search["text"][:400])
    elif not has_source_urls(search["events"]) and "https://" not in search["text"]:
        errors.append("search produced no citation URLs")
        print(search["text"][:400])
    else:
        print("OK search hosted-tool evidence present")
        print(search["text"][:300])

    fetch = chat_with_optional_search(
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
    fetch_calls = tool_calls_executed(fetch["usage"])
    print(f"fetch status={fetch['status']} tool_calls_executed={fetch_calls}")
    if fetch["status"] != 200:
        errors.append(f"fetch {fetch['status']} {fetch['error']}")
    elif _failed_tools(fetch):
        errors.append("fetch tool-use/stream error")
    elif fetch_calls < 1 and not has_status_description(fetch["events"], "Fetching web page"):
        errors.append("fetch produced no hosted web_fetch events/usage")
        print(fetch["text"][:400])
    elif "deprecated" not in fetch["text"].lower() and ":online" not in fetch["text"]:
        errors.append("fetch produced no page-read evidence")
        print(fetch["text"][:400])
    else:
        print("OK fetch hosted-tool evidence present")
        print(fetch["text"][:300])

    idle = chat_with_optional_search(
        h,
        TEXT_WEB_SEARCH_CANARY_MODEL_ID,
        [{"role": "user", "content": "Reply with only the word OK. Do not search the web and do not fetch any URL."}],
        enable_search=True,
    )
    idle_searches = web_search_requests(idle["usage"])
    print(f"idle status={idle['status']} web_search_requests={idle_searches} usage={idle['usage']}")
    if idle["status"] != 200:
        errors.append(f"idle {idle['status']} {idle['error']}")
    elif idle_searches or has_status_action(idle["events"], "web_search"):
        errors.append(f"idle unexpectedly searched ({idle_searches})")
    else:
        print("OK idle had no search tool events")

    image = chat_with_optional_search(
        h,
        IMAGE_SMOKE_MODEL,
        [{"role": "user", "content": "Generate a tiny red square, nothing else."}],
        enable_search=False,
    )
    print(f"image status={image['status']}")
    if image["status"] != 200:
        errors.append(f"image {image['status']} {image['error']}")
    elif _failed_tools(image):
        errors.append("image tool-use 404")
    else:
        print("OK image smoke had no tool-use 404")

    print(f"canary live: {4 - len(errors)} ok, {len(errors)} err")
    for error in errors:
        print(f"  - {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
