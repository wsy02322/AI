#!/usr/bin/env python3
"""Inject AMAP_KEY into ST-16 Tool Valves and probe Amap from this host.

Does not print the key. Does not change Pipe valves, WEBUI_SECRET_KEY, or
openai.api_configs. Merge-only: existing MAX_CALLS / MAX_VIA kept.

Env: AMAP_KEY (or AMAP_WEB_KEY), OPENWEBUI_URL / USERNAME / PASSWORD.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apply_amap_drive_route import get_tool, merge_valves
from text_web_search_ops import headers, signin

GEOCODE_URL = "https://restapi.amap.com/v3/geocode/geo"
DRIVING_URL = "https://restapi.amap.com/v5/direction/driving"


def _key() -> str:
    key = (os.environ.get("AMAP_KEY") or os.environ.get("AMAP_WEB_KEY") or "").strip()
    if not key:
        raise SystemExit("Missing AMAP_KEY (or AMAP_WEB_KEY). Do not commit it.")
    return key


def _get(url: str, params: dict[str, str], timeout: int = 20) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(f"{url}?{query}", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001 — surface upstream class only
        return {"status": "0", "info": f"http_error:{type(exc).__name__}"}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"status": "0", "info": "bad_json"}
    return data if isinstance(data, dict) else {"status": "0", "info": "not_object"}


def probe_amap(key: str) -> dict[str, Any]:
    geo = _get(GEOCODE_URL, {"key": key, "address": "北京南站", "output": "JSON"})
    geo_status = str(geo.get("status") or "")
    geo_info = str(geo.get("info") or geo.get("infocode") or "")
    location = ""
    geos = geo.get("geocodes")
    if isinstance(geos, list) and geos and isinstance(geos[0], dict):
        location = str(geos[0].get("location") or "")
    dest = _get(GEOCODE_URL, {"key": key, "address": "北京首都国际机场", "output": "JSON"})
    dest_loc = ""
    dests = dest.get("geocodes")
    if isinstance(dests, list) and dests and isinstance(dests[0], dict):
        dest_loc = str(dests[0].get("location") or "")
    origin = location or "116.378319,39.865246"
    destination = dest_loc or "116.603928,40.080111"
    drive = _get(
        DRIVING_URL,
        {
            "key": key,
            "origin": origin,
            "destination": destination,
            "strategy": "32",
            "show_fields": "cost,tmcs,polyline",
            "output": "json",
        },
    )
    drive_status = str(drive.get("status") or "")
    drive_info = str(drive.get("info") or drive.get("infocode") or "")
    km = None
    minutes = None
    has_tmc = False
    route = drive.get("route") if isinstance(drive.get("route"), dict) else {}
    paths = route.get("paths") if isinstance(route, dict) else None
    if isinstance(paths, list) and paths and isinstance(paths[0], dict):
        path = paths[0]
        try:
            km = round(float(path.get("distance") or 0) / 1000.0, 1)
        except (TypeError, ValueError):
            km = None
        cost = path.get("cost") if isinstance(path.get("cost"), dict) else {}
        try:
            minutes = int(round(float(cost.get("duration") or 0) / 60.0))
        except (TypeError, ValueError):
            minutes = None
        tmcs = path.get("tmcs")
        has_tmc = isinstance(tmcs, list) and bool(tmcs)
    ok = geo_status == "1" and drive_status == "1" and km is not None
    return {
        "ok": ok,
        "geocode_status": geo_status,
        "geocode_info": geo_info,
        "driving_status": drive_status,
        "driving_info": drive_info,
        "km": km,
        "minutes": minutes,
        "has_tmc": has_tmc,
    }


def _hint(row: dict[str, Any]) -> str:
    blob = f"{row.get('geocode_info')} {row.get('driving_info')}".upper()
    if "USERKEY_PLAT_NOMATCH" in blob:
        return "Key 类型不对：必须是 Web服务，不是 Web端(JS API) / Android / iOS"
    if "INVALID_USER_IP" in blob or "10005" in blob:
        return "IP 白名单未包含本机出口。VPS 填 78.47.152.85"
    if "INVALID_USER_SIGNATURE" in blob or "INVALID_USER_SCODE" in blob:
        return "不要开数字签名；本工具不传 sig"
    if "INVALID_USER_KEY" in blob:
        return "Key 错或过期"
    if "DAILY_QUERY_OVER_LIMIT" in blob or "USER_DAILY_QUERY_OVER_LIMIT" in blob:
        return "配额用尽"
    if row.get("ok"):
        return ""
    return "高德未返回可用路线；对照 geocode_info / driving_info"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe-only", action="store_true", help="only hit Amap, do not write OWUI valves")
    parser.add_argument("--inject-only", action="store_true", help="only merge OWUI valves, skip Amap probe")
    args = parser.parse_args()
    key = _key()
    if not args.inject_only:
        probe = probe_amap(key)
        hint = _hint(probe)
        print(
            "amap probe "
            f"ok={probe['ok']} geo={probe['geocode_status']}/{probe['geocode_info']} "
            f"drive={probe['driving_status']}/{probe['driving_info']} "
            f"km={probe['km']} minutes={probe['minutes']} tmc={probe['has_tmc']}"
        )
        if hint:
            print(f"hint: {hint}")
        if not probe["ok"]:
            print("not writing OWUI valves")
            return 1
    if not args.probe_only:
        h = headers(signin())
        status, tool = get_tool(h)
        if status != 200 or not tool:
            raise SystemExit(f"tool amap_drive_route missing ({status})")
        valves = merge_valves(h)
        print(f"owui valves key_set={bool(str(valves.get('AMAP_KEY') or '').strip())}")
    print("inject amap key ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
