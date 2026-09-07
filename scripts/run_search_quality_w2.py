#!/usr/bin/env python3
"""W2 live smoke: Gemini native still searches; China traffic still uses Amap.

Does not change Pipe valves. Writes /opt/cursor/artifacts/search-quality-w2-smoke.json.
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

OUT = Path(os.environ.get("W2_SMOKE_OUT", "/opt/cursor/artifacts/search-quality-w2-smoke.json"))
FLASH = f"{PIPE}.google.gemini-3.8-flash"
MAX_SINGLE_COST_USD = float(os.environ.get("W2_MAX_SINGLE_COST_USD", "2.0"))
MAX_SEARCHES = int(os.environ.get("W2_MAX_SEARCHES", "12"))

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


def _function_calls(result: dict) -> int:
    usage = result.get("usage") or {}
    try:
        return int(usage.get("function_call_count") or 0)
    except (TypeError, ValueError):
        return 0


def _tool_mentioned(result: dict) -> bool:
    blob = (result.get("blob") or "") + _text(result)
    if AMAP_DRIVE_ROUTE_TOOL in blob or "drive_route" in blob:
        return True
    for item in event_actions(result.get("events") or []):
        desc = str(item.get("description") or "")
        if "drive_route" in desc or "China Drive" in desc or "amap" in desc.lower():
            return True
    return False


def _cost(result: dict) -> float:
    value = usage_cost_usd(result.get("usage") or {})
    return float(value) if value is not None else 0.0


def _web_row(result: dict, prompt: str) -> dict:
    text = _text(result)
    return {
        "status": result.get("status"),
        "cost_usd": _cost(result),
        "web_search_requests": web_search_requests(result.get("usage") or {}),
        "has_web_search_event": has_status_action(result.get("events") or [], "web_search"),
        "has_http_url": "http" in text.lower() or bool(collect_source_urls(result.get("events") or [])),
        "text_chars": len(text),
        "text_head": text[:400],
        "error": (result.get("error") or "")[:240],
        "prompt_head": prompt[:160],
    }


def _route_row(result: dict, prompt: str) -> dict:
    text = _text(result)
    lowered = text.lower()
    calls = _function_calls(result)
    return {
        "status": result.get("status"),
        "cost_usd": _cost(result),
        "function_call_count": calls,
        "web_search_requests": web_search_requests(result.get("usage") or {}),
        "tool_mentioned": _tool_mentioned(result) or calls >= 1,
        "has_unavailable": "路线接口不可用" in text,
        "has_km_or_minutes": any(token in text for token in ("公里", "km", "分钟", "min")),
        "has_traffic": any(token in text for token in ("路况", "畅通", "缓行", "拥堵")),
        "has_phone": any(token in lowered for token in ("电话", "tel:", "phone")),
        "has_rating": any(token in text for token in ("评分", "星级", "rating")),
        "text_chars": len(text),
        "text_head": text[:400],
        "error": (result.get("error") or "")[:240],
        "prompt_head": prompt[:160],
    }


def main() -> int:
    h = headers(signin())
    web_result = chat_with_optional_search(
        h, FLASH, [{"role": "user", "content": SHORT_PROMPT}], enable_search=True, timeout=180
    )
    route_result = chat_with_optional_search(
        h,
        FLASH,
        [{"role": "user", "content": ROUTE_PROMPT}],
        enable_search=True,
        timeout=180,
        tool_ids=[AMAP_DRIVE_ROUTE_TOOL],
    )
    payload = {
        "flash_short_web": _web_row(web_result, SHORT_PROMPT),
        "flash_china_route": _route_row(route_result, ROUTE_PROMPT),
        "max_single_cost_usd": MAX_SINGLE_COST_USD,
        "max_searches": MAX_SEARCHES,
    }
    errors: list[str] = []
    web_row = payload["flash_short_web"]
    route_row = payload["flash_china_route"]
    if web_row["status"] != 200:
        errors.append(f"flash_short_web status {web_row['status']}")
    if not (web_row["web_search_requests"] or web_row["has_web_search_event"]):
        errors.append("flash_short_web did not search")
    if web_row["cost_usd"] > MAX_SINGLE_COST_USD:
        errors.append(f"flash_short_web cost ${web_row['cost_usd']:.4f} > ${MAX_SINGLE_COST_USD}")
    if web_row["web_search_requests"] > MAX_SEARCHES:
        errors.append(f"flash_short_web searches {web_row['web_search_requests']} > {MAX_SEARCHES}")
    if route_row["status"] != 200:
        errors.append(f"flash_china_route status {route_row['status']}")
    if route_row["has_unavailable"]:
        errors.append("expected live traffic, got 路线接口不可用")
    if not (route_row["tool_mentioned"] or route_row["function_call_count"]):
        errors.append("china route did not call drive_route (must not use Google for traffic)")
    if not route_row["has_km_or_minutes"]:
        errors.append("expected km/minutes in live answer")
    if not route_row["has_traffic"]:
        errors.append("expected traffic wording")
    if not route_row.get("function_call_count"):
        errors.append("expected function_call_count>=1")
    if route_row["has_phone"] or route_row["has_rating"]:
        errors.append("route leaked phone/rating")
    if route_row["cost_usd"] > MAX_SINGLE_COST_USD:
        errors.append(f"flash_china_route cost ${route_row['cost_usd']:.4f} > ${MAX_SINGLE_COST_USD}")
    payload["errors"] = errors
    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {OUT}")
    except OSError:
        fallback = Path("/tmp/search-quality-w2-smoke.json")
        fallback.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {fallback}")
    print(
        f"flash_short_web status={web_row['status']} searches={web_row['web_search_requests']} "
        f"${web_row['cost_usd']:.4f}"
    )
    print(
        f"flash_china_route status={route_row['status']} km={route_row['has_km_or_minutes']} "
        f"traffic={route_row['has_traffic']} tool={route_row['tool_mentioned']} "
        f"calls={route_row['function_call_count']} ${route_row['cost_usd']:.4f}"
    )
    for error in errors:
        print(f"  - {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
