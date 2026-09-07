#!/usr/bin/env python3
"""Unit tests for the ST-16 Amap drive-route tool (no live key required)."""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from amap_drive_route_tool import (
    AMAP_DRIVE_ROUTE_M1A_V1,
    AMAP_DRIVE_ROUTE_V1,
    UNAVAILABLE,
    Tools,
    allow_call,
    compact_route,
    lookup_drive,
    parse_polyline,
    parse_via,
    sparse_via,
    stop_region,
    traffic_summary,
)
from stack_contract import AMAP_DRIVE_ROUTE_M1A_MARKER, AMAP_DRIVE_ROUTE_MARKER


class AmapDriveRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        allow_call.__globals__["_CALLS"].clear()

    def test_marker_matches_contract(self) -> None:
        self.assertEqual(AMAP_DRIVE_ROUTE_V1, AMAP_DRIVE_ROUTE_MARKER)
        self.assertEqual(AMAP_DRIVE_ROUTE_M1A_V1, AMAP_DRIVE_ROUTE_M1A_MARKER)
        source = Path(__file__).with_name("amap_drive_route_tool.py").read_text(encoding="utf-8")
        self.assertIn(AMAP_DRIVE_ROUTE_MARKER, source)
        self.assertIn(AMAP_DRIVE_ROUTE_M1A_MARKER, source)

    def test_sparse_via_about_one_km(self) -> None:
        points = [(116.0 + i * 0.01, 39.9) for i in range(20)]
        via = sparse_via(points, total_m=20000, max_points=24, spacing_m=1000)
        self.assertGreaterEqual(len(via), 8)
        self.assertLessEqual(len(via), 24)
        self.assertEqual(via[0], [round(points[0][0], 5), round(points[0][1], 5)])
        self.assertEqual(via[-1][1], round(points[-1][1], 5))

    def test_long_route_caps_via_points(self) -> None:
        points = [(116.0 + i * 0.02, 39.9) for i in range(200)]
        via = sparse_via(points, total_m=400000, max_points=24, spacing_m=1000)
        self.assertLessEqual(len(via), 24)
        self.assertGreaterEqual(len(via), 4)

    def test_polyline_semicolon_and_flat(self) -> None:
        self.assertEqual(parse_polyline("116.4,39.9;116.5,39.91"), [(116.4, 39.9), (116.5, 39.91)])
        self.assertEqual(parse_polyline("116.4,39.9,116.5,39.91"), [(116.4, 39.9), (116.5, 39.91)])

    def test_traffic_summary_and_compact_omits_place_details(self) -> None:
        tmcs = [
            {"tmc_status": "畅通", "tmc_distance": "8000"},
            {"tmc_status": "缓行", "tmc_distance": "1500"},
            {"tmc_status": "拥堵", "tmc_distance": "500"},
        ]
        text, share = traffic_summary(tmcs)
        self.assertIn("畅通", text)
        self.assertGreater(share["畅通"], share["拥堵"])
        path = {
            "distance": "12000",
            "cost": {"duration": "1500"},
            "polyline": "116.37,39.86;116.40,39.90;116.50,40.00;116.60,40.08",
            "tmcs": tmcs,
            "steps": [{"road_name": "机场高速", "tel": "should-not-leak"}],
        }
        compact = compact_route(
            origin_name="北京南站",
            dest_name="首都机场",
            origin=(116.37, 39.86),
            dest=(116.60, 40.08),
            path=path,
            max_via=24,
        )
        blob = json.dumps(compact, ensure_ascii=False)
        self.assertTrue(compact["ok"])
        self.assertEqual(compact["km"], 12.0)
        self.assertEqual(compact["minutes"], 25)
        self.assertEqual(compact["crs"], "GCJ-02")
        self.assertNotIn("tel", blob)
        self.assertNotIn("phone", blob)
        self.assertNotIn("rating", blob)
        self.assertIn("机场高速", compact["roads"])

    def test_lookup_uses_geocode_and_driving(self) -> None:
        calls: list[str] = []

        def http(url: str, params: dict[str, str]) -> dict:
            calls.append(url)
            if "geocode" in url:
                place = params["address"]
                loc = "116.378,39.865" if "南" in place else "116.603,40.080"
                return {
                    "status": "1",
                    "geocodes": [{"formatted_address": place, "location": loc}],
                }
            self.assertEqual(params["show_fields"], "cost,tmcs,polyline")
            self.assertNotIn("navi", params["show_fields"])
            return {
                "status": "1",
                "route": {
                    "paths": [
                        {
                            "distance": "28500",
                            "cost": {"duration": "2460"},
                            "polyline": "116.378,39.865;116.50,39.95;116.603,40.080",
                            "tmcs": [{"tmc_status": "畅通", "tmc_distance": "28500"}],
                            "steps": [{"road_name": "二环"}],
                        }
                    ]
                },
            }

        raw = lookup_drive("test-key", "北京南站", "首都机场", max_via=24, http=http)
        data = json.loads(raw)
        self.assertTrue(data["ok"])
        self.assertEqual(data["km"], 28.5)
        self.assertEqual(data["minutes"], 41)
        self.assertEqual(len(data["legs"]), 1)
        self.assertEqual(data["totals"]["km"], 28.5)
        self.assertEqual(len(calls), 3)

    def test_missing_key_and_cap(self) -> None:
        tools = Tools()
        tools.valves.AMAP_KEY = ""
        first = json.loads(tools.drive_route("北京南站", "首都机场", __metadata__={"chat_id": "c1"}))
        self.assertFalse(first["ok"])
        self.assertEqual(first["error"], UNAVAILABLE)
        tools.valves.AMAP_KEY = "x"
        tools.valves.MAX_CALLS_PER_TURN = 2

        def http(url: str, params: dict[str, str], *_args: object, **_kwargs: object) -> dict:
            if "geocode" in url:
                return {"status": "1", "geocodes": [{"formatted_address": "x", "location": "116.4,39.9"}]}
            return {"status": "0"}

        import amap_drive_route_tool as mod

        orig = mod.amap_get
        mod.amap_get = http  # type: ignore[assignment]
        try:
            tools.drive_route("a", "b", __metadata__={"chat_id": "cap"})
            tools.drive_route("a", "b", __metadata__={"chat_id": "cap"})
            capped = json.loads(tools.drive_route("a", "b", __metadata__={"chat_id": "cap"}))
        finally:
            mod.amap_get = orig
        self.assertTrue(capped.get("capped"))
        self.assertEqual(capped["error"], "本轮路线查询已达上限")

    def test_inject_hint_maps_amap_errors(self) -> None:
        from inject_amap_key import _hint

        self.assertIn("Web服务", _hint({"geocode_info": "USERKEY_PLAT_NOMATCH", "driving_info": ""}))
        self.assertIn("78.47.152.85", _hint({"geocode_info": "INVALID_USER_IP", "driving_info": "10005"}))
        self.assertIn("数字签名", _hint({"geocode_info": "", "driving_info": "INVALID_USER_SIGNATURE"}))
        self.assertEqual(_hint({"ok": True, "geocode_info": "OK", "driving_info": "OK"}), "")

    def test_parse_via_and_regions(self) -> None:
        self.assertEqual(parse_via("西宁;青海湖"), ["西宁", "青海湖"])
        self.assertEqual(parse_via("西宁, 青海湖"), ["西宁", "青海湖"])
        self.assertEqual(parse_via('["西宁","青海湖"]'), ["西宁", "青海湖"])
        self.assertEqual(stop_region(116.4, 39.9), "cn")
        self.assertEqual(stop_region(139.69, 35.68), "overseas")
        self.assertEqual(stop_region(114.17, 22.32), "overseas")

    def test_via_fans_out_one_tool_call(self) -> None:
        calls: list[str] = []

        def http(url: str, params: dict[str, str]) -> dict:
            calls.append(url)
            if "geocode" in url:
                locs = {
                    "西安": "108.94,34.26",
                    "西宁": "101.78,36.62",
                    "青海湖": "100.14,36.87",
                    "张掖": "100.45,38.93",
                }
                place = params["address"]
                return {
                    "status": "1",
                    "geocodes": [{"formatted_address": place, "location": locs[place]}],
                }
            return {
                "status": "1",
                "route": {
                    "paths": [
                        {
                            "distance": "100000",
                            "cost": {"duration": "7200"},
                            "polyline": f"{params['origin']};{params['destination']}",
                            "tmcs": [{"tmc_status": "畅通", "tmc_distance": "100000"}],
                            "steps": [{"road_name": "G30"}],
                        }
                    ]
                },
            }

        raw = lookup_drive(
            "test-key",
            "西安",
            "张掖",
            via="西宁,青海湖",
            max_via=24,
            http=http,
        )
        data = json.loads(raw)
        self.assertTrue(data["ok"])
        self.assertEqual(len(data["legs"]), 3)
        self.assertEqual(data["stops"], ["西安", "西宁", "青海湖", "张掖"])
        self.assertEqual(data["totals"]["km"], 300.0)
        self.assertEqual(data["totals"]["minutes"], 360)
        self.assertEqual(sum(1 for url in calls if "geocode" in url), 4)
        self.assertEqual(sum(1 for url in calls if "driving" in url), 3)

    def test_mix_and_too_many_via_fail(self) -> None:
        def tokyo_http(url: str, params: dict[str, str]) -> dict:
            if "geocode" in url:
                place = params["address"]
                loc = "139.69,35.68" if "东京" in place else "108.94,34.26"
                return {"status": "1", "geocodes": [{"formatted_address": place, "location": loc}]}
            return {"status": "0"}

        mixed = json.loads(lookup_drive("k", "西安", "东京", max_via=8, http=tokyo_http))
        self.assertFalse(mixed["ok"])
        self.assertTrue(mixed.get("mix"))
        too_many = json.loads(
            lookup_drive(
                "k",
                "西安",
                "敦煌",
                via="a,b,c,d,e,f,g",
                max_via=8,
                http=lambda *_args, **_kwargs: {},
            )
        )
        self.assertFalse(too_many["ok"])
        self.assertTrue(too_many.get("too_many"))

    def test_poi_fallback_when_geocode_jumps(self) -> None:
        seen: list[str] = []

        def http(url: str, params: dict[str, str]) -> dict:
            seen.append(url)
            if "geocode" in url:
                place = params["address"]
                if place == "西宁":
                    return {
                        "status": "1",
                        "geocodes": [
                            {"formatted_address": "青海省西宁市", "location": "101.78,36.62", "city": "西宁市"}
                        ],
                    }
                return {
                    "status": "1",
                    "geocodes": [
                        {"formatted_address": "新疆某处青海湖", "location": "87.62,43.83", "city": "乌鲁木齐市"}
                    ],
                }
            if "place/text" in url:
                self.assertEqual(params.get("extensions"), "base")
                return {
                    "status": "1",
                    "pois": [{"name": "青海湖", "location": "100.14,36.87", "cityname": "海南州"}],
                }
            return {
                "status": "1",
                "route": {
                    "paths": [
                        {
                            "distance": "150000",
                            "cost": {"duration": "9000"},
                            "polyline": f"{params['origin']};{params['destination']}",
                            "tmcs": [{"tmc_status": "畅通", "tmc_distance": "150000"}],
                            "steps": [{"road_name": "G109"}],
                        }
                    ]
                },
            }

        raw = lookup_drive("k", "西宁", "青海湖", max_via=8, http=http)
        data = json.loads(raw)
        self.assertTrue(data["ok"])
        self.assertLess(data["km"], 400)
        self.assertTrue(any("place/text" in url for url in seen))
        self.assertNotIn("rating", json.dumps(data))


if __name__ == "__main__":
    unittest.main()
