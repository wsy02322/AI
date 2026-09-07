#!/usr/bin/env python3
"""Unit tests for Sol / OpenAI server-tool 400 retry inject (no live OWUI)."""

from __future__ import annotations

import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from patch_pipe_server_tool_fail import (
    FLAG_ANCHOR,
    HELPER_ANCHOR,
    HELPERS,
    MARKER,
    RETRY_ANCHOR,
    inject,
)


STUB = f"""prefix
        reasoning_retry_attempted = False
{FLAG_ANCHOR}            type(__request__).__name__,
        )
        while True:
            try:
                return
            except OpenRouterAPIError as exc:
{RETRY_ANCHOR}                    exc,
                )
                return
{HELPER_ANCHOR}    model_id, plugins, tools, *, fusion_enabled, is_task_request):
    return None
suffix COMPARE_CROSS_MODEL_REASONING_V1 FABLE_UNSIGNED_SUMMARY_V1
"""


def _helpers() -> dict:
    namespace: dict = {}
    exec("from typing import Any\nimport re\n" + HELPERS, namespace)
    return namespace


class ServerToolFailPatchTests(unittest.TestCase):
    def test_inject_is_idempotent(self) -> None:
        patched = inject(STUB)
        self.assertIn(MARKER, patched)
        self.assertIn("server_tool_image_retry_attempted", patched)
        self.assertIn("_stf_strip_input_images", patched)
        self.assertIn("_stf_disable_server_tools", patched)
        self.assertIn("COMPARE_CROSS_MODEL_REASONING_V1", patched)
        self.assertEqual(inject(patched), patched)
        self.assertEqual(patched.count(MARKER), patched.count("SERVER_TOOL_FAIL_RETRY_V1"))

    def test_inject_requires_unique_anchors(self) -> None:
        with self.assertRaises(RuntimeError):
            inject("no anchors here")

    def test_is_server_tool_fail_only_on_400_phrase(self) -> None:
        ns = _helpers()
        pred = ns["_stf_is_server_tool_fail"]
        self.assertTrue(
            pred(SimpleNamespace(status=400, upstream_message="Server tool request failed"))
        )
        self.assertTrue(
            pred(SimpleNamespace(status_code=400, reason="server tool request failed (id)"))
        )
        self.assertFalse(
            pred(SimpleNamespace(status=400, upstream_message="thinking cannot be modified"))
        )
        self.assertFalse(
            pred(SimpleNamespace(status=429, upstream_message="Server tool request failed"))
        )

    def test_strip_images_keeps_text_and_markdown_urls_go(self) -> None:
        ns = _helpers()
        body = SimpleNamespace(
            input=[
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "路线图 ![x](https://quickchart.io/graphviz?g=digraph)",
                        },
                        {
                            "type": "input_image",
                            "image_url": "https://example.com/a.png",
                        },
                    ],
                },
                {"type": "input_image", "image_url": "https://files.example/saved.png"},
                {"role": "user", "content": "下一阶段"},
            ]
        )
        self.assertTrue(ns["_stf_strip_input_images"](body))
        self.assertEqual(len(body.input), 2)
        self.assertEqual(body.input[0]["content"][0]["text"], "路线图 ")
        self.assertEqual(body.input[1]["content"], "下一阶段")
        self.assertFalse(ns["_stf_strip_input_images"](body))

    def test_disable_server_tools_keeps_function_tools(self) -> None:
        ns = _helpers()
        body = SimpleNamespace(
            tools=[
                {"type": "openrouter:web_search", "engine": "native"},
                {"type": "openrouter:web_fetch", "engine": "native"},
                {"type": "function", "name": "amap_drive_route"},
            ],
            stop_server_tools_when=[{"name": "step_count_is", "value": 8}],
        )
        self.assertTrue(ns["_stf_disable_server_tools"](body))
        self.assertEqual(body.tools, [{"type": "function", "name": "amap_drive_route"}])
        self.assertIsNone(body.stop_server_tools_when)
        self.assertFalse(ns["_stf_disable_server_tools"](body))

    def test_no_empty_retry_when_nothing_to_strip(self) -> None:
        ns = _helpers()
        body = SimpleNamespace(
            input=[{"role": "user", "content": "固原到靖边通不通"}],
            tools=[{"type": "function", "name": "amap_drive_route"}],
            stop_server_tools_when=None,
        )
        self.assertFalse(ns["_stf_strip_input_images"](body))
        self.assertFalse(ns["_stf_disable_server_tools"](body))


if __name__ == "__main__":
    unittest.main()
