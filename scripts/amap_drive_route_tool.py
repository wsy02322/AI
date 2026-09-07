"""
title: China Drive Route
author: micropigeon
id: amap_drive_route
description: Amap driving route and traffic for China. Compact JSON, via stops, official nav link, optional static map.
version: 1.2.0
"""

from __future__ import annotations

import base64
import json
import math
import os
import re
import time
import urllib.parse
import urllib.request
from typing import Any, Callable

from pydantic import BaseModel, Field

AMAP_DRIVE_ROUTE_V1 = "AMAP_DRIVE_ROUTE_V1"
AMAP_DRIVE_ROUTE_M1A_V1 = "AMAP_DRIVE_ROUTE_M1A_V1"
AMAP_DRIVE_ROUTE_MAP_LITE_V1 = "AMAP_DRIVE_ROUTE_MAP_LITE_V1"
UNAVAILABLE = "路线接口不可用"
NOTE = "分钟数是路网估算；实时路况只代表现在"
MAX_STOPS = 8
MAX_VIA_STOPS = 6
LEG_VIA_CAP = 8
MIX_HINT = "中国大陆与海外站点请拆开，海外用 Overseas Drive Route"
COORD_RE = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$"
)
TMC_LABELS = ("未知", "畅通", "缓行", "拥堵", "严重拥堵")
GEOCODE_URL = "https://restapi.amap.com/v3/geocode/geo"
PLACE_URL = "https://restapi.amap.com/v3/place/text"
DRIVING_URL = "https://restapi.amap.com/v5/direction/driving"
STATICMAP_URL = "https://restapi.amap.com/v3/staticmap"
JUMP_M = 400000.0

_CALLS: dict[str, tuple[float, int]] = {}
HttpFn = Callable[[str, dict[str, str]], dict[str, Any]]


def parse_via(via: Any) -> list[str]:
    if via is None:
        return []
    if isinstance(via, (list, tuple)):
        parts = [str(item).strip() for item in via]
    else:
        text = str(via).strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                parts = [str(item).strip() for item in parsed]
            else:
                parts = re.split(r"[;|，,、/]+", text)
        else:
            parts = re.split(r"[;|，,、/]+", text)
    return [part.strip() for part in parts if part and part.strip()]


def stop_region(lng: float, lat: float) -> str:
    if 113.75 <= lng <= 114.5 and 22.13 <= lat <= 22.58:
        return "overseas"
    if 113.52 <= lng <= 113.63 and 22.10 <= lat <= 22.22:
        return "overseas"
    if 119.3 <= lng <= 122.1 and 21.8 <= lat <= 25.4:
        return "overseas"
    if 73.0 <= lng <= 135.1 and 18.0 <= lat <= 53.7:
        return "cn"
    return "overseas"


def amap_nav_url(resolved: list[tuple[str, tuple[float, float]]]) -> str:
    origin_name, (olng, olat) = resolved[0]
    dest_name, (dlng, dlat) = resolved[-1]
    params = {
        "from": f"{olng},{olat},{origin_name}",
        "to": f"{dlng},{dlat},{dest_name}",
        "mode": "car",
        "policy": "1",
        "src": "micropigeon",
        "coordinate": "gaode",
        "callnative": "0",
    }
    if len(resolved) > 2:
        params["via"] = ";".join(
            f"{lng},{lat},{name}" for name, (lng, lat) in resolved[1:-1]
        )
    return "https://uri.amap.com/navigation?" + urllib.parse.urlencode(params)


def fetch_amap_static_png(
    key: str,
    resolved: list[tuple[str, tuple[float, float]]],
    *,
    http: HttpFn | None = None,
) -> bytes | None:
    markers = "|".join(
        f"mid,0xC53030,{index + 1}:{lng},{lat}"
        for index, (_name, (lng, lat)) in enumerate(resolved)
    )
    path = "5,0x2B6CB0,1,,:" + ";".join(f"{lng},{lat}" for _name, (lng, lat) in resolved)
    params = {
        "key": key,
        "size": "600*400",
        "markers": markers,
        "paths": path,
    }
    if http is not None:
        data = http(STATICMAP_URL, params)
        raw = data.get("_bytes") if isinstance(data, dict) else None
        return raw if isinstance(raw, (bytes, bytearray)) else None
    query = urllib.parse.urlencode(params, safe=":|,;")
    request = urllib.request.Request(
        f"{STATICMAP_URL}?{query}",
        headers={"User-Agent": "micropigeon-amap-drive/1.2"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read()
    except Exception:
        return None
    if raw[:8] == b"\x89PNG\r\n\x1a\n" or raw[:2] == b"\xff\xd8":
        return bytes(raw)
    return None


def attach_closeout(
    payload: dict[str, Any],
    resolved: list[tuple[str, tuple[float, float]]],
    *,
    key: str,
    include_map: bool,
    http: HttpFn | None = None,
) -> dict[str, Any]:
    payload["nav_url"] = amap_nav_url(resolved)
    payload["nav_label"] = "在高德打开这条路线"
    if include_map:
        png = fetch_amap_static_png(key, resolved, http=http)
        if png:
            payload["map_data_uri"] = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
            payload["map_kind"] = "amap_static"
    return payload


def attach_itinerary(compact: dict[str, Any], legs: list[dict[str, Any]], stops: list[str]) -> dict[str, Any]:
    compact["traffic_as_of"] = "now"
    compact["note"] = NOTE
    compact["stops"] = stops
    compact["legs"] = legs
    compact["totals"] = {"km": compact["km"], "minutes": compact["minutes"]}
    return compact


def leg_from_compact(compact: dict[str, Any], *, max_via: int) -> dict[str, Any]:
    via = compact.get("via") or []
    cap = max(4, min(int(max_via), LEG_VIA_CAP))
    if len(via) > cap:
        via = via[: cap - 1] + via[-1:]
    return {
        "from": compact["origin"]["name"],
        "to": compact["destination"]["name"],
        "km": compact["km"],
        "minutes": compact["minutes"],
        "traffic": compact["traffic"],
        "roads": compact.get("roads") or [],
        "via": via,
    }


def fail(message: str = UNAVAILABLE, **extra: Any) -> str:
    payload = {
        "ok": False,
        "error": message,
        "hint": "不要编造精确分钟数冒充路况",
    }
    payload.update(extra)
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def parse_coord(text: str) -> tuple[float, float] | None:
    match = COORD_RE.match(text or "")
    if not match:
        return None
    lng, lat = float(match.group(1)), float(match.group(2))
    if abs(lng) > 180 or abs(lat) > 90:
        return None
    return lng, lat


def fmt_coord(lng: float, lat: float) -> str:
    return f"{lng:.6f},{lat:.6f}"


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    radius = 6371000.0
    lng1, lat1 = math.radians(a[0]), math.radians(a[1])
    lng2, lat2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(min(1.0, h)))


def parse_polyline(raw: str) -> list[tuple[float, float]]:
    if not isinstance(raw, str) or not raw.strip():
        return []
    text = raw.strip()
    if ";" in text:
        chunks = [part for part in text.split(";") if part.strip()]
        points: list[tuple[float, float]] = []
        for chunk in chunks:
            parsed = parse_coord(chunk)
            if parsed:
                points.append(parsed)
        return points
    nums: list[float] = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            nums.append(float(part))
        except ValueError:
            return []
    return [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]


def sparse_via(
    points: list[tuple[float, float]],
    *,
    total_m: float,
    max_points: int,
    spacing_m: float = 1000.0,
) -> list[list[float]]:
    if not points:
        return []
    cap = max(4, min(int(max_points), 40))
    if total_m <= 0:
        total_m = sum(haversine_m(points[i], points[i + 1]) for i in range(len(points) - 1))
    step = spacing_m
    if total_m / max(step, 1) + 1 > cap:
        step = total_m / max(cap - 1, 1)
    picked = [points[0]]
    acc = 0.0
    next_at = step
    for index in range(1, len(points)):
        acc += haversine_m(points[index - 1], points[index])
        if acc >= next_at:
            picked.append(points[index])
            next_at += step
            if len(picked) >= cap - 1:
                break
    if picked[-1] != points[-1]:
        picked.append(points[-1])
    return [[round(lng, 5), round(lat, 5)] for lng, lat in picked[:cap]]


def traffic_summary(tmcs: list[dict[str, Any]]) -> tuple[str, dict[str, float]]:
    dist: dict[str, float] = {label: 0.0 for label in TMC_LABELS}
    for item in tmcs:
        if not isinstance(item, dict):
            continue
        status = str(item.get("tmc_status") or item.get("status") or "未知")
        if status not in dist:
            status = "未知"
        try:
            meters = float(item.get("tmc_distance") or item.get("distance") or 0)
        except (TypeError, ValueError):
            meters = 0.0
        dist[status] += max(0.0, meters)
    total = sum(dist.values())
    share = {
        label: round(meters / total, 3)
        for label, meters in dist.items()
        if meters > 0 and total > 0
    }
    jam = share.get("拥堵", 0) + share.get("严重拥堵", 0)
    slow = share.get("缓行", 0)
    smooth = share.get("畅通", 0)
    if total <= 0:
        text = "路况未知"
    elif jam >= 0.3:
        text = "较多拥堵"
    elif smooth >= 0.7 and jam < 0.1:
        text = "畅通为主" + ("，局部缓行" if slow >= 0.1 else "")
    elif slow >= 0.3:
        text = "缓行为主"
    else:
        text = "路况一般"
    return text, share


def collect_tmcs(path: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    direct = path.get("tmcs")
    if isinstance(direct, list):
        out.extend(item for item in direct if isinstance(item, dict))
    steps = path.get("steps")
    if isinstance(steps, list):
        for step in steps:
            if not isinstance(step, dict):
                continue
            tmcs = step.get("tmcs")
            if isinstance(tmcs, list):
                out.extend(item for item in tmcs if isinstance(item, dict))
    return out


def collect_roads(path: dict[str, Any], *, limit: int = 6) -> list[str]:
    names: list[str] = []
    steps = path.get("steps")
    if not isinstance(steps, list):
        return names
    for step in steps:
        if not isinstance(step, dict):
            continue
        name = str(step.get("road_name") or "").strip()
        if name and name not in names:
            names.append(name)
        if len(names) >= limit:
            break
    return names


def compact_route(
    *,
    origin_name: str,
    dest_name: str,
    origin: tuple[float, float],
    dest: tuple[float, float],
    path: dict[str, Any],
    max_via: int,
) -> dict[str, Any]:
    try:
        meters = float(path.get("distance") or 0)
    except (TypeError, ValueError):
        meters = 0.0
    cost = path.get("cost") if isinstance(path.get("cost"), dict) else {}
    try:
        seconds = float(cost.get("duration") or path.get("duration") or 0)
    except (TypeError, ValueError):
        seconds = 0.0
    points = parse_polyline(str(path.get("polyline") or ""))
    if not points:
        for step in path.get("steps") or []:
            if isinstance(step, dict):
                points.extend(parse_polyline(str(step.get("polyline") or "")))
    traffic, share = traffic_summary(collect_tmcs(path))
    return {
        "ok": True,
        "provider": "amap",
        "crs": "GCJ-02",
        "origin": {
            "name": origin_name,
            "lng": round(origin[0], 5),
            "lat": round(origin[1], 5),
        },
        "destination": {
            "name": dest_name,
            "lng": round(dest[0], 5),
            "lat": round(dest[1], 5),
        },
        "km": round(meters / 1000.0, 1),
        "minutes": int(round(seconds / 60.0)) if seconds else 0,
        "traffic": traffic,
        "traffic_share": share,
        "roads": collect_roads(path),
        "via": sparse_via(points, total_m=meters, max_points=max_via),
    }


def amap_get(url: str, params: dict[str, str], http: HttpFn | None = None) -> dict[str, Any]:
    if http is not None:
        return http(url, params)
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{url}?{query}",
        headers={"User-Agent": "micropigeon-amap-drive/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except Exception:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def geocode_place(
    key: str,
    place: str,
    http: HttpFn | None = None,
    city: str = "",
) -> tuple[str, tuple[float, float], str] | None:
    parsed = parse_coord(place)
    if parsed:
        return place.strip(), parsed, city
    params = {"key": key, "address": place, "output": "JSON"}
    if city:
        params["city"] = city
    data = amap_get(GEOCODE_URL, params, http)
    if str(data.get("status")) != "1":
        return None
    geos = data.get("geocodes")
    if not isinstance(geos, list) or not geos:
        return None
    first = geos[0] if isinstance(geos[0], dict) else {}
    location = parse_coord(str(first.get("location") or ""))
    if not location:
        return None
    name = str(first.get("formatted_address") or place).strip() or place
    hint = str(first.get("city") or first.get("province") or city).strip()
    return name, location, hint


def place_search(
    key: str,
    place: str,
    city: str,
    http: HttpFn | None = None,
) -> tuple[str, tuple[float, float], str] | None:
    if not place or not city:
        return None
    data = amap_get(
        PLACE_URL,
        {
            "key": key,
            "keywords": place,
            "city": city,
            "offset": "1",
            "page": "1",
            "extensions": "base",
        },
        http,
    )
    if str(data.get("status")) != "1":
        return None
    pois = data.get("pois")
    if not isinstance(pois, list) or not pois or not isinstance(pois[0], dict):
        return None
    first = pois[0]
    location = parse_coord(str(first.get("location") or ""))
    if not location:
        return None
    name = str(first.get("name") or place).strip() or place
    hint = str(first.get("cityname") or first.get("pname") or city).strip()
    return name, location, hint


def is_admin_city_match(query: str, formatted: str, city_field: str) -> bool:
    q = (query or "").replace("市", "").strip()
    if not q:
        return False
    city = (city_field or "").replace("市", "").strip()
    if city and city == q:
        return True
    text = formatted or ""
    return text.endswith(q + "市") or f"{q}市" in text


def resolve_stop(
    key: str,
    place: str,
    *,
    prev_xy: tuple[float, float] | None = None,
    prev_city: str = "",
    http: HttpFn | None = None,
) -> tuple[str, tuple[float, float], str] | None:
    geo = geocode_place(key, place, http, city="")
    if geo is None and prev_city:
        return place_search(key, place, prev_city, http)
    if geo is None:
        return None
    name, xy, city = geo
    if (
        prev_xy is not None
        and prev_city
        and haversine_m(prev_xy, xy) > JUMP_M
        and not is_admin_city_match(place, name, city)
    ):
        poi = place_search(key, place, prev_city, http)
        if poi is not None and haversine_m(prev_xy, poi[1]) < haversine_m(prev_xy, xy):
            return poi
    return name, xy, city or prev_city


def drive_one(
    key: str,
    origin_name: str,
    dest_name: str,
    origin_xy: tuple[float, float],
    dest_xy: tuple[float, float],
    *,
    max_via: int,
    http: HttpFn | None = None,
) -> dict[str, Any] | None:
    data = amap_get(
        DRIVING_URL,
        {
            "key": key,
            "origin": fmt_coord(*origin_xy),
            "destination": fmt_coord(*dest_xy),
            "strategy": "32",
            "show_fields": "cost,tmcs,polyline",
            "output": "json",
        },
        http,
    )
    if str(data.get("status")) != "1":
        return None
    route = data.get("route") if isinstance(data.get("route"), dict) else {}
    paths = route.get("paths")
    if not isinstance(paths, list) or not paths or not isinstance(paths[0], dict):
        return None
    return compact_route(
        origin_name=origin_name,
        dest_name=dest_name,
        origin=origin_xy,
        dest=dest_xy,
        path=paths[0],
        max_via=max_via,
    )


def lookup_drive(
    key: str,
    origin: str,
    destination: str,
    *,
    max_via: int,
    via: Any = "",
    http: HttpFn | None = None,
) -> str:
    via_stops = parse_via(via)
    if len(via_stops) > MAX_VIA_STOPS:
        return fail(UNAVAILABLE, too_many=True)
    labels = [origin, *via_stops, destination]
    if len(labels) > MAX_STOPS:
        return fail(UNAVAILABLE, too_many=True)
    resolved: list[tuple[str, tuple[float, float]]] = []
    prev_xy: tuple[float, float] | None = None
    prev_city = ""
    for label in labels:
        place = resolve_stop(key, label, prev_xy=prev_xy, prev_city=prev_city, http=http)
        if not place:
            return fail()
        name, xy, city = place
        if stop_region(*xy) != "cn":
            return fail(UNAVAILABLE, mix=True, hint=MIX_HINT)
        resolved.append((name, xy))
        prev_xy = xy
        prev_city = city or prev_city
    leg_max = min(int(max_via), LEG_VIA_CAP) if len(resolved) > 2 else int(max_via)
    compacts: list[dict[str, Any]] = []
    for index in range(len(resolved) - 1):
        start_name, start_xy = resolved[index]
        end_name, end_xy = resolved[index + 1]
        compact = drive_one(
            key,
            start_name,
            end_name,
            start_xy,
            end_xy,
            max_via=leg_max,
            http=http,
        )
        if compact is None:
            return fail()
        compacts.append(compact)
    first = compacts[0]
    last = compacts[-1]
    totals_km = round(sum(item["km"] for item in compacts), 1)
    totals_min = int(sum(item["minutes"] for item in compacts))
    legs = [leg_from_compact(item, max_via=leg_max) for item in compacts]
    payload = {
        "ok": True,
        "provider": "amap",
        "crs": "GCJ-02",
        "origin": first["origin"],
        "destination": last["destination"],
        "km": totals_km,
        "minutes": totals_min,
        "traffic": first["traffic"] if len(compacts) == 1 else "分段见 legs",
        "traffic_share": first.get("traffic_share") if len(compacts) == 1 else {},
        "roads": first.get("roads") or [],
        "via": first.get("via") or [],
    }
    if len(compacts) == 1:
        payload["traffic"] = first["traffic"]
        payload["traffic_share"] = first.get("traffic_share") or {}
        payload["roads"] = first.get("roads") or []
        payload["via"] = first.get("via") or []
    attach_itinerary(payload, legs, [name for name, _xy in resolved])
    attach_closeout(
        payload,
        resolved,
        key=key,
        include_map=len(resolved) >= 3,
        http=http,
    )
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def allow_call(chat_id: str, limit: int, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    stamp, count = _CALLS.get(chat_id, (now, 0))
    if now - stamp > 120:
        count = 0
        stamp = now
    if count >= limit:
        _CALLS[chat_id] = (stamp, count)
        return False
    _CALLS[chat_id] = (stamp, count + 1)
    return True


class Tools:
    class Valves(BaseModel):
        AMAP_KEY: str = Field(default="", description="Amap Web Service key. Not committed.")
        MAX_CALLS_PER_TURN: int = Field(default=3, ge=1, le=5)
        MAX_VIA_POINTS: int = Field(default=24, ge=4, le=40)

    def __init__(self) -> None:
        self.valves = self.Valves()

    def _key(self) -> str:
        valve = (self.valves.AMAP_KEY or "").strip()
        if valve:
            return valve
        return (os.environ.get("AMAP_KEY") or os.environ.get("AMAP_WEB_KEY") or "").strip()

    def drive_route(
        self,
        origin: str,
        destination: str,
        via: str = "",
        __metadata__: dict | None = None,
    ) -> str:
        """Must-use tool for mainland China driving time, traffic, or a multi-day road trip.

        Call once. For 西安→西宁→青海湖→张掖 put middle cities in via (comma or
        semicolon, max 6). Do not call once per city. Hong Kong / Macau / Taiwan
        and overseas cities: use Overseas Drive Route instead. origin/destination:
        place name or 'lng,lat' (GCJ-02). Returns compact JSON: km, minutes,
        traffic, legs[], totals, nav_url. Multi-stop also returns map_data_uri
        (Amap static schematic). In the visible reply: (1) a legs table,
        (2) markdown link [nav_label](nav_url), (3) if map_data_uri exists,
        one markdown image. Do not paste raw base64. Do not print the API key.
        No phone, rating, or interactive map UI. If ok is false, say
        路线接口不可用 and do not invent exact minutes.
        """
        # AMAP_DRIVE_ROUTE_V1
        # AMAP_DRIVE_ROUTE_M1A_V1
        # AMAP_DRIVE_ROUTE_MAP_LITE_V1
        origin = (origin or "").strip()
        destination = (destination or "").strip()
        if not origin or not destination:
            return fail()
        key = self._key()
        if not key:
            return fail()
        chat_id = "anon"
        if isinstance(__metadata__, dict):
            chat_id = str(__metadata__.get("chat_id") or __metadata__.get("chatId") or "anon")
        if not allow_call(chat_id, int(self.valves.MAX_CALLS_PER_TURN)):
            return fail("本轮路线查询已达上限", capped=True)
        return lookup_drive(
            key,
            origin,
            destination,
            via=via,
            max_via=int(self.valves.MAX_VIA_POINTS),
        )
