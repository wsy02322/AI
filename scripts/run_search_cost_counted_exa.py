#!/usr/bin/env python3
"""C-class live smoke: unmetered native (Grok/Gemini) on Exa; Anthropic stays native.

Writes /opt/cursor/artifacts/search-cost-counted-exa.json. Does not change valves.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import PIPE
from text_web_search_ops import (
    chat_with_optional_search,
    fetch_called_hard,
    fetch_called_soft,
    headers,
    search_called,
    signin,
    usage_cost_usd,
    web_search_requests,
)

OUT = Path(os.environ.get("SEARCH_COST_C_OUT", "/opt/cursor/artifacts/search-cost-counted-exa.json"))
GROK = f"{PIPE}.x-ai.grok-4.6"
FLASH = f"{PIPE}.google.gemini-3.8-flash"
GEMINI_PRO = f"{PIPE}.google.gemini-3.1-pro-preview"
OPUS = f"{PIPE}.anthropic.claude-opus-5"
CONTINUE_LIMIT = 8


def _short(model_id: str) -> str:
    prefix = PIPE + "."
    return model_id[len(prefix):] if model_id.startswith(prefix) else model_id


def _search(h: dict, model_id: str) -> dict:
    return chat_with_optional_search(
        h,
        model_id,
        [
            {
                "role": "user",
                "content": (
                    "You must call web_search. Do not answer from memory. "
                    "What official product news did OpenAI announce this week? "
                    "Cite at least one live source URL from the search results."
                ),
            }
        ],
        enable_search=True,
        timeout=300,
    )


def _fetch(h: dict, model_id: str) -> dict:
    return chat_with_optional_search(
        h,
        model_id,
        [
            {
                "role": "user",
                "content": (
                    "You must call web_fetch on this exact URL. Do not guess the page. "
                    "Read https://openrouter.ai/docs/guides/features/server-tools/web-search "
                    "and quote the sentence that says the :online variant is deprecated."
                ),
            }
        ],
        enable_search=True,
        timeout=300,
    )


def _summarize(result: dict) -> dict:
    usage = result.get("usage") or {}
    return {
        "status": result.get("status"),
        "web_search_requests": web_search_requests(usage),
        "search_called": search_called(result),
        "fetch_hard": fetch_called_hard(result),
        "fetch_soft": fetch_called_soft(result),
        "cost_usd": usage_cost_usd(usage),
        "input_tokens": usage.get("prompt_tokens") or usage.get("input_tokens"),
        "text_chars": len(result.get("text") or ""),
        "text_head": (result.get("text") or "")[:240],
        "error": (result.get("error") or "")[:300],
    }


def _ok_search(result: dict) -> bool:
    return result.get("status") == 200 and search_called(result)


def _ok_fetch(result: dict) -> bool:
    text = (result.get("text") or "").lower()
    quoted = "deprecated" in text and ":online" in text
    fetched = fetch_called_hard(result) or fetch_called_soft(result)
    return result.get("status") == 200 and (quoted or fetched)


def main() -> int:
    h = headers(signin())
    errors: list[str] = []
    rows: dict[str, dict] = {}

    for model_id in (GROK, FLASH, GEMINI_PRO, OPUS):
        short = _short(model_id)
        search = _search(h, model_id)
        fetch = _fetch(h, model_id)
        rows[f"{short}.search"] = _summarize(search)
        rows[f"{short}.fetch"] = _summarize(fetch)
        print(
            f"{short} search status={search['status']} "
            f"web_search_requests={web_search_requests(search.get('usage'))} "
            f"cost={usage_cost_usd(search.get('usage'))}"
        )
        print(
            f"{short} fetch status={fetch['status']} "
            f"quoted={('deprecated' in (fetch.get('text') or '').lower())} "
            f"cost={usage_cost_usd(fetch.get('usage'))}"
        )
        if not _ok_search(search):
            errors.append(f"{short} search failed")
        if not _ok_fetch(fetch):
            errors.append(f"{short} fetch failed")

    first = _search(h, GROK)
    continue_turn = chat_with_optional_search(
        h,
        GROK,
        [
            {
                "role": "user",
                "content": (
                    "You must call web_search. Do not answer from memory. "
                    "What official product news did OpenAI announce this week? "
                    "Cite at least one live source URL from the search results."
                ),
            },
            {"role": "assistant", "content": first.get("text") or "已根据检索整理。"},
            {"role": "user", "content": "需要我做什么吗？需要请说 不需要就你继续"},
        ],
        enable_search=True,
        timeout=360,
    )
    continue_searches = web_search_requests(continue_turn.get("usage"))
    rows["grok.continue"] = {
        **_summarize(continue_turn),
        "limit": CONTINUE_LIMIT,
        "first_search_requests": web_search_requests(first.get("usage")),
    }
    print(
        f"grok continue status={continue_turn['status']} "
        f"web_search_requests={continue_searches} "
        f"cost={usage_cost_usd(continue_turn.get('usage'))}"
    )
    if continue_turn["status"] != 200:
        errors.append(f"grok continue {continue_turn['status']}")
    elif continue_searches > CONTINUE_LIMIT:
        errors.append(f"grok continue web_search_requests={continue_searches} > {CONTINUE_LIMIT}")

    payload = {"rows": rows, "errors": errors}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"counted-exa smoke: {len(rows) - len(errors)} ok, {len(errors)} err")
    for error in errors:
        print(f"  - {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
