#!/usr/bin/env python3
"""T1 live smoke: OpenAI-class Exa + bounded continue, plus Sol/Astra Search+Fetch.

Writes /opt/cursor/artifacts/search-cost-t1.json. Does not change valves.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import ASTRA_PUBLIC_MODEL_IDS, PIPE
from text_web_search_ops import (
    chat_with_optional_search,
    fetch_called_hard,
    fetch_called_soft,
    has_status_action,
    headers,
    search_called,
    signin,
    usage_cost_usd,
    web_search_requests,
)

OUT = Path(os.environ.get("SEARCH_COST_T1_OUT", "/opt/cursor/artifacts/search-cost-t1.json"))
SOL = f"{PIPE}.openai.gpt-5.6-sol"
ASTRA = ASTRA_PUBLIC_MODEL_IDS[0] if ASTRA_PUBLIC_MODEL_IDS[0].endswith(".gpt-6-astra") else f"{PIPE}.openai.gpt-6-astra"
ASTRA_PRO = f"{PIPE}.openai.gpt-6-astra-pro"
CONTINUE_LIMIT = 8


def _short(model_id: str) -> str:
    return model_id.rsplit(".", 1)[-1]


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
        "output_tokens": usage.get("completion_tokens") or usage.get("output_tokens"),
        "text_chars": len(result.get("text") or ""),
        "text_head": (result.get("text") or "")[:240],
        "error": (result.get("error") or "")[:300],
    }


def main() -> int:
    h = headers(signin())
    errors: list[str] = []
    rows: dict[str, dict] = {}

    for model_id in (SOL, ASTRA, ASTRA_PRO):
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
            f"fetch_hard={fetch_called_hard(fetch)} "
            f"cost={usage_cost_usd(fetch.get('usage'))}"
        )
        if search["status"] != 200 or not search_called(search):
            errors.append(f"{short} search failed")
        if fetch["status"] != 200 or not (
            fetch_called_hard(fetch)
            or fetch_called_soft(fetch)
            or ("deprecated" in (fetch.get("text") or "").lower() and ":online" in (fetch.get("text") or ""))
        ):
            errors.append(f"{short} fetch failed")
        elif "deprecated" not in (fetch.get("text") or "").lower():
            errors.append(f"{short} fetch produced no page-read evidence")

    first = _search(h, ASTRA_PRO)
    continue_turn = chat_with_optional_search(
        h,
        ASTRA_PRO,
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
            {
                "role": "user",
                "content": "需要我做什么吗？需要请说 不需要就你继续",
            },
        ],
        enable_search=True,
        timeout=360,
    )
    continue_searches = web_search_requests(continue_turn.get("usage"))
    rows["astra-pro.continue"] = {
        **_summarize(continue_turn),
        "limit": CONTINUE_LIMIT,
        "first_search_requests": web_search_requests(first.get("usage")),
    }
    print(
        f"astra-pro continue status={continue_turn['status']} "
        f"web_search_requests={continue_searches} "
        f"cost={usage_cost_usd(continue_turn.get('usage'))}"
    )
    if continue_turn["status"] != 200:
        errors.append(f"astra-pro continue {continue_turn['status']}")
    elif continue_searches > CONTINUE_LIMIT:
        errors.append(
            f"astra-pro continue web_search_requests={continue_searches} > {CONTINUE_LIMIT}"
        )

    payload = {"rows": rows, "errors": errors}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"t1 smoke: {len(rows) - len(errors)} ok, {len(errors)} err")
    for error in errors:
        print(f"  - {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
