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
from amap_drive_route_tool import lookup_drive
from stack_contract import AMAP_DRIVE_ROUTE_TOOL, GOOGLE_DRIVE_ROUTE_TOOL, PIPE
from text_web_search_ops import (
    OPENWEBUI_URL,
    chat_with_optional_search,
    headers,
    signin,
    usage_cost_usd,
)
import requests

OUT = Path(os.environ.get("M1A_SMOKE_OUT", "/opt/cursor/artifacts/drive-route-m1a-smoke.json"))
FLASH = f"{PIPE}.google.gemini-3.8-flash"
CHINA_SINGLE = (
    "用中国路线工具查询实时路况，不要凭记忆编分钟数。"
    "开车从北京南站到北京首都国际机场，现在怎么走、大概多久、路况怎么样？"
    "只要距离、时间、路况大意，可以给官方导航链接。"
    "不要评分、不要电话、不要出静态示意图。"
)
CHINA_MULTI = (
    "用中国路线工具，只调用一次。"
    "开车自驾：起点西安，途经西宁、青海湖，终点张掖。"
    "把中间城市放进 via，不要每个城市单独打一次。"
    "可见回复必须有分段表（每段公里和分钟）、官方高德导航链接、"
    "以及工具返回的那一张静态示意图。"
    "不要评分、不要电话、不要第二张坐标投影图、不要贴 API key 或原始 base64。"
)
OVERSEAS_SINGLE = (
    "用海外路线工具查询实时路况，不要凭记忆编分钟数。"
    "开车从纽约肯尼迪机场（JFK）到时代广场（Times Square），大概多久？"
    "只要距离、时间、路况大意，可以给 Google 地图链接。"
    "不要评分、不要电话、不要静态示意图。"
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
        "has_amap_nav": "uri.amap.com" in text or "在高德打开" in text,
        "has_google_nav": "google.com/maps" in text or "Google 地图" in text,
        "has_markdown_image": "![" in text or "data:image" in text,
        "text_chars": len(text),
        "text_head": text[:500],
        "error": (result.get("error") or "")[:300],
        "prompt_head": prompt[:80],
    }


def _direct_china_multi(h: dict[str, str]) -> dict:
    valves = requests.get(
        f"{OPENWEBUI_URL}/api/v1/tools/id/{AMAP_DRIVE_ROUTE_TOOL}/valves",
        headers=h,
        timeout=30,
    )
    key = ""
    if valves.status_code == 200 and isinstance(valves.json(), dict):
        key = str(valves.json().get("AMAP_KEY") or "").strip()
    if not key:
        return {"ok": False, "error": "no-key"}
    raw = lookup_drive(key, "西安", "张掖", via="西宁,青海湖", max_via=8)
    data = json.loads(raw)
    legs = data.get("legs") or []
    nav = str(data.get("nav_url") or "")
    leg_navs = [str(leg.get("nav_url") or "") for leg in legs if isinstance(leg, dict)]
    uri = str(data.get("map_data_uri") or "")
    raw = json.dumps(data, ensure_ascii=False)
    return {
        "ok": bool(data.get("ok")),
        "leg_count": len(legs),
        "stops": data.get("stops") or [],
        "leg_km": [leg.get("km") for leg in legs],
        "xining_qinghai_km": legs[1]["km"] if len(legs) > 1 else None,
        "has_nav_url": any("uri.amap.com/navigation" in item for item in (*leg_navs, nav)),
        "has_app_nav": any(
            key in data for key in ("nav_app_android", "nav_app_ios", "nav_app_label")
        )
        or "amapuri://" in raw
        or "iosamap://" in raw,
        "web_via_in_nav": any("via=" in item for item in (*leg_navs, nav)),
        "has_map_data_uri": uri.startswith("data:image/"),
        "map_kind": data.get("map_kind") or "",
        "key_leaked": ("key=" in raw.lower()) or ("amap_key" in raw.lower()),
        "error": data.get("error") or "",
    }


def main() -> int:
    h = headers(signin())
    direct = _direct_china_multi(h)
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
        "direct_china_multi": direct,
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
        if not direct.get("ok") or direct.get("leg_count") != 3:
            errors.append(f"direct multi not 3 legs: {direct}")
        qh = direct.get("xining_qinghai_km")
        if qh is None or float(qh) >= 400:
            errors.append(f"西宁→青海湖 km={qh} want <400")
        if not direct.get("has_nav_url"):
            errors.append("direct multi missing amap nav_url")
        if direct.get("has_app_nav"):
            errors.append("direct multi still emits amap app nav")
        if direct.get("web_via_in_nav"):
            errors.append("direct multi web nav still has via=")
        if not direct.get("has_map_data_uri"):
            errors.append("direct multi missing map_data_uri")
        if direct.get("key_leaked"):
            errors.append("direct multi leaked key")
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
        if not multi.get("has_amap_nav"):
            errors.append("china multi missing 高德 nav link")
        if overseas_row["has_unavailable"] or not overseas_row["has_km_or_minutes"]:
            errors.append("overseas single failed live gate")
        if not overseas_row["function_call_count"]:
            errors.append("overseas single did not call the route tool")
        if not overseas_row.get("has_google_nav"):
            errors.append("overseas single missing Google Maps link")
    payload["errors"] = errors
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    written = None
    try:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(text, encoding="utf-8")
        written = OUT
    except OSError:
        fallback = Path("/tmp/drive-route-m1a-smoke.json")
        fallback.write_text(text, encoding="utf-8")
        written = fallback
    print(f"wrote {written}")
    print(f"direct_china_multi ok={direct.get('ok')} legs={direct.get('leg_count')} km={direct.get('leg_km')}")
    for name in ("china_single", "china_multi", "overseas_single"):
        row = payload[name]
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
