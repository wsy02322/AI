#!/usr/bin/env python3
"""W6 production smoke: Sol/Astra Pro native search; China route still Amap.

Does not change Pipe valves. Writes /opt/cursor/artifacts/search-quality-w6-smoke.json.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import AMAP_DRIVE_ROUTE_TOOL, PIPE
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

OUT = Path(os.environ.get("W6_SMOKE_OUT", "/opt/cursor/artifacts/search-quality-w6-smoke.json"))
SOL = f"{PIPE}.openai.gpt-5.6-sol"
ASTRA_PRO = f"{PIPE}.openai.gpt-6-astra-pro"
MAX_SINGLE_COST_USD = float(os.environ.get("W6_MAX_SINGLE_COST_USD", "3.0"))
MAX_SEARCHES = int(os.environ.get("W6_MAX_SEARCHES", "6"))

SHORT_PROMPT = (
    "What official product news did OpenAI announce this week? "
    "Cite at least one live source URL."
)
ROUTE_PROMPT = (
    "用路线工具查询实时路况，不要凭记忆编分钟数。"
    "开车从北京南站到北京首都国际机场，现在怎么走、大概多久、路况怎么样？"
    "只要距离、时间、路况大意和大概途经点。不要评分、不要电话、不要画地图。"
)


def _text(result: dict) -> str:
    return result.get("text") or ""


def _cost(result: dict) -> float:
    value = usage_cost_usd(result.get("usage") or {})
    return float(value) if value is not None else 0.0


def _function_calls(result: dict) -> int:
    usage = result.get("usage") or {}
    try:
        return int(usage.get("function_call_count") or 0)
    except (TypeError, ValueError):
        return 0


def _row(result: dict, prompt: str) -> dict:
    text = _text(result)
    return {
        "status": result.get("status"),
        "cost_usd": _cost(result),
        "web_search_requests": web_search_requests(result.get("usage") or {}),
        "function_call_count": _function_calls(result),
        "has_web_search_event": has_status_action(result.get("events") or [], "web_search"),
        "has_http_url": "http" in text.lower() or bool(collect_source_urls(result.get("events") or [])),
        "text_chars": len(text),
        "text_head": text[:400],
        "error": (result.get("error") or "")[:240],
        "prompt_head": prompt[:160],
    }


def main() -> int:
    h = headers(signin())
    sol = chat_with_optional_search(
        h, SOL, [{"role": "user", "content": SHORT_PROMPT}], enable_search=True, timeout=180
    )
    astra = chat_with_optional_search(
        h, ASTRA_PRO, [{"role": "user", "content": SHORT_PROMPT}], enable_search=True, timeout=240
    )
    route = chat_with_optional_search(
        h, SOL, [{"role": "user", "content": ROUTE_PROMPT}], enable_search=True, timeout=180
    )
    payload = {
        "sol_web": _row(sol, SHORT_PROMPT),
        "astra_pro_web": _row(astra, SHORT_PROMPT),
        "sol_china_route": _row(route, ROUTE_PROMPT),
    }
    errors: list[str] = []
    for key in ("sol_web", "astra_pro_web"):
        row = payload[key]
        if row["status"] != 200:
            errors.append(f"{key} status {row['status']}")
        if row["cost_usd"] > MAX_SINGLE_COST_USD:
            errors.append(f"{key} cost ${row['cost_usd']:.4f}")
        if row["web_search_requests"] < 1 and not row["has_web_search_event"]:
            errors.append(f"{key} did not search")
        if row["web_search_requests"] > MAX_SEARCHES:
            errors.append(f"{key} searches {row['web_search_requests']} > {MAX_SEARCHES}")
        if not row["has_http_url"]:
            errors.append(f"{key} missing live URL")
    route_row = payload["sol_china_route"]
    if route_row["status"] != 200:
        errors.append(f"route status {route_row['status']}")
    blob = ((route.get("blob") or "") + _text(route)).lower()
    used_amap = AMAP_DRIVE_ROUTE_TOOL in blob or "amap" in blob or route_row["function_call_count"]
    if not used_amap:
        for item in event_actions(route.get("events") or []):
            desc = str(item.get("description") or "").lower()
            if "amap" in desc or "drive_route" in desc or "china drive" in desc:
                used_amap = True
    if not used_amap:
        errors.append("china route did not use Amap")
    payload["errors"] = errors
    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {OUT}")
    except OSError:
        fallback = Path("/tmp/search-quality-w6-smoke.json")
        fallback.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {fallback}")
    print(
        f"sol_web searches={payload['sol_web']['web_search_requests']} "
        f"${payload['sol_web']['cost_usd']:.4f}"
    )
    print(
        f"astra_pro_web searches={payload['astra_pro_web']['web_search_requests']} "
        f"${payload['astra_pro_web']['cost_usd']:.4f}"
    )
    print(
        f"sol_china_route calls={payload['sol_china_route']['function_call_count']} "
        f"searches={payload['sol_china_route']['web_search_requests']}"
    )
    for error in errors:
        print(f"  - {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
