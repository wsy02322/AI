#!/usr/bin/env python3
"""Unit tests for the thin text Web Search Filter inlet."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import IMAGE_MODEL_IDS, PIPE, SONAR_MODEL_IDS, TEXT_WEB_SEARCH_MODEL_IDS
from text_web_search_filter import Filter


def _run(
    model_id: str,
    *,
    user_valves: dict | None = None,
    extra_tools: dict | None = None,
    capabilities: dict | None = None,
    name: str = "",
) -> tuple[dict, dict]:
    filt = Filter()
    body = {"model": model_id, "messages": [{"role": "user", "content": "hi"}]}
    metadata = {"openrouter_pipe": {"server_tools": dict(extra_tools or {})}}
    model = {
        "id": model_id,
        "name": name or model_id,
        "meta": {"capabilities": capabilities or {}},
    }
    user = {"valves": user_valves or {}}
    out = filt.inlet(body, __user__=user, __model__=model, __metadata__=metadata)
    return out, metadata


class TextWebSearchFilterTests(unittest.TestCase):
    def test_class_level_toggle_is_true(self) -> None:
        self.assertTrue(Filter.toggle)
        self.assertTrue(Filter().toggle)

    def test_allowlist_writes_only_search_and_fetch(self) -> None:
        for model_id in TEXT_WEB_SEARCH_MODEL_IDS:
            body, metadata = _run(model_id)
            tools = metadata["openrouter_pipe"]["server_tools"]
            self.assertEqual(set(tools), {"web_search", "web_fetch"}, model_id)
            self.assertEqual(tools["web_search"]["engine"], "auto")
            self.assertEqual(tools["web_search"]["max_uses"], 3)
            self.assertEqual(tools["web_fetch"]["max_uses"], 5)
            self.assertEqual(
                metadata["openrouter_pipe"]["stop_server_tools_when"],
                [
                    {"type": "step_count_is", "step_count": 8},
                    {"type": "max_cost", "max_cost_in_dollars": 0.05},
                ],
            )
            self.assertFalse(body["features"]["web_search"])

    def test_sonar_and_images_early_return(self) -> None:
        for model_id in SONAR_MODEL_IDS + IMAGE_MODEL_IDS:
            body = {"model": model_id, "messages": []}
            metadata = {"keep": True}
            out = Filter().inlet(body, __model__={"id": model_id}, __metadata__=metadata)
            self.assertIs(out, body)
            self.assertEqual(metadata, {"keep": True})
            self.assertNotIn("openrouter_pipe", metadata)

    def test_unknown_and_video_early_return(self) -> None:
        for model_id, name in (
            (f"{PIPE}.moonshotai.kimi-k3", "Kimi K3"),
            (f"{PIPE}.unknown.not-in-allowlist", "Unknown"),
            (f"{PIPE}.minimax.hailuo-3-max", "Hailuo video"),
        ):
            metadata = {"openrouter_pipe": {"server_tools": {"advisor": {}}}}
            Filter().inlet(
                {"model": model_id},
                __model__={"id": model_id, "name": name, "meta": {"capabilities": {"video_generation": True}}}
                if "hailuo" in model_id
                else {"id": model_id, "name": name},
                __metadata__=metadata,
            )
            self.assertEqual(metadata["openrouter_pipe"]["server_tools"], {"advisor": {}})

    def test_capability_deny_even_if_name_looks_safe(self) -> None:
        metadata = {}
        Filter().inlet(
            {"model": f"{PIPE}.x-ai.grok-4.6"},
            __model__={
                "id": f"{PIPE}.x-ai.grok-4.6",
                "meta": {"capabilities": {"image_output": True}},
            },
            __metadata__=metadata,
        )
        self.assertNotIn("server_tools", (metadata.get("openrouter_pipe") or {}))

    def test_merges_existing_foreign_tools(self) -> None:
        _, metadata = _run(
            TEXT_WEB_SEARCH_MODEL_IDS[0],
            extra_tools={"advisor": {"model": "keep-me"}},
        )
        tools = metadata["openrouter_pipe"]["server_tools"]
        self.assertEqual(tools["advisor"], {"model": "keep-me"})
        self.assertIn("web_search", tools)
        self.assertIn("web_fetch", tools)

    def test_clear_own_tools_keeps_foreign_tools(self) -> None:
        _, metadata = _run(
            TEXT_WEB_SEARCH_MODEL_IDS[0],
            user_valves={"WEB_SEARCH": False, "WEB_FETCH": False},
            extra_tools={"advisor": {"model": "keep-me"}, "web_search": {"engine": "old"}},
        )
        tools = metadata["openrouter_pipe"]["server_tools"]
        self.assertEqual(tools, {"advisor": {"model": "keep-me"}})
        self.assertNotIn("stop_server_tools_when", metadata["openrouter_pipe"])


if __name__ == "__main__":
    unittest.main()
