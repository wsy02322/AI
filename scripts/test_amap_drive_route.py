#!/usr/bin/env python3
"""Unit tests for the ST-16 Amap drive-route tool (no live key required)."""

from __future__ import annotations

import json
import os
import sys
import unittest
import urllib.parse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from amap_drive_route_tool import (
    AMAP_DRIVE_ROUTE_M1A_V1,
    AMAP_DRIVE_ROUTE_MAP_LITE_V1,
    AMAP_DRIVE_ROUTE_MAP_ROAD_V1,
    AMAP_DRIVE_ROUTE_NAV_LEGS_V1,
    AMAP_DRIVE_ROUTE_NAV_WEB_ONLY_V1,
    AMAP_DRIVE_ROUTE_NAV_PAGE_V1,
    AMAP_DRIVE_ROUTE_V1,
    UNAVAILABLE,
    Tools,
    allow_call,
    amap_nav_app_android,
    amap_nav_app_ios,
    amap_nav_page_url,
    amap_nav_url,
    decode_nav_page_payload,
    encode_nav_page_payload,
    amap_nav_web_url,
    compact_route,
    lookup_drive,
    parse_polyline,
    parse_via,
    sparse_via,
    static_draw_points,
    stop_region,
    traffic_summary,
)
from stack_contract import (
    AMAP_DRIVE_ROUTE_M1A_MARKER,
    AMAP_DRIVE_ROUTE_MAP_LITE_MARKER,
    AMAP_DRIVE_ROUTE_MAP_ROAD_MARKER,
    AMAP_DRIVE_ROUTE_NAV_LEGS_MARKER,
    AMAP_DRIVE_ROUTE_NAV_WEB_ONLY_MARKER,
    AMAP_DRIVE_ROUTE_NAV_PAGE_MARKER,
    AMAP_NAV_PAGE_MARKER,
    AMAP_DRIVE_ROUTE_MARKER,
)

MINI_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


class AmapDriveRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        allow_call.__globals__["_CALLS"].clear()

    def test_marker_matches_contract(self) -> None:
        self.assertEqual(AMAP_DRIVE_ROUTE_V1, AMAP_DRIVE_ROUTE_MARKER)
        self.assertEqual(AMAP_DRIVE_ROUTE_M1A_V1, AMAP_DRIVE_ROUTE_M1A_MARKER)
        source = Path(__file__).with_name("amap_drive_route_tool.py").read_text(encoding="utf-8")
        self.assertEqual(AMAP_DRIVE_ROUTE_MAP_LITE_V1, AMAP_DRIVE_ROUTE_MAP_LITE_MARKER)
        self.assertEqual(AMAP_DRIVE_ROUTE_MAP_ROAD_V1, AMAP_DRIVE_ROUTE_MAP_ROAD_MARKER)
        self.assertEqual(AMAP_DRIVE_ROUTE_NAV_LEGS_V1, AMAP_DRIVE_ROUTE_NAV_LEGS_MARKER)
        self.assertEqual(AMAP_DRIVE_ROUTE_NAV_WEB_ONLY_V1, AMAP_DRIVE_ROUTE_NAV_WEB_ONLY_MARKER)
        self.assertEqual(AMAP_DRIVE_ROUTE_NAV_PAGE_V1, AMAP_DRIVE_ROUTE_NAV_PAGE_MARKER)
        self.assertIn(AMAP_DRIVE_ROUTE_MARKER, source)
        self.assertIn(AMAP_DRIVE_ROUTE_M1A_MARKER, source)
        self.assertIn(AMAP_DRIVE_ROUTE_MAP_LITE_MARKER, source)
        self.assertIn(AMAP_DRIVE_ROUTE_MAP_ROAD_MARKER, source)
        self.assertIn(AMAP_DRIVE_ROUTE_NAV_LEGS_MARKER, source)
        self.assertIn(AMAP_DRIVE_ROUTE_NAV_WEB_ONLY_MARKER, source)
        self.assertIn(AMAP_DRIVE_ROUTE_NAV_PAGE_MARKER, source)
        page = Path(__file__).resolve().parents[1].joinpath("nav", "index.html").read_text(encoding="utf-8")
        self.assertIn(AMAP_NAV_PAGE_MARKER, page)
        self.assertNotIn('payload["nav_app_android"] =', source)

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
        self.assertIn("uri.amap.com/navigation", data["nav_url"])
        self.assertNotIn("via=", data["nav_url"])
        self.assertIn("uri.amap.com/navigation", data["legs"][0]["nav_url"])
        self.assertNotIn("nav_app_android", data)
        self.assertNotIn("nav_app_ios", data)
        self.assertNotIn("nav_app_label", data)
        self.assertNotIn("nav_page_url", data)
        self.assertNotIn("amapuri://", raw)
        self.assertNotIn("iosamap://", raw)
        self.assertNotIn("map_data_uri", data)
        self.assertNotIn("test-key", raw)
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
        static_paths: list[str] = []

        def http(url: str, params: dict[str, str]) -> dict:
            calls.append(url)
            if "staticmap" in url:
                static_paths.append(str(params.get("paths") or ""))
                return {"_bytes": MINI_PNG}
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
                            "polyline": f"{params['origin']};103.83,36.06;{params['destination']}",
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
        self.assertEqual(sum(1 for url in calls if "staticmap" in url), 1)
        self.assertNotIn("nav_url", data)
        self.assertEqual(len(data["legs"]), 3)
        for leg in data["legs"]:
            self.assertIn("uri.amap.com/navigation", leg["nav_url"])
            self.assertNotIn("via=", leg["nav_url"])
        self.assertNotIn("nav_app_android", data)
        self.assertNotIn("nav_app_ios", data)
        self.assertNotIn("nav_app_label", data)
        self.assertIn("逐站添加", data["nav_hint"])
        self.assertNotIn("nav_page_url", data)
        self.assertNotIn("amapuri://", raw)
        parsed = urllib.parse.urlparse(data["legs"][0]["nav_url"])
        self.assertEqual(parsed.netloc, "uri.amap.com")
        self.assertTrue(data["map_data_uri"].startswith("data:image/png;base64,"))
        self.assertEqual(len(static_paths), 1)
        self.assertIn("103.83,36.06", static_paths[0])
        self.assertNotIn("_path_points", data)
        self.assertNotIn("test-key", raw)
        self.assertNotIn("key=", raw)

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

    def test_next_city_geocode_is_not_biased(self) -> None:
        seen: list[tuple[str, str]] = []

        def http(url: str, params: dict[str, str]) -> dict:
            if "geocode" in url:
                seen.append((params["address"], params.get("city") or ""))
                locs = {"西安": "108.94,34.26", "西宁": "101.78,36.62"}
                place = params["address"]
                city = "西安市" if place == "西安" else "西宁市"
                return {
                    "status": "1",
                    "geocodes": [
                        {"formatted_address": f"{place}市", "location": locs[place], "city": city}
                    ],
                }
            return {
                "status": "1",
                "route": {
                    "paths": [
                        {
                            "distance": "700000",
                            "cost": {"duration": "28800"},
                            "polyline": f"{params['origin']};{params['destination']}",
                            "tmcs": [{"tmc_status": "畅通", "tmc_distance": "700000"}],
                            "steps": [{"road_name": "G6"}],
                        }
                    ]
                },
            }

        raw = lookup_drive("k", "西安", "西宁", max_via=8, http=http)
        data = json.loads(raw)
        self.assertTrue(data["ok"])
        self.assertGreater(data["km"], 400)
        self.assertEqual(seen, [("西安", ""), ("西宁", "")])

    def test_web_nav_is_one_pair_without_app_links(self) -> None:
        stops = [
            ("太原", (112.55, 37.87)),
            ("临县", (110.99, 37.95)),
            ("米脂", (110.18, 37.76)),
            ("盐池", (107.41, 37.78)),
            ("临夏", (103.24, 35.60)),
            ("循化", (102.49, 35.85)),
            ("同仁", (102.02, 35.52)),
        ]
        web = amap_nav_web_url(stops[0], stops[1])
        self.assertNotIn("via=", web)
        self.assertIn("%E5%A4%AA%E5%8E%9F", web)
        self.assertIn("%E4%B8%B4%E5%8E%BF", web)
        self.assertNotIn("%E7%B1%B3%E8%84%82", web)
        full = amap_nav_url(stops)
        self.assertIn("uri.amap.com/navigation", full)
        self.assertNotIn("via=", full)
        self.assertNotIn("米脂", urllib.parse.unquote(full))
        encoded = encode_nav_page_payload(stops)
        decoded = decode_nav_page_payload(encoded)
        self.assertEqual([name for name, _xy in decoded or []], [name for name, _xy in stops])
        page = amap_nav_page_url("https://micropigeon.com/nav/", stops)
        self.assertTrue(page.startswith("https://micropigeon.com/nav/#p="))
        self.assertNotIn("amapuri://", page)
        android = amap_nav_app_android(stops)
        ios = amap_nav_app_ios(stops)
        self.assertIn("vian=5", android)
        self.assertIn("vianames=", android)
        self.assertIn("临县", urllib.parse.unquote(android))
        self.assertIn("vian=5", ios)
        self.assertIn("sourceApplication=micropigeon", ios)

    def test_static_draw_points_caps_road_sample(self) -> None:
        resolved = [("西安", (108.94, 34.26)), ("张掖", (100.45, 38.93))]
        long_path = [(108.94 - i * 0.05, 34.26 + i * 0.03) for i in range(400)]
        drawn = static_draw_points(resolved, long_path)
        self.assertGreaterEqual(len(drawn), 4)
        self.assertLessEqual(len(drawn), 100)
        self.assertNotEqual(drawn, [(108.94, 34.26), (100.45, 38.93)])

    def test_static_map_is_data_uri_without_key(self) -> None:
        seen_paths: list[str] = []

        def http(url: str, params: dict[str, str]) -> dict:
            if "staticmap" in url:
                self.assertEqual(params.get("key"), "secret-key")
                seen_paths.append(str(params.get("paths") or ""))
                return {"_bytes": MINI_PNG}
            if "geocode" in url:
                locs = {"西安": "108.94,34.26", "西宁": "101.78,36.62", "张掖": "100.45,38.93"}
                place = params["address"]
                return {
                    "status": "1",
                    "geocodes": [{"formatted_address": place, "location": locs[place], "city": place + "市"}],
                }
            return {
                "status": "1",
                "route": {
                    "paths": [
                        {
                            "distance": "100000",
                            "cost": {"duration": "7200"},
                            "polyline": f"{params['origin']};103.83,36.06;{params['destination']}",
                            "tmcs": [{"tmc_status": "畅通", "tmc_distance": "100000"}],
                            "steps": [{"road_name": "G30"}],
                        }
                    ]
                },
            }

        raw = lookup_drive("secret-key", "西安", "张掖", via="西宁", max_via=8, http=http)
        data = json.loads(raw)
        self.assertTrue(data["ok"])
        self.assertTrue(data["map_data_uri"].startswith("data:image/png;base64,"))
        self.assertTrue(any("103.83,36.06" in item for item in seen_paths))
        self.assertNotIn("secret-key", raw)
        self.assertNotIn("key=", raw)
        url = amap_nav_url([("西安", (108.94, 34.26)), ("西宁", (101.78, 36.62)), ("张掖", (100.45, 38.93))])
        self.assertIn("uri.amap.com/navigation", url)
        self.assertNotIn("via=", url)

    def test_static_map_falls_back_to_straight_path(self) -> None:
        paths: list[str] = []

        def http(url: str, params: dict[str, str]) -> dict:
            if "staticmap" in url:
                paths.append(str(params.get("paths") or ""))
                if len(paths) == 1:
                    return {}
                return {"_bytes": MINI_PNG}
            if "geocode" in url:
                locs = {"西安": "108.94,34.26", "西宁": "101.78,36.62", "张掖": "100.45,38.93"}
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
                            "polyline": f"{params['origin']};103.83,36.06;{params['destination']}",
                            "tmcs": [{"tmc_status": "畅通", "tmc_distance": "100000"}],
                            "steps": [{"road_name": "G30"}],
                        }
                    ]
                },
            }

        data = json.loads(lookup_drive("k", "西安", "张掖", via="西宁", max_via=8, http=http))
        self.assertTrue(data["ok"])
        self.assertIn("map_data_uri", data)
        self.assertEqual(len(paths), 2)
        self.assertIn("103.83,36.06", paths[0])
        self.assertNotIn("103.83,36.06", paths[1])

    def test_static_map_failure_keeps_nav(self) -> None:
        def http(url: str, params: dict[str, str]) -> dict:
            if "staticmap" in url:
                return {}
            if "geocode" in url:
                locs = {"西安": "108.94,34.26", "西宁": "101.78,36.62", "张掖": "100.45,38.93"}
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

        data = json.loads(
            lookup_drive(
                "k",
                "西安",
                "张掖",
                via="西宁",
                max_via=8,
                http=http,
                page_base="https://micropigeon.com/nav/",
            )
        )
        self.assertTrue(data["ok"])
        self.assertNotIn("nav_url", data)
        self.assertIn("uri.amap.com/navigation", data["legs"][0]["nav_url"])
        self.assertTrue(data["nav_page_url"].startswith("https://micropigeon.com/nav/#p="))
        self.assertIn("nav_page_url", data["nav_hint"])
        self.assertNotIn("nav_app_android", data)
        self.assertNotIn("nav_app_ios", data)
        self.assertNotIn("amapuri://", json.dumps(data))
        self.assertNotIn("map_data_uri", data)


if __name__ == "__main__":
    unittest.main()
