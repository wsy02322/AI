#!/usr/bin/env python3
"""M1a live smoke: single-leg regression + one multi-stop China itinerary.

Writes /opt/cursor/artifacts/drive-route-m1a-smoke.json.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import AMAP_DRIVE_ROUTE_TOOL, GOOGLE_DRIVE_ROUTE_TOOL, PIPE
from text_web_search_ops import chat_with_optional_search, headers, signin, usage_cost_usd

OUT = Path(os.environ.get("M1A_SMOKE_OUT", "/opt/cursor/artifacts/drive-route-m1a-smoke.json"))
FLASH = f"{PIPE}.google.gemini-3.8-flash"
CHINA_SINGLE = (
    "用中国路线工具查询实时路况，不要凭记忆编分钟数。"
    "开车从北京南站到北京首都国际机场，现在怎么走、大概多久、路况怎么样？"
    "只要距离、时间、路况大意。不要评分、不要电话、不要画地图。"
)
CHINA_MULTI = (
    "用中国路线工具，只调用一次。"
    "开车自驾：起点西安，途经西宁、青海湖，终点张掖。"
    "把中间城市放进 via，不要每个城市单独打一次。"
    "请按段写出每一段的大概公里和分钟。不要评分、不要电话、不要画地图。"
)
OVERSEAS_SINGLE = (
    "用海外路线工具查询实时路况，不要凭记忆编分钟数。"
    "开车从纽约肯尼迪机场（JFK）到时代广场（Times Square），大概多久？"
    "只要距离、时间、路况大意。不要评分、不要电话、不要画地图。"
    "这不是中国大陆路线。"
)


def _text(result: dict) -> str:
    return result.get("text") or ""


def _calls(result: dict) -> int:
    usage = result.get("usage") or {}
    try:
        return int(usage.get("function_call_count") or 0)
    except (TypeError, ValueError):
        return 0


def _summarize(result: dict, prompt: str) -> dict:
    text = _text(result)
    return {
        "status": result.get("status"),
        "cost_usd": usage_cost_usd(result.get("usage") or {}),
        "function_call_count": _calls(result),
        "has_unavailable": "路线接口不可用" in text,
        "has_km_or_minutes": any(token in text for token in ("公里", "km", "分钟", "min", "minutes")),
        "has_xining": "西宁" in text,
        "has_zhangye": "张掖" in text,
        "has_phone": any(token in text.lower() for token in ("电话", "tel:", "phone")),
        "has_rating": any(token in text for token in ("评分", "星级", "rating")),
        "text_chars": len(text),
        "text_head": text[:500],
        "error": (result.get("error") or "")[:300],
        "prompt_head": prompt[:80],
    }


def main() -> int:
    h = headers(signin())
    tools = [AMAP_DRIVE_ROUTE_TOOL, GOOGLE_DRIVE_ROUTE_TOOL]
    china_single = chat_with_optional_search(
        h, FLASH, [{"role": "user", "content": CHINA_SINGLE}], enable_search=True, timeout=180, tool_ids=tools
    )
    china_multi = chat_with_optional_search(
        h, FLASH, [{"role": "user", "content": CHINA_MULTI}], enable_search=True, timeout=240, tool_ids=tools
    )
    overseas = chat_with_optional_search(
        h, FLASH, [{"role": "user", "content": OVERSEAS_SINGLE}], enable_search=True, timeout=180, tool_ids=tools
    )
    payload = {
        "china_single": _summarize(china_single, CHINA_SINGLE),
        "china_multi": _summarize(china_multi, CHINA_MULTI),
        "overseas_single": _summarize(overseas, OVERSEAS_SINGLE),
    }
    errors: list[str] = []
    for name in ("china_single", "china_multi", "overseas_single"):
        row = payload[name]
        if row["status"] != 200:
            errors.append(f"{name} status {row['status']}")
        if row["has_phone"] or row["has_rating"]:
            errors.append(f"{name} leaked phone/rating")
    expect_live = os.environ.get("M1A_EXPECT_LIVE", "").strip().lower() in {"1", "true", "yes"}
    if expect_live:
        single = payload["china_single"]
        multi = payload["china_multi"]
        overseas_row = payload["overseas_single"]
        if single["has_unavailable"] or not single["has_km_or_minutes"] or not single["function_call_count"]:
            errors.append("china single failed live gate")
        if multi["has_unavailable"]:
            errors.append("china multi got 路线接口不可用")
        if not multi["function_call_count"]:
            errors.append("china multi did not call the route tool")
        if multi["function_call_count"] > 3:
            errors.append(f"china multi used {multi['function_call_count']} calls, want <=3")
        if not (multi["has_xining"] and multi["has_zhangye"]):
            errors.append("china multi text missing 西宁/张掖")
        if not multi["has_km_or_minutes"]:
            errors.append("china multi missing km/minutes")
        if overseas_row["has_unavailable"] or not overseas_row["has_km_or_minutes"]:
            errors.append("overseas single failed live gate")
        if not overseas_row["function_call_count"]:
            errors.append("overseas single did not call the route tool")
    payload["errors"] = errors
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")
    for name, row in payload.items():
        if name == "errors":
            continue
        print(
            f"{name} status={row['status']} calls={row['function_call_count']} "
            f"km={row['has_km_or_minutes']} unavailable={row['has_unavailable']} "
            f"${row['cost_usd']}"
        )
    for error in errors:
        print(f"  - {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
