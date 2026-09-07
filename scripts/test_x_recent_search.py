#!/usr/bin/env python3
"""Unit tests for the ST-17 X recent-search tool (no live token required)."""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import X_RECENT_SEARCH_MARKER
from x_recent_search_tool import (
    SEARCH_URL,
    UNAVAILABLE,
    X_RECENT_SEARCH_V1,
    Tools,
    allow_call,
    compact_posts,
    lookup_posts,
    sanitize_query,
)


class XRecentSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        allow_call.__globals__["_CALLS"].clear()

    def test_marker_matches_contract(self) -> None:
        self.assertEqual(X_RECENT_SEARCH_V1, X_RECENT_SEARCH_MARKER)
        source = Path(__file__).with_name("x_recent_search_tool.py").read_text(encoding="utf-8")
        self.assertIn(X_RECENT_SEARCH_MARKER, source)
        self.assertNotIn("public_metrics", source)
        self.assertNotIn("nitter", source.lower())

    def test_sanitize_and_compact_omits_metrics(self) -> None:
        self.assertEqual(sanitize_query("  Tesla   SpaceX  "), "Tesla SpaceX")
        payload = compact_posts(
            {
                "data": [
                    {
                        "id": "2093794565274669068",
                        "text": "hello from x " * 40,
                        "created_at": "2026-09-07T12:00:00.000Z",
                        "author_id": "44196397",
                        "public_metrics": {"like_count": 99},
                    }
                ],
                "includes": {"users": [{"id": "44196397", "username": "elonmusk", "name": "Elon"}]},
            },
            query="Tesla",
            limit=10,
        )
        blob = json.dumps(payload, ensure_ascii=False)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["posts"][0]["author"], "elonmusk")
        self.assertEqual(payload["posts"][0]["url"], "https://x.com/elonmusk/status/2093794565274669068")
        self.assertLessEqual(len(payload["posts"][0]["text"]), 181)
        self.assertNotIn("like_count", blob)
        self.assertNotIn("public_metrics", blob)
        self.assertNotIn("Elon", blob)

    def test_lookup_requests_minimal_fields(self) -> None:
        seen: dict[str, Any] = {}

        def http(url: str, token: str, params: dict[str, str]) -> dict:
            seen["url"] = url
            seen["token"] = token
            seen["params"] = params
            return {
                "data": [
                    {
                        "id": "1",
                        "text": "live post",
                        "created_at": "2026-09-07T01:00:00.000Z",
                        "author_id": "9",
                    }
                ],
                "includes": {"users": [{"id": "9", "username": "spacex"}]},
            }

        raw = lookup_posts("tok", "from:spacex", max_results=8, http=http)
        data = json.loads(raw)
        self.assertTrue(data["ok"])
        self.assertEqual(data["posts"][0]["author"], "spacex")
        self.assertEqual(seen["url"], SEARCH_URL)
        self.assertEqual(seen["params"]["max_results"], "10")
        self.assertEqual(seen["params"]["tweet.fields"], "created_at,author_id")
        self.assertEqual(seen["params"]["user.fields"], "username")
        self.assertNotIn("public_metrics", seen["params"]["tweet.fields"])

    def test_missing_token_and_cap(self) -> None:
        tools = Tools()
        tools.valves.X_BEARER_TOKEN = ""
        first = json.loads(tools.search_x_posts("Tesla", __metadata__={"chat_id": "c1"}))
        self.assertFalse(first["ok"])
        self.assertEqual(first["error"], UNAVAILABLE)
        tools.valves.X_BEARER_TOKEN = "x"
        tools.valves.MAX_CALLS_PER_TURN = 2

        def http(_url: str, _token: str, _params: dict[str, str], *_args: object, **_kwargs: object) -> dict:
            return {"title": "Unauthorized", "status": 401}

        import x_recent_search_tool as mod

        orig = mod.x_get
        mod.x_get = http  # type: ignore[assignment]
        try:
            tools.search_x_posts("a", __metadata__={"chat_id": "cap"})
            tools.search_x_posts("a", __metadata__={"chat_id": "cap"})
            capped = json.loads(tools.search_x_posts("a", __metadata__={"chat_id": "cap"}))
        finally:
            mod.x_get = orig
        self.assertTrue(capped.get("capped"))
        self.assertEqual(capped["error"], "本轮 X 查询已达上限")


if __name__ == "__main__":
    unittest.main()
