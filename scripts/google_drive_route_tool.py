"""
title: Overseas Drive Route
author: micropigeon
id: google_drive_route
description: Google Routes driving time and traffic outside mainland China. Compact JSON, optional via stops, no map UI.
version: 1.1.0
"""

from __future__ import annotations

import json
import math
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from pydantic import BaseModel, Field

GOOGLE_DRIVE_ROUTE_V1 = "GOOGLE_DRIVE_ROUTE_V1"
GOOGLE_DRIVE_ROUTE_M1A_V1 = "GOOGLE_DRIVE_ROUTE_M1A_V1"
UNAVAILABLE = "路线接口不可用"
NOTE = "分钟数是路网估算；实时路况只代表现在"
MAX_STOPS = 8
MAX_VIA_STOPS = 6
LEG_VIA_CAP = 8
MIX_HINT = "海外与中国大陆站点请拆开，大陆用 China Drive Route"
FIELD_MASK = (
    "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline,"
    "routes.legs.duration,routes.legs.distanceMeters,"
    "routes.legs.startLocation,routes.legs.endLocation,"
    "routes.legs.polyline.encodedPolyline,"
    "routes.legs.travelAdvisory.speedReadingIntervals,"
    "routes.travelAdvisory.speedReadingIntervals"
)
COORD_RE = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$"
)
SPEED_LABELS = {
    "NORMAL": "畅通",
    "SLOW": "缓行",
    "TRAFFIC_JAM": "拥堵",
    "SPEED_UNSPECIFIED": "未知",
}
ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

_CALLS: dict[str, tuple[float, int]] = {}
HttpFn = Callable[[str, str, dict[str, Any]], dict[str, Any]]


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


def attach_itinerary(compact: dict[str, Any], legs: list[dict[str, Any]], stops: list[str]) -> dict[str, Any]:
    compact["traffic_as_of"] = "now"
    compact["note"] = NOTE
    compact["stops"] = stops
    compact["legs"] = legs
    compact["totals"] = {"km": compact["km"], "minutes": compact["minutes"]}
    return compact


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


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    radius = 6371000.0
    lng1, lat1 = math.radians(a[0]), math.radians(a[1])
    lng2, lat2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(min(1.0, h)))


def decode_polyline(encoded: str) -> list[tuple[float, float]]:
    if not isinstance(encoded, str) or not encoded:
        return []
    points: list[tuple[float, float]] = []
    index = 0
    lat = 0
    lng = 0
    length = len(encoded)
    while index < length:
        result = 1
        shift = 0
        while True:
            if index >= length:
                return points
            byte = ord(encoded[index]) - 63 - 1
            index += 1
            result += byte << shift
            shift += 5
            if byte < 0x1F:
                break
        lat += ~(result >> 1) if result & 1 else (result >> 1)
        result = 1
        shift = 0
        while True:
            if index >= length:
                return points
            byte = ord(encoded[index]) - 63 - 1
            index += 1
            result += byte << shift
            shift += 5
            if byte < 0x1F:
                break
        lng += ~(result >> 1) if result & 1 else (result >> 1)
        points.append((lng / 1e5, lat / 1e5))
    return points


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


def interval_meters(
    points: list[tuple[float, float]],
    start: int,
    end: int,
) -> float:
    if not points:
        return 0.0
    lo = max(0, min(int(start), len(points) - 1))
    hi = max(lo, min(int(end), len(points) - 1))
    return sum(haversine_m(points[i], points[i + 1]) for i in range(lo, hi))


def traffic_summary(
    intervals: list[dict[str, Any]],
    points: list[tuple[float, float]],
) -> tuple[str, dict[str, float]]:
    dist = {"未知": 0.0, "畅通": 0.0, "缓行": 0.0, "拥堵": 0.0}
    for item in intervals:
        if not isinstance(item, dict):
            continue
        speed = str(item.get("speed") or "SPEED_UNSPECIFIED")
        label = SPEED_LABELS.get(speed, "未知")
        try:
            start = int(item.get("startPolylinePointIndex") or 0)
            end = int(item.get("endPolylinePointIndex") or start)
        except (TypeError, ValueError):
            continue
        dist[label] += max(0.0, interval_meters(points, start, end))
    total = sum(dist.values())
    share = {
        label: round(meters / total, 3)
        for label, meters in dist.items()
        if meters > 0 and total > 0
    }
    jam = share.get("拥堵", 0)
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


def parse_duration_seconds(raw: Any) -> float:
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw or "").strip().rstrip("s")
    try:
        return float(text)
    except ValueError:
        return 0.0


def waypoint(place: str) -> dict[str, Any]:
    parsed = parse_coord(place)
    if parsed:
        lng, lat = parsed
        return {"location": {"latLng": {"latitude": lat, "longitude": lng}}}
    return {"address": place}


def latlng_pair(node: Any) -> tuple[float, float] | None:
    if not isinstance(node, dict):
        return None
    loc = node.get("latLng") if isinstance(node.get("latLng"), dict) else node
    try:
        lat = float(loc.get("latitude"))
        lng = float(loc.get("longitude"))
    except (TypeError, ValueError, AttributeError):
        return None
    if abs(lng) > 180 or abs(lat) > 90:
        return None
    return lng, lat


def compact_route(
    *,
    origin_name: str,
    dest_name: str,
    route: dict[str, Any],
    max_via: int,
) -> dict[str, Any]:
    try:
        meters = float(route.get("distanceMeters") or 0)
    except (TypeError, ValueError):
        meters = 0.0
    seconds = parse_duration_seconds(route.get("duration"))
    encoded = ""
    poly = route.get("polyline")
    if isinstance(poly, dict):
        encoded = str(poly.get("encodedPolyline") or "")
    points = decode_polyline(encoded)
    legs = route.get("legs") if isinstance(route.get("legs"), list) else []
    origin_xy = points[0] if points else None
    dest_xy = points[-1] if points else None
    if legs and isinstance(legs[0], dict):
        origin_xy = latlng_pair(legs[0].get("startLocation")) or origin_xy
        dest_xy = latlng_pair(legs[0].get("endLocation")) or dest_xy
    advisory = route.get("travelAdvisory") if isinstance(route.get("travelAdvisory"), dict) else {}
    intervals = advisory.get("speedReadingIntervals")
    if not isinstance(intervals, list):
        intervals = []
    traffic, share = traffic_summary(intervals, points)
    origin_xy = origin_xy or (0.0, 0.0)
    dest_xy = dest_xy or (0.0, 0.0)
    return {
        "ok": True,
        "provider": "google",
        "crs": "WGS84",
        "origin": {
            "name": origin_name,
            "lng": round(origin_xy[0], 5),
            "lat": round(origin_xy[1], 5),
        },
        "destination": {
            "name": dest_name,
            "lng": round(dest_xy[0], 5),
            "lat": round(dest_xy[1], 5),
        },
        "km": round(meters / 1000.0, 1),
        "minutes": int(round(seconds / 60.0)) if seconds else 0,
        "traffic": traffic,
        "traffic_share": share,
        "via": sparse_via(points, total_m=meters, max_points=max_via),
    }


def routes_post(key: str, body: dict[str, Any], http: HttpFn | None = None) -> dict[str, Any]:
    if http is not None:
        return http(ROUTES_URL, key, body)
    payload = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        ROUTES_URL,
        data=payload,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "X-Goog-Api-Key": key,
            "X-Goog-FieldMask": FIELD_MASK,
            "User-Agent": "micropigeon-google-drive/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read().decode("utf-8", errors="replace")
        except Exception:
            return {}
    except Exception:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def compact_leg(
    *,
    from_name: str,
    to_name: str,
    meters: float,
    seconds: float,
    points: list[tuple[float, float]],
    traffic: str,
    max_via: int,
) -> dict[str, Any]:
    cap = max(4, min(int(max_via), LEG_VIA_CAP))
    return {
        "from": from_name,
        "to": to_name,
        "km": round(meters / 1000.0, 1),
        "minutes": int(round(seconds / 60.0)) if seconds else 0,
        "traffic": traffic,
        "roads": [],
        "via": sparse_via(points, total_m=meters, max_points=cap),
    }


def regions_from_points(points: list[tuple[float, float]]) -> set[str]:
    return {stop_region(lng, lat) for lng, lat in points if abs(lng) > 0 or abs(lat) > 0}


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
    for label in labels:
        parsed = parse_coord(label)
        if parsed and stop_region(*parsed) == "cn":
            return fail(UNAVAILABLE, mix=True, hint=MIX_HINT)
    body: dict[str, Any] = {
        "origin": waypoint(origin),
        "destination": waypoint(destination),
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
        "polylineQuality": "OVERVIEW",
        "computeAlternativeRoutes": False,
        "languageCode": "en",
        "units": "METRIC",
        "extraComputations": ["TRAFFIC_ON_POLYLINE"],
    }
    if via_stops:
        body["intermediates"] = [waypoint(stop) for stop in via_stops]
    data = routes_post(key, body, http)
    if data.get("error"):
        return fail()
    routes = data.get("routes")
    if not isinstance(routes, list) or not routes or not isinstance(routes[0], dict):
        return fail()
    route = routes[0]
    compact = compact_route(
        origin_name=origin,
        dest_name=destination,
        route=route,
        max_via=max_via if not via_stops else min(int(max_via), LEG_VIA_CAP),
    )
    if compact["km"] <= 0 and compact["minutes"] <= 0:
        return fail()
    route_legs = route.get("legs") if isinstance(route.get("legs"), list) else []
    names = [origin, *via_stops, destination]
    check_points = [
        (compact["origin"]["lng"], compact["origin"]["lat"]),
        (compact["destination"]["lng"], compact["destination"]["lat"]),
    ]
    for item in route_legs:
        if isinstance(item, dict):
            start = latlng_pair(item.get("startLocation"))
            end = latlng_pair(item.get("endLocation"))
            if start:
                check_points.append(start)
            if end:
                check_points.append(end)
    regions = regions_from_points(check_points)
    if "cn" in regions:
        return fail(UNAVAILABLE, mix=True, hint=MIX_HINT)
    legs_out: list[dict[str, Any]] = []
    if via_stops and len(route_legs) == len(names) - 1:
        overall_traffic = compact["traffic"]
        for index, item in enumerate(route_legs):
            if not isinstance(item, dict):
                return fail()
            try:
                meters = float(item.get("distanceMeters") or 0)
            except (TypeError, ValueError):
                meters = 0.0
            seconds = parse_duration_seconds(item.get("duration"))
            encoded = ""
            poly = item.get("polyline")
            if isinstance(poly, dict):
                encoded = str(poly.get("encodedPolyline") or "")
            points = decode_polyline(encoded)
            advisory = item.get("travelAdvisory") if isinstance(item.get("travelAdvisory"), dict) else {}
            intervals = advisory.get("speedReadingIntervals")
            if isinstance(intervals, list) and intervals:
                traffic, _share = traffic_summary(intervals, points)
            else:
                traffic = overall_traffic
            legs_out.append(
                compact_leg(
                    from_name=names[index],
                    to_name=names[index + 1],
                    meters=meters,
                    seconds=seconds,
                    points=points,
                    traffic=traffic,
                    max_via=min(int(max_via), LEG_VIA_CAP),
                )
            )
        compact["km"] = round(sum(leg["km"] for leg in legs_out), 1)
        compact["minutes"] = int(sum(leg["minutes"] for leg in legs_out))
        compact["traffic"] = "分段见 legs"
        compact["via"] = []
    else:
        legs_out = [
            {
                "from": compact["origin"]["name"],
                "to": compact["destination"]["name"],
                "km": compact["km"],
                "minutes": compact["minutes"],
                "traffic": compact["traffic"],
                "roads": [],
                "via": compact.get("via") or [],
            }
        ]
    attach_itinerary(compact, legs_out, names)
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
        GOOGLE_MAPS_KEY: str = Field(default="", description="Google Maps Routes API key. Not committed.")
        MAX_CALLS_PER_TURN: int = Field(default=3, ge=1, le=5)
        MAX_VIA_POINTS: int = Field(default=24, ge=4, le=40)

    def __init__(self) -> None:
        self.valves = self.Valves()

    def _key(self) -> str:
        valve = (self.valves.GOOGLE_MAPS_KEY or "").strip()
        if valve:
            return valve
        return (
            os.environ.get("GOOGLE_MAPS_KEY")
            or os.environ.get("GOOGLE_ROUTES_KEY")
            or os.environ.get("GOOGLE_MAPS_API_KEY")
            or ""
        ).strip()

    def overseas_drive_route(
        self,
        origin: str,
        destination: str,
        via: str = "",
        __metadata__: dict | None = None,
    ) -> str:
        """Must-use tool for driving time, traffic, or a multi-stop road trip OUTSIDE mainland China.

        Use this for the US, Europe, Hong Kong, Macau, Taiwan. Call once. Put
        middle cities in via (comma or semicolon, max 6). Do not use for
        mainland China — that is China Drive Route. origin/destination: place
        name or 'lng,lat' (WGS84). Returns compact JSON: km, minutes, traffic,
        legs[], totals. No phone, rating, or map UI. If ok is false, say
        路线接口不可用 and do not invent exact minutes.
        """
        # GOOGLE_DRIVE_ROUTE_V1
        # GOOGLE_DRIVE_ROUTE_M1A_V1
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
