#!/usr/bin/env python3
"""W5 live smoke: Flash must cite a live x.com status; Grok native still works.

Writes /opt/cursor/artifacts/x-recent-search-smoke.json.
Does not change Pipe valves.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import PIPE, X_RECENT_SEARCH_TOOL
from text_web_search_ops import (
    chat_with_optional_search,
    collect_source_urls,
    event_actions,
    headers,
    has_status_action,
    signin,
    usage_cost_usd,
    web_search_requests,
)

OUT = Path(os.environ.get("X_SMOKE_OUT", "/opt/cursor/artifacts/x-recent-search-smoke.json"))
FLASH = f"{PIPE}.google.gemini-3.8-flash"
GROK = f"{PIPE}.x-ai.grok-4.6"
X_RE = re.compile(r"https?://(?:www\.)?(?:x\.com|twitter\.com)/[\w]+/status/\d+", re.I)
MAX_SINGLE_COST_USD = float(os.environ.get("W5_MAX_SINGLE_COST_USD", "2.0"))

FLASH_X_PROMPT = (
    "用 X 最近帖工具查询，不要编造推文或链接。"
    "Search X (Twitter) for a real recent post from the last 7 days about Tesla or SpaceX. "
    "Cite at least one https://x.com/ status URL from the tool result. "
    "One short paragraph plus the URL."
)
GROK_X_PROMPT = (
    "Search X (Twitter) for a real recent post from the last 7 days about Tesla or SpaceX. "
    "Cite at least one https://x.com/ or https://twitter.com/ status URL. "
    "Do not invent tweets or URLs. One short paragraph plus the URL."
)
WEB_PROMPT = (
    "What official product news did OpenAI announce this week? "
    "Cite at least one live source URL. Do not search X unless necessary."
)


def _text(result: dict) -> str:
    return result.get("text") or ""


def _function_calls(result: dict) -> int:
    usage = result.get("usage") or {}
    try:
        return int(usage.get("function_call_count") or 0)
    except (TypeError, ValueError):
        return 0


def _mentions_x_tool(result: dict) -> bool:
    blob = ((result.get("blob") or "") + _text(result)).lower()
    if X_RECENT_SEARCH_TOOL in blob or "search_x_posts" in blob or "x recent" in blob:
        return True
    if "x 最近帖" in _text(result) or "x最近帖" in _text(result):
        return True
    for item in event_actions(result.get("events") or []):
        desc = str(item.get("description") or "").lower()
        if X_RECENT_SEARCH_TOOL in desc or "search_x_posts" in desc or "x recent" in desc:
            return True
    return False


def _cost(result: dict) -> float:
    value = usage_cost_usd(result.get("usage") or {})
    return float(value) if value is not None else 0.0


def _x_url(result: dict) -> bool:
    blob = _text(result) + " " + " ".join(collect_source_urls(result.get("events") or []))
    return bool(X_RE.search(blob))


def _row(result: dict, prompt: str) -> dict:
    text = _text(result)
    return {
        "status": result.get("status"),
        "cost_usd": _cost(result),
        "function_call_count": _function_calls(result),
        "web_search_requests": web_search_requests(result.get("usage") or {}),
        "has_web_search_event": has_status_action(result.get("events") or [], "web_search"),
        "used_x_tool": _mentions_x_tool(result),
        "has_x_url": _x_url(result),
        "has_unavailable": "X 接口不可用" in text,
        "text_chars": len(text),
        "text_head": text[:400],
        "error": (result.get("error") or "")[:240],
        "prompt_head": prompt[:160],
    }


def main() -> int:
    h = headers(signin())
    flash_x = chat_with_optional_search(
        h,
        FLASH,
        [{"role": "user", "content": FLASH_X_PROMPT}],
        enable_search=True,
        timeout=180,
        tool_ids=[X_RECENT_SEARCH_TOOL],
    )
    grok_x = chat_with_optional_search(
        h, GROK, [{"role": "user", "content": GROK_X_PROMPT}], enable_search=True, timeout=300
    )
    flash_web = chat_with_optional_search(
        h,
        FLASH,
        [{"role": "user", "content": WEB_PROMPT}],
        enable_search=True,
        timeout=180,
        tool_ids=[X_RECENT_SEARCH_TOOL],
    )
    payload = {
        "flash_x": _row(flash_x, FLASH_X_PROMPT),
        "grok_x": _row(grok_x, GROK_X_PROMPT),
        "flash_web": _row(flash_web, WEB_PROMPT),
        "max_single_cost_usd": MAX_SINGLE_COST_USD,
    }
    errors: list[str] = []
    flash_row = payload["flash_x"]
    grok_row = payload["grok_x"]
    web_row = payload["flash_web"]
    if flash_row["status"] != 200:
        errors.append(f"flash_x status {flash_row['status']}")
    if grok_row["status"] != 200:
        errors.append(f"grok_x status {grok_row['status']}")
    if web_row["status"] != 200:
        errors.append(f"flash_web status {web_row['status']}")
    if flash_row["cost_usd"] > MAX_SINGLE_COST_USD:
        errors.append(f"flash_x cost ${flash_row['cost_usd']:.4f}")
    if grok_row["cost_usd"] > MAX_SINGLE_COST_USD:
        errors.append(f"grok_x cost ${grok_row['cost_usd']:.4f}")
    expect_live = os.environ.get("X_EXPECT_LIVE", "").strip().lower() in {"1", "true", "yes"}
    if expect_live:
        if flash_row["has_unavailable"]:
            errors.append("flash expected live X, got X 接口不可用")
        if not flash_row["has_x_url"]:
            errors.append("flash missing x.com/status URL")
        if not (flash_row["used_x_tool"] or flash_row["function_call_count"]):
            errors.append("flash did not call x_recent_search")
        if not grok_row["has_x_url"]:
            errors.append("grok missing x.com/status URL")
        if not (grok_row["has_x_url"] or grok_row["used_x_tool"] or grok_row["web_search_requests"]):
            errors.append("grok X regression lost search")
        if web_row["used_x_tool"] and web_row["function_call_count"] and not (
            web_row["web_search_requests"] or web_row["has_web_search_event"]
        ):
            errors.append("flash web-only question used X tool without web search")
    else:
        if not (flash_row["has_unavailable"] or flash_row["used_x_tool"] or flash_row["function_call_count"]):
            errors.append("flash did not call x_recent_search")
    payload["errors"] = errors
    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {OUT}")
    except OSError:
        fallback = Path("/tmp/x-recent-search-smoke.json")
        fallback.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {fallback}")
    print(
        f"flash_x status={flash_row['status']} x_url={flash_row['has_x_url']} "
        f"tool={flash_row['used_x_tool']} unavailable={flash_row['has_unavailable']} "
        f"${flash_row['cost_usd']:.4f}"
    )
    print(
        f"grok_x status={grok_row['status']} x_url={grok_row['has_x_url']} "
        f"${grok_row['cost_usd']:.4f}"
    )
    print(f"flash_web status={web_row['status']} used_x={web_row['used_x_tool']}")
    for error in errors:
        print(f"  - {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
