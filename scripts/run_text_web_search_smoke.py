#!/usr/bin/env python3
"""Search + Fetch smoke for every WS-A allowlist model. Requires --mode attach or final."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import TEXT_WEB_SEARCH_MODEL_IDS
from text_web_search_ops import (
    chat_with_optional_search,
    has_status_action,
    has_status_description,
    headers,
    signin,
    tool_calls_executed,
    web_search_requests,
)


def _failed_tools(result: dict) -> bool:
    blob = result["blob"] + result["error"] + result["text"]
    return "No endpoints found that support tool use" in blob or "stream closed with reason: error" in blob


def main() -> int:
    h = headers(signin())
    errors: list[str] = []
    for model_id in TEXT_WEB_SEARCH_MODEL_IDS:
        short = model_id.rsplit(".", 1)[-1]
        search = chat_with_optional_search(
            h,
            model_id,
            [
                {
                    "role": "user",
                    "content": "Use web search once. What is today's UTC date? Reply with the date and one source URL.",
                }
            ],
            enable_search=True,
        )
        searches = web_search_requests(search["usage"])
        print(f"{short} search status={search['status']} web_search_requests={searches}")
        if search["status"] != 200:
            errors.append(f"{short} search {search['status']} {search['error']}")
        elif _failed_tools(search):
            errors.append(f"{short} search tool-use/stream error")
        elif searches < 1 and not has_status_action(search["events"], "web_search"):
            errors.append(f"{short} search produced no hosted web_search evidence")
            print(search["text"][:240])
        else:
            print(f"OK {short} search")

        fetch = chat_with_optional_search(
            h,
            model_id,
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
        calls = tool_calls_executed(fetch["usage"])
        print(f"{short} fetch status={fetch['status']} tool_calls_executed={calls}")
        if fetch["status"] != 200:
            errors.append(f"{short} fetch {fetch['status']} {fetch['error']}")
        elif _failed_tools(fetch):
            errors.append(f"{short} fetch tool-use/stream error")
        elif calls < 1 and not has_status_description(fetch["events"], "Fetching web page"):
            errors.append(f"{short} fetch produced no hosted web_fetch evidence")
            print(fetch["text"][:240])
        elif "deprecated" not in fetch["text"].lower() and ":online" not in fetch["text"]:
            errors.append(f"{short} fetch produced no page-read evidence")
            print(fetch["text"][:240])
        else:
            print(f"OK {short} fetch")

    print(f"allowlist smoke: {len(TEXT_WEB_SEARCH_MODEL_IDS) * 2 - len(errors)} ok, {len(errors)} err")
    for error in errors:
        print(f"  - {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
