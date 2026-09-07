#!/usr/bin/env python3
"""ST-16 live smoke: China route question + a non-route control.

Writes /opt/cursor/artifacts/amap-drive-route-smoke.json.
Uses the attached Tool; does not change Pipe valves.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import AMAP_DRIVE_ROUTE_TOOL, PIPE
from text_web_search_ops import (
    TEXT_WEB_SEARCH_FILTER,
    chat_with_optional_search,
    event_actions,
    headers,
    signin,
    usage_cost_usd,
)

OUT = Path(os.environ.get("AMAP_SMOKE_OUT", "/opt/cursor/artifacts/amap-drive-route-smoke.json"))
FLASH = f"{PIPE}.google.gemini-3.8-flash"
ROUTE_PROMPT = (
    "开车从北京南站到北京首都国际机场，现在怎么走、大概多久、路况怎么样？"
    "只要距离、时间、路况大意和大概途经点。不要评分、不要电话、不要画地图。"
)
CONTROL_PROMPT = "What is the derivative of x^2? Reply with one short sentence. Do not use tools."


def _text(result: dict) -> str:
    return result.get("text") or ""


def _tool_mentioned(result: dict) -> bool:
    blob = (result.get("blob") or "") + _text(result)
    if AMAP_DRIVE_ROUTE_TOOL in blob or "drive_route" in blob:
        return True
    for item in event_actions(result.get("events") or []):
        desc = str(item.get("description") or "")
        if "drive_route" in desc or "China Drive" in desc or "amap" in desc.lower():
            return True
    return False


def _summarize(result: dict, prompt: str) -> dict:
    text = _text(result)
    lowered = text.lower()
    return {
        "status": result.get("status"),
        "cost_usd": usage_cost_usd(result.get("usage") or {}),
        "tool_mentioned": _tool_mentioned(result),
        "has_unavailable": "路线接口不可用" in text,
        "has_km_or_minutes": any(token in text for token in ("公里", "km", "分钟", "min")),
        "has_traffic": any(token in text for token in ("路况", "畅通", "缓行", "拥堵")),
        "has_phone": any(token in lowered for token in ("电话", "tel:", "phone")),
        "has_rating": any(token in text for token in ("评分", "星级", "rating")),
        "text_chars": len(text),
        "text_head": text[:400],
        "error": (result.get("error") or "")[:300],
        "prompt_head": prompt[:80],
    }


def main() -> int:
    h = headers(signin())
    route = chat_with_optional_search(
        h,
        FLASH,
        [{"role": "user", "content": ROUTE_PROMPT}],
        enable_search=True,
        timeout=180,
        tool_ids=[AMAP_DRIVE_ROUTE_TOOL],
    )
    control = chat_with_optional_search(
        h,
        FLASH,
        [{"role": "user", "content": CONTROL_PROMPT}],
        enable_search=True,
        timeout=120,
        tool_ids=[AMAP_DRIVE_ROUTE_TOOL],
    )
    payload = {
        "route": _summarize(route, ROUTE_PROMPT),
        "control": _summarize(control, CONTROL_PROMPT),
    }
    errors: list[str] = []
    route_row = payload["route"]
    control_row = payload["control"]
    if route_row["status"] != 200:
        errors.append(f"route status {route_row['status']}")
    if route_row["has_phone"] or route_row["has_rating"]:
        errors.append("route leaked phone/rating")
    if not (route_row["has_km_or_minutes"] or route_row["has_unavailable"] or route_row["tool_mentioned"]):
        errors.append("route had no duration/distance, tool call, or unavailable")
    if control_row["status"] != 200:
        errors.append(f"control status {control_row['status']}")
    if control_row["tool_mentioned"] or control_row["has_unavailable"]:
        errors.append("control unexpectedly used drive_route")
    payload["errors"] = errors
    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {OUT}")
    except OSError:
        fallback = Path("/tmp/amap-drive-route-smoke.json")
        fallback.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {fallback}")
    print(
        f"route status={route_row['status']} km={route_row['has_km_or_minutes']} "
        f"traffic={route_row['has_traffic']} unavailable={route_row['has_unavailable']} "
        f"tool={route_row['tool_mentioned']}"
    )
    print(
        f"control status={control_row['status']} tool={control_row['tool_mentioned']}"
    )
    for error in errors:
        print(f"  - {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
