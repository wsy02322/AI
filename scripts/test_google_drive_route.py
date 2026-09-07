#!/usr/bin/env python3
"""Unit tests for the ST-16 Google Routes overseas drive tool (no live key)."""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from google_drive_route_tool import (
    FIELD_MASK,
    GOOGLE_DRIVE_ROUTE_M1A_V1,
    GOOGLE_DRIVE_ROUTE_MAP_LITE_V1,
    GOOGLE_DRIVE_ROUTE_V1,
    UNAVAILABLE,
    Tools,
    allow_call,
    compact_route,
    decode_polyline,
    lookup_drive,
    parse_via,
    sparse_via,
    traffic_summary,
    waypoint,
)
from stack_contract import (
    GOOGLE_DRIVE_ROUTE_M1A_MARKER,
    GOOGLE_DRIVE_ROUTE_MAP_LITE_MARKER,
    GOOGLE_DRIVE_ROUTE_MARKER,
)


class GoogleDriveRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        allow_call.__globals__["_CALLS"].clear()

    def test_marker_matches_contract(self) -> None:
        self.assertEqual(GOOGLE_DRIVE_ROUTE_V1, GOOGLE_DRIVE_ROUTE_MARKER)
        self.assertEqual(GOOGLE_DRIVE_ROUTE_M1A_V1, GOOGLE_DRIVE_ROUTE_M1A_MARKER)
        source = Path(__file__).with_name("google_drive_route_tool.py").read_text(encoding="utf-8")
        self.assertIn(GOOGLE_DRIVE_ROUTE_MARKER, source)
        self.assertEqual(GOOGLE_DRIVE_ROUTE_MAP_LITE_V1, GOOGLE_DRIVE_ROUTE_MAP_LITE_MARKER)
        self.assertIn(GOOGLE_DRIVE_ROUTE_M1A_MARKER, source)
        self.assertIn(GOOGLE_DRIVE_ROUTE_MAP_LITE_MARKER, source)
        self.assertIn("mainland China", source)
        self.assertNotIn("Place Details", source)

    def test_decode_google_polyline_example(self) -> None:
        # Google docs example: (lat, lng) = (38.5, -120.2)
        points = decode_polyline("_p~iF~ps|U")
        self.assertEqual(len(points), 1)
        lng, lat = points[0]
        self.assertAlmostEqual(lat, 38.5, places=4)
        self.assertAlmostEqual(lng, -120.2, places=4)

    def test_sparse_via_caps(self) -> None:
        points = [(-74.0 + i * 0.01, 40.7) for i in range(200)]
        via = sparse_via(points, total_m=400000, max_points=24, spacing_m=1000)
        self.assertLessEqual(len(via), 24)
        self.assertGreaterEqual(len(via), 4)

    def test_waypoint_coord_is_wgs84_latlng(self) -> None:
        point = waypoint("-73.7781,40.6413")
        latlng = point["location"]["latLng"]
        self.assertAlmostEqual(latlng["latitude"], 40.6413)
        self.assertAlmostEqual(latlng["longitude"], -73.7781)
        self.assertEqual(waypoint("JFK Airport")["address"], "JFK Airport")

    def test_compact_omits_place_details(self) -> None:
        points = decode_polyline("_p~iF~ps|U")
        route = {
            "distanceMeters": 21400,
            "duration": "1680s",
            "polyline": {"encodedPolyline": "_p~iF~ps|U"},
            "legs": [
                {
                    "startLocation": {"latLng": {"latitude": 40.6413, "longitude": -73.7781}},
                    "endLocation": {"latLng": {"latitude": 40.7580, "longitude": -73.9855}},
                    "phone": "should-not-leak",
                }
            ],
            "travelAdvisory": {
                "speedReadingIntervals": [
                    {"startPolylinePointIndex": 0, "endPolylinePointIndex": 0, "speed": "NORMAL"},
                ]
            },
        }
        compact = compact_route(
            origin_name="JFK Airport",
            dest_name="Times Square",
            route=route,
            max_via=24,
        )
        blob = json.dumps(compact, ensure_ascii=False)
        self.assertTrue(compact["ok"])
        self.assertEqual(compact["provider"], "google")
        self.assertEqual(compact["crs"], "WGS84")
        self.assertEqual(compact["km"], 21.4)
        self.assertEqual(compact["minutes"], 28)
        self.assertNotIn("phone", blob)
        self.assertNotIn("rating", blob)
        self.assertNotIn("tel", blob)
        self.assertEqual(compact["origin"]["lng"], -73.7781)
        self.assertGreaterEqual(len(points), 1)

    def test_traffic_jam_wording(self) -> None:
        points = [(-74.0, 40.7), (-73.99, 40.71), (-73.98, 40.72), (-73.97, 40.73)]
        text, share = traffic_summary(
            [
                {"startPolylinePointIndex": 0, "endPolylinePointIndex": 3, "speed": "TRAFFIC_JAM"},
            ],
            points,
        )
        self.assertIn("拥堵", text)
        self.assertGreater(share.get("拥堵", 0), 0)

    def test_lookup_uses_routes_api_and_field_mask(self) -> None:
        seen: dict[str, Any] = {}

        def http(url: str, key: str, body: dict[str, Any]) -> dict:
            seen["url"] = url
            seen["key"] = key
            seen["body"] = body
            return {
                "routes": [
                    {
                        "distanceMeters": 27800,
                        "duration": "2460s",
                        "polyline": {"encodedPolyline": "_p~iF~ps|U"},
                        "legs": [
                            {
                                "startLocation": {"latLng": {"latitude": 40.6413, "longitude": -73.7781}},
                                "endLocation": {"latLng": {"latitude": 40.7580, "longitude": -73.9855}},
                            }
                        ],
                        "travelAdvisory": {
                            "speedReadingIntervals": [
                                {"startPolylinePointIndex": 0, "endPolylinePointIndex": 0, "speed": "NORMAL"}
                            ]
                        },
                    }
                ]
            }

        raw = lookup_drive("test-key", "JFK Airport", "Times Square", max_via=24, http=http)
        data = json.loads(raw)
        self.assertTrue(data["ok"])
        self.assertEqual(data["km"], 27.8)
        self.assertEqual(data["minutes"], 41)
        self.assertEqual(len(data["legs"]), 1)
        self.assertIn("google.com/maps/dir", data["nav_url"])
        self.assertEqual(seen["url"], "https://routes.googleapis.com/directions/v2:computeRoutes")
        self.assertEqual(seen["body"]["travelMode"], "DRIVE")
        self.assertEqual(seen["body"]["routingPreference"], "TRAFFIC_AWARE")
        self.assertNotIn("intermediates", seen["body"])
        self.assertIn("TRAFFIC_ON_POLYLINE", seen["body"]["extraComputations"])
        self.assertNotIn("places", json.dumps(seen["body"]))
        self.assertIn("speedReadingIntervals", FIELD_MASK)
        self.assertIn("legs.duration", FIELD_MASK)
        self.assertNotIn("formattedAddress", FIELD_MASK)

    def test_missing_key_and_cap(self) -> None:
        tools = Tools()
        tools.valves.GOOGLE_MAPS_KEY = ""
        first = json.loads(
            tools.overseas_drive_route("JFK Airport", "Times Square", __metadata__={"chat_id": "c1"})
        )
        self.assertFalse(first["ok"])
        self.assertEqual(first["error"], UNAVAILABLE)
        tools.valves.GOOGLE_MAPS_KEY = "x"
        tools.valves.MAX_CALLS_PER_TURN = 2

        def http(_url: str, _key: str, _body: dict[str, Any]) -> dict:
            return {"error": {"status": "PERMISSION_DENIED"}}

        import google_drive_route_tool as mod

        orig = mod.routes_post
        mod.routes_post = http  # type: ignore[assignment]
        try:
            tools.overseas_drive_route("a", "b", __metadata__={"chat_id": "cap"})
            tools.overseas_drive_route("a", "b", __metadata__={"chat_id": "cap"})
            capped = json.loads(tools.overseas_drive_route("a", "b", __metadata__={"chat_id": "cap"}))
        finally:
            mod.routes_post = orig
        self.assertTrue(capped.get("capped"))
        self.assertEqual(capped["error"], "本轮路线查询已达上限")

    def test_via_sends_intermediates_and_splits_legs(self) -> None:
        seen: dict[str, Any] = {}

        def http(_url: str, _key: str, body: dict[str, Any]) -> dict:
            seen["body"] = body
            return {
                "routes": [
                    {
                        "distanceMeters": 40000,
                        "duration": "3600s",
                        "polyline": {"encodedPolyline": "_p~iF~ps|U"},
                        "legs": [
                            {
                                "distanceMeters": 22000,
                                "duration": "1800s",
                                "startLocation": {"latLng": {"latitude": 40.6413, "longitude": -73.7781}},
                                "endLocation": {"latLng": {"latitude": 40.75, "longitude": -73.99}},
                                "polyline": {"encodedPolyline": "_p~iF~ps|U"},
                            },
                            {
                                "distanceMeters": 18000,
                                "duration": "1500s",
                                "startLocation": {"latLng": {"latitude": 40.75, "longitude": -73.99}},
                                "endLocation": {"latLng": {"latitude": 40.758, "longitude": -73.9855}},
                                "polyline": {"encodedPolyline": "_p~iF~ps|U"},
                            },
                        ],
                    }
                ]
            }

        raw = lookup_drive(
            "test-key",
            "JFK Airport",
            "Times Square",
            via="Midtown Manhattan",
            max_via=24,
            http=http,
        )
        data = json.loads(raw)
        self.assertTrue(data["ok"])
        self.assertEqual(len(seen["body"]["intermediates"]), 1)
        self.assertEqual(len(data["legs"]), 2)
        self.assertEqual(data["legs"][0]["minutes"], 30)
        self.assertEqual(data["legs"][1]["minutes"], 25)
        self.assertEqual(data["totals"]["minutes"], 55)
        self.assertIn("google.com/maps/dir", data["nav_url"])
        self.assertNotIn("map_data_uri", data)
        self.assertNotIn("test-key", raw)
        self.assertEqual(parse_via("Philadelphia; Boston"), ["Philadelphia", "Boston"])

    def test_mainland_coord_and_too_many_via_fail(self) -> None:
        mixed = json.loads(lookup_drive("k", "116.40,39.90", "Times Square", max_via=8))
        self.assertFalse(mixed["ok"])
        self.assertTrue(mixed.get("mix"))
        too_many = json.loads(lookup_drive("k", "JFK", "Boston", via="a,b,c,d,e,f,g", max_via=8))
        self.assertFalse(too_many["ok"])
        self.assertTrue(too_many.get("too_many"))


if __name__ == "__main__":
    unittest.main()
