#!/usr/bin/env python3
"""W3 live smoke: Grok native should search the web and cite X.

Does not change Pipe valves. Writes /opt/cursor/artifacts/search-quality-w3-smoke.json.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import PIPE
from text_web_search_ops import (
    chat_with_optional_search,
    collect_source_urls,
    headers,
    has_status_action,
    signin,
    usage_cost_usd,
    web_search_requests,
)

OUT = Path(os.environ.get("W3_SMOKE_OUT", "/opt/cursor/artifacts/search-quality-w3-smoke.json"))
GROK = f"{PIPE}.x-ai.grok-4.6"
FLASH = f"{PIPE}.google.gemini-3.8-flash"
X_RE = re.compile(r"https?://(?:www\.)?(?:x\.com|twitter\.com)/", re.I)

X_PROMPT = (
    "Search X (Twitter) for a real recent post from the last 7 days about Tesla or SpaceX. "
    "Cite at least one https://x.com/ or https://twitter.com/ status URL. "
    "Do not invent tweets or URLs. One short paragraph plus the URL."
)
WEB_PROMPT = (
    "You must call web_search. Do not answer from memory. "
    "What official product news did OpenAI announce this week? "
    "Cite at least one live source URL from the search results."
)


def _text(result: dict) -> str:
    return result.get("text") or ""


def _x_hit(result: dict) -> bool:
    blob = _text(result) + " " + " ".join(collect_source_urls(result.get("events") or []))
    return bool(X_RE.search(blob))


def _row(result: dict, prompt: str) -> dict:
    text = _text(result)
    return {
        "status": result.get("status"),
        "cost_usd": usage_cost_usd(result.get("usage") or {}),
        "web_search_requests": web_search_requests(result.get("usage") or {}),
        "has_web_search_event": has_status_action(result.get("events") or [], "web_search"),
        "has_x_url": _x_hit(result),
        "has_http_url": "http" in text.lower() or bool(collect_source_urls(result.get("events") or [])),
        "text_chars": len(text),
        "text_head": text[:400],
        "error": (result.get("error") or "")[:240],
        "prompt_head": prompt[:160],
    }


def main() -> int:
    h = headers(signin())
    x_result = chat_with_optional_search(
        h, GROK, [{"role": "user", "content": X_PROMPT}], enable_search=True, timeout=300
    )
    web_result = chat_with_optional_search(
        h, GROK, [{"role": "user", "content": WEB_PROMPT}], enable_search=True, timeout=300
    )
    flash_result = chat_with_optional_search(
        h, FLASH, [{"role": "user", "content": WEB_PROMPT}], enable_search=True, timeout=180
    )
    payload = {
        "grok_x": _row(x_result, X_PROMPT),
        "grok_web": _row(web_result, WEB_PROMPT),
        "flash_web_regression": _row(flash_result, WEB_PROMPT),
    }
    errors: list[str] = []
    x_row = payload["grok_x"]
    web_row = payload["grok_web"]
    flash_row = payload["flash_web_regression"]
    if x_row["status"] != 200:
        errors.append(f"grok_x status {x_row['status']}")
    if not (x_row["web_search_requests"] or x_row["has_web_search_event"]):
        errors.append("grok_x did not search")
    if not x_row["has_x_url"]:
        errors.append("grok_x missing x.com/twitter.com URL")
    if web_row["status"] != 200:
        errors.append(f"grok_web status {web_row['status']}")
    if not (web_row["web_search_requests"] or web_row["has_web_search_event"] or web_row["has_http_url"]):
        errors.append("grok_web had no search evidence")
    if flash_row["status"] != 200:
        errors.append(f"flash_web status {flash_row['status']}")
    if not (flash_row["web_search_requests"] or flash_row["has_web_search_event"]):
        errors.append("flash_web regression lost search")
    payload["errors"] = errors
    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {OUT}")
    except OSError:
        fallback = Path("/tmp/search-quality-w3-smoke.json")
        fallback.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {fallback}")
    print(
        f"grok_x status={x_row['status']} searches={x_row['web_search_requests']} "
        f"x_url={x_row['has_x_url']} $"
        f"{x_row['cost_usd']:.4f}"
    )
    print(
        f"grok_web status={web_row['status']} searches={web_row['web_search_requests']} "
        f"url={web_row['has_http_url']} ${web_row['cost_usd']:.4f}"
    )
    print(
        f"flash_web status={flash_row['status']} searches={flash_row['web_search_requests']} "
        f"${flash_row['cost_usd']:.4f}"
    )
    for error in errors:
        print(f"  - {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
