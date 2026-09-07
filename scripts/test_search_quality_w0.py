#!/usr/bin/env python3
"""Unit tests for W0 native + max_tool_calls probe inject (no live OWUI)."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from search_quality_w0 import (
    FILTER_MARKER,
    MAX_TOOL_CALLS,
    PIPE_CALL_ANCHOR,
    PIPE_MARKER,
    PIPE_STOP_ANCHOR,
    inject_filter,
    inject_pipe,
    load_filter_class,
)
from stack_contract import PIPE
from text_web_search_ops import filter_source


def _run(cls: type, model_id: str, content: str) -> tuple[dict, dict]:
    filt = cls()
    body = {"model": model_id, "messages": [{"role": "user", "content": content}]}
    metadata: dict = {"openrouter_pipe": {}}
    model = {"id": model_id, "name": model_id, "meta": {"capabilities": {}}}
    out = filt.inlet(body, __user__={"valves": {}}, __model__=model, __metadata__=metadata)
    return out, metadata


class W0InjectTests(unittest.TestCase):
    def test_filter_inject_is_message_scoped(self) -> None:
        original = filter_source()
        patched = inject_filter(original)
        self.assertIn(FILTER_MARKER, patched)
        self.assertEqual(inject_filter(patched), patched)
        cls = load_filter_class(patched)
        sol = f"{PIPE}.openai.gpt-5.6-sol"
        unmarked, unmarked_meta = _run(cls, sol, "What is the weather in Tokyo?")
        tools = unmarked_meta["openrouter_pipe"]["server_tools"]
        self.assertEqual(tools["web_search"]["engine"], "exa")
        self.assertEqual(tools["web_fetch"]["engine"], "exa")
        self.assertIn("stop_server_tools_when", unmarked_meta["openrouter_pipe"])
        self.assertNotIn("max_tool_calls", unmarked)
        self.assertNotIn("w0_probe", unmarked_meta["openrouter_pipe"])

        marked, marked_meta = _run(
            cls,
            sol,
            f"{FILTER_MARKER} Search ten independent topics separately.",
        )
        tools = marked_meta["openrouter_pipe"]["server_tools"]
        self.assertEqual(tools["web_search"]["engine"], "native")
        self.assertEqual(tools["web_fetch"]["engine"], "native")
        self.assertEqual(marked.get("max_tool_calls"), MAX_TOOL_CALLS)
        self.assertEqual(marked_meta["openrouter_pipe"].get("max_tool_calls"), MAX_TOOL_CALLS)
        self.assertNotIn("stop_server_tools_when", marked_meta["openrouter_pipe"])
        self.assertEqual(marked_meta["openrouter_pipe"]["w0_probe"]["engine"], "native")

        opus = f"{PIPE}.anthropic.claude-opus-5"
        opus_body, opus_meta = _run(
            cls,
            opus,
            f"{FILTER_MARKER} Search ten independent topics separately.",
        )
        self.assertEqual(opus_meta["openrouter_pipe"]["server_tools"]["web_search"]["engine"], "auto")
        self.assertIn("stop_server_tools_when", opus_meta["openrouter_pipe"])
        self.assertNotIn("max_tool_calls", opus_body)

    def test_pipe_inject_copies_max_tool_calls_and_stamps(self) -> None:
        stub = (
            "prefix\n"
            + PIPE_STOP_ANCHOR
            + "\nclass RequestOrchestrator:\n    pass\n"
            + PIPE_CALL_ANCHOR
            + "        stripped_tools = 1\n"
        )
        patched = inject_pipe(stub)
        self.assertIn(PIPE_MARKER, patched)
        self.assertIn("responses_body.max_tool_calls = _mtc", patched)
        self.assertIn('eng={_eng} mtc={_mtc} stop={bool(_stop)}', patched)
        self.assertEqual(inject_pipe(patched), patched)
        self.assertEqual(patched.count(PIPE_STOP_ANCHOR), 1)
        self.assertEqual(patched.count(PIPE_CALL_ANCHOR), 1)


if __name__ == "__main__":
    unittest.main()
