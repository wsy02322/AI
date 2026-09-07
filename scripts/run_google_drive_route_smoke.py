#!/usr/bin/env python3
"""W4 live smoke: overseas Google Routes + China still uses Amap.

Writes /opt/cursor/artifacts/google-drive-route-smoke.json.
Uses attached Tools; does not change Pipe valves.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import AMAP_DRIVE_ROUTE_TOOL, GOOGLE_DRIVE_ROUTE_TOOL, PIPE
from text_web_search_ops import (
    chat_with_optional_search,
    event_actions,
    headers,
    signin,
    usage_cost_usd,
)

OUT = Path(os.environ.get("GOOGLE_SMOKE_OUT", "/opt/cursor/artifacts/google-drive-route-smoke.json"))
FLASH = f"{PIPE}.google.gemini-3.8-flash"
MAX_SINGLE_COST_USD = float(os.environ.get("W4_MAX_SINGLE_COST_USD", "2.0"))
OVERSEAS_PROMPT = (
    "用海外路线工具查询实时路况，不要凭记忆编分钟数。"
    "开车从纽约肯尼迪机场（JFK）到时代广场（Times Square），现在怎么走、大概多久、路况怎么样？"
    "只要距离、时间、路况大意和大概途经点。不要评分、不要电话、不要画地图。"
    "这不是中国大陆路线，不要用中国路线工具。"
)
CHINA_PROMPT = (
    "用中国路线工具查询实时路况，不要凭记忆编分钟数。"
    "开车从北京南站到北京首都国际机场，现在怎么走、大概多久、路况怎么样？"
    "只要距离、时间、路况大意和大概途经点。不要评分、不要电话、不要画地图。"
    "这是中国大陆路线，不要用海外路线工具。"
)


def _text(result: dict) -> str:
    return result.get("text") or ""


def _function_calls(result: dict) -> int:
    usage = result.get("usage") or {}
    try:
        return int(usage.get("function_call_count") or 0)
    except (TypeError, ValueError):
        return 0


def _mentions(result: dict, *needles: str) -> bool:
    blob = ((result.get("blob") or "") + _text(result)).lower()
    if any(needle.lower() in blob for needle in needles):
        return True
    for item in event_actions(result.get("events") or []):
        desc = str(item.get("description") or "").lower()
        if any(needle.lower() in desc for needle in needles):
            return True
    return False


def _cost(result: dict) -> float:
    value = usage_cost_usd(result.get("usage") or {})
    return float(value) if value is not None else 0.0


def _summarize(result: dict, prompt: str) -> dict:
    text = _text(result)
    lowered = text.lower()
    calls = _function_calls(result)
    used_google = _mentions(
        result,
        GOOGLE_DRIVE_ROUTE_TOOL,
        "overseas_drive_route",
        "Overseas Drive",
        "海外路线工具",
    )
    used_amap = _mentions(
        result,
        AMAP_DRIVE_ROUTE_TOOL,
        "China Drive",
        "amap_drive_route",
        "中国路线工具",
    )
    blob = (result.get("blob") or "") + _text(result)
    if "drive_route" in blob and "overseas_drive_route" not in blob and not used_google:
        used_amap = True
    return {
        "status": result.get("status"),
        "cost_usd": _cost(result),
        "function_call_count": calls,
        "used_google": used_google,
        "used_amap": used_amap,
        "has_unavailable": "路线接口不可用" in text,
        "has_km_or_minutes": any(token in text for token in ("公里", "km", "分钟", "min", "minutes")),
        "has_phone": any(token in lowered for token in ("电话", "tel:", "phone")),
        "has_rating": any(token in text for token in ("评分", "星级", "rating")),
        "text_chars": len(text),
        "text_head": text[:400],
        "error": (result.get("error") or "")[:300],
        "prompt_head": prompt[:80],
    }


def main() -> int:
    h = headers(signin())
    tool_ids = [AMAP_DRIVE_ROUTE_TOOL, GOOGLE_DRIVE_ROUTE_TOOL]
    overseas = chat_with_optional_search(
        h,
        FLASH,
        [{"role": "user", "content": OVERSEAS_PROMPT}],
        enable_search=True,
        timeout=180,
        tool_ids=tool_ids,
    )
    china = chat_with_optional_search(
        h,
        FLASH,
        [{"role": "user", "content": CHINA_PROMPT}],
        enable_search=True,
        timeout=180,
        tool_ids=tool_ids,
    )
    payload = {
        "overseas": _summarize(overseas, OVERSEAS_PROMPT),
        "china": _summarize(china, CHINA_PROMPT),
        "max_single_cost_usd": MAX_SINGLE_COST_USD,
    }
    errors: list[str] = []
    overseas_row = payload["overseas"]
    china_row = payload["china"]
    if overseas_row["status"] != 200:
        errors.append(f"overseas status {overseas_row['status']}")
    if china_row["status"] != 200:
        errors.append(f"china status {china_row['status']}")
    if overseas_row["has_phone"] or overseas_row["has_rating"]:
        errors.append("overseas leaked phone/rating")
    if china_row["has_phone"] or china_row["has_rating"]:
        errors.append("china leaked phone/rating")
    if overseas_row["cost_usd"] > MAX_SINGLE_COST_USD:
        errors.append(f"overseas cost ${overseas_row['cost_usd']:.4f} > ${MAX_SINGLE_COST_USD}")
    if china_row["cost_usd"] > MAX_SINGLE_COST_USD:
        errors.append(f"china cost ${china_row['cost_usd']:.4f} > ${MAX_SINGLE_COST_USD}")
    expect_live = os.environ.get("GOOGLE_EXPECT_LIVE", "").strip().lower() in {"1", "true", "yes"}
    if expect_live:
        if overseas_row["has_unavailable"]:
            errors.append("expected live overseas traffic, got 路线接口不可用")
        if not overseas_row["has_km_or_minutes"]:
            errors.append("expected overseas km/minutes")
        if not (overseas_row["used_google"] or overseas_row["function_call_count"]):
            errors.append("overseas did not call google routes")
        if overseas_row["used_amap"] and not overseas_row["used_google"]:
            errors.append("overseas used Amap instead of Google Routes")
        if china_row["has_unavailable"]:
            errors.append("china expected live Amap, got 路线接口不可用")
        if not china_row["has_km_or_minutes"]:
            errors.append("expected china km/minutes")
        if china_row["used_google"] and not china_row["used_amap"]:
            errors.append("china used Google Routes instead of Amap")
        if not (china_row["used_amap"] or china_row["function_call_count"]):
            errors.append("china did not call Amap")
    else:
        if not (overseas_row["has_unavailable"] or overseas_row["used_google"] or overseas_row["function_call_count"]):
            errors.append("overseas did not call google routes")
    payload["errors"] = errors
    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {OUT}")
    except OSError:
        fallback = Path("/tmp/google-drive-route-smoke.json")
        fallback.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {fallback}")
    print(
        f"overseas status={overseas_row['status']} km={overseas_row['has_km_or_minutes']} "
        f"google={overseas_row['used_google']} amap={overseas_row['used_amap']} "
        f"unavailable={overseas_row['has_unavailable']} ${overseas_row['cost_usd']:.4f}"
    )
    print(
        f"china status={china_row['status']} km={china_row['has_km_or_minutes']} "
        f"google={china_row['used_google']} amap={china_row['used_amap']} "
        f"unavailable={china_row['has_unavailable']} ${china_row['cost_usd']:.4f}"
    )
    for error in errors:
        print(f"  - {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
