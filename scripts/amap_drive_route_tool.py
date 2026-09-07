"""
title: China Drive Route
author: micropigeon
id: amap_drive_route
description: Amap driving route and traffic for China. Compact JSON, no map UI.
version: 1.0.0
"""

from __future__ import annotations

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
UNAVAILABLE = "路线接口不可用"
COORD_RE = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$"
)
TMC_LABELS = ("未知", "畅通", "缓行", "拥堵", "严重拥堵")
GEOCODE_URL = "https://restapi.amap.com/v3/geocode/geo"
DRIVING_URL = "https://restapi.amap.com/v5/direction/driving"

_CALLS: dict[str, tuple[float, int]] = {}
HttpFn = Callable[[str, dict[str, str]], dict[str, Any]]


def fail(message: str = UNAVAILABLE, **extra: Any) -> str:
    payload = {"ok": False, "error": message}
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


def geocode_place(key: str, place: str, http: HttpFn | None = None) -> tuple[str, tuple[float, float]] | None:
    parsed = parse_coord(place)
    if parsed:
        return place.strip(), parsed
    data = amap_get(GEOCODE_URL, {"key": key, "address": place, "output": "JSON"}, http)
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
    return name, location


def lookup_drive(
    key: str,
    origin: str,
    destination: str,
    *,
    max_via: int,
    http: HttpFn | None = None,
) -> str:
    start = geocode_place(key, origin, http)
    end = geocode_place(key, destination, http)
    if not start or not end:
        return fail()
    origin_name, origin_xy = start
    dest_name, dest_xy = end
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
        return fail()
    route = data.get("route") if isinstance(data.get("route"), dict) else {}
    paths = route.get("paths")
    if not isinstance(paths, list) or not paths or not isinstance(paths[0], dict):
        return fail()
    compact = compact_route(
        origin_name=origin_name,
        dest_name=dest_name,
        origin=origin_xy,
        dest=dest_xy,
        path=paths[0],
        max_via=max_via,
    )
    return json.dumps(compact, ensure_ascii=False, separators=(",", ":"))


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
        __metadata__: dict | None = None,
    ) -> str:
        """China driving route with live traffic. origin/destination: place name or 'lng,lat' (GCJ-02).

        Returns compact JSON: km, minutes, traffic, sparse via points (~1km).
        No phone, rating, or map UI. On failure returns 路线接口不可用.
        """
        # AMAP_DRIVE_ROUTE_V1
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
            max_via=int(self.valves.MAX_VIA_POINTS),
        )
