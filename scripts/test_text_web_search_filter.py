#!/usr/bin/env python3
"""Unit tests for the thin text Web Search Filter inlet."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import (
    CHINA_TEXT_MODEL_IDS,
    IMAGE_MODEL_IDS,
    PIPE,
    SONAR_MODEL_IDS,
    TEXT_WEB_SEARCH_MODEL_IDS,
)
from text_web_search_filter import (
    Filter,
    TEXT_WEB_SEARCH_COUNTED_EXA_V1,
    TEXT_WEB_SEARCH_DENY_CLASS_V1,
    TEXT_WEB_SEARCH_OPENAI_EXA_V1,
    TEXT_WEB_SEARCH_XAI_NATIVE_V1,
)


def _expected_engine(model_id: str) -> str:
    lowered = model_id.lower()
    if any(marker in lowered for marker in ("x-ai.", "x-ai/", "xai.", "xai/")):
        return "native"
    if any(marker in lowered for marker in ("openai.", "openai/", "google.", "google/")):
        return "exa"
    return "auto"


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

    def test_qualified_text_writes_search_and_fetch(self) -> None:
        self.assertGreaterEqual(len(TEXT_WEB_SEARCH_MODEL_IDS), 12)
        self.assertTrue(set(CHINA_TEXT_MODEL_IDS) <= set(TEXT_WEB_SEARCH_MODEL_IDS))
        self.assertTrue(set(TEXT_WEB_SEARCH_MODEL_IDS).isdisjoint(IMAGE_MODEL_IDS))
        self.assertTrue(set(TEXT_WEB_SEARCH_MODEL_IDS).isdisjoint(SONAR_MODEL_IDS))
        for model_id in TEXT_WEB_SEARCH_MODEL_IDS:
            body, metadata = _run(model_id)
            tools = metadata["openrouter_pipe"]["server_tools"]
            self.assertEqual(set(tools), {"web_search", "web_fetch"}, model_id)
            engine = _expected_engine(model_id)
            self.assertEqual(tools["web_search"]["engine"], engine, model_id)
            self.assertEqual(tools["web_fetch"]["engine"], engine, model_id)
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

    def test_video_early_return_unknown_text_gets_tools(self) -> None:
        video_id = f"{PIPE}.minimax.hailuo-3-max"
        metadata = {"openrouter_pipe": {"server_tools": {"advisor": {}}}}
        Filter().inlet(
            {"model": video_id},
            __model__={
                "id": video_id,
                "name": "Hailuo video",
                "meta": {"capabilities": {"video_generation": True}},
            },
            __metadata__=metadata,
        )
        self.assertEqual(metadata["openrouter_pipe"]["server_tools"], {"advisor": {}})

        _, kimi = _run(f"{PIPE}.moonshotai.kimi-k3")
        self.assertIn("web_search", kimi["openrouter_pipe"]["server_tools"])
        self.assertEqual(kimi["openrouter_pipe"]["server_tools"]["web_search"]["engine"], "auto")

        _, unknown = _run(f"{PIPE}.unknown.not-in-allowlist")
        self.assertIn("web_search", unknown["openrouter_pipe"]["server_tools"])

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

    def test_unmetered_native_uses_exa_anthropic_stays_auto(self) -> None:
        from pathlib import Path

        import text_web_search_filter as filt_mod

        source = Path(filt_mod.__file__).read_text(encoding="utf-8")
        self.assertIn(TEXT_WEB_SEARCH_COUNTED_EXA_V1, source)
        self.assertIn(TEXT_WEB_SEARCH_OPENAI_EXA_V1, source)
        self.assertIn(TEXT_WEB_SEARCH_XAI_NATIVE_V1, source)
        self.assertIn(TEXT_WEB_SEARCH_DENY_CLASS_V1, source)
        _, deepseek = _run(f"{PIPE}.deepseek.deepseek-v4-pro-0813")
        _, kimi = _run(f"{PIPE}.moonshotai.kimi-k3")
        _, qwen = _run(f"{PIPE}.qwen.qwen3.8-max-0902")
        self.assertEqual(deepseek["openrouter_pipe"]["server_tools"]["web_search"]["engine"], "auto")
        self.assertEqual(kimi["openrouter_pipe"]["server_tools"]["web_search"]["engine"], "auto")
        self.assertEqual(qwen["openrouter_pipe"]["server_tools"]["web_search"]["engine"], "auto")
        _, astra = _run(f"{PIPE}.openai.gpt-6-astra-pro")
        _, sol = _run(f"{PIPE}.openai.gpt-5.6-sol")
        _, grok = _run(f"{PIPE}.x-ai.grok-4.6")
        _, flash = _run(f"{PIPE}.google.gemini-3.8-flash")
        _, gemini_pro = _run(f"{PIPE}.google.gemini-3.1-pro-preview")
        _, opus = _run(f"{PIPE}.anthropic.claude-opus-5")
        _, fable = _run(f"{PIPE}.anthropic.claude-fable-5.1")
        self.assertEqual(astra["openrouter_pipe"]["server_tools"]["web_search"]["engine"], "exa")
        self.assertEqual(sol["openrouter_pipe"]["server_tools"]["web_search"]["engine"], "exa")
        self.assertEqual(grok["openrouter_pipe"]["server_tools"]["web_search"]["engine"], "native")
        self.assertEqual(grok["openrouter_pipe"]["server_tools"]["web_fetch"]["engine"], "native")
        self.assertEqual(flash["openrouter_pipe"]["server_tools"]["web_search"]["engine"], "exa")
        self.assertEqual(gemini_pro["openrouter_pipe"]["server_tools"]["web_search"]["engine"], "exa")
        self.assertEqual(opus["openrouter_pipe"]["server_tools"]["web_search"]["engine"], "auto")
        self.assertEqual(fable["openrouter_pipe"]["server_tools"]["web_search"]["engine"], "auto")

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
