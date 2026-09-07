#!/usr/bin/env python3
"""Unit tests for the T1 Pipe compact patch (no live OWUI)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from patch_pipe_search_page_compact import MARKER, NEW_HELPERS, OLD_CALL, OLD_HELPERS, patch_content


STUB = f"""prefix
{OLD_HELPERS}
mid
{OLD_CALL}
        body.input = validated
suffix COMPARE_CROSS_MODEL_REASONING_V1 FABLE_UNSIGNED_SUMMARY_V1
"""


def test_patch_inserts_marker_once() -> None:
    patched = patch_content(STUB)
    assert patched.count(MARKER) >= 1
    assert "apply_search_page_compaction(normalized)" in patched
    assert "compacted_pages" in patched
    assert "COMPARE_CROSS_MODEL_REASONING_V1" in patched
    assert patch_content(patched) == patched


def test_helpers_compact_old_page() -> None:
    namespace: dict = {}
    exec(
        "from typing import Any\nimport re\n"
        "def apply_replay_tool_output_budget():\n"
        "    omitted_call_ids = set()\n"
        + NEW_HELPERS,
        namespace,
    )
    page = "西北公路 " + ("路况 " * 900) + " https://example.com/a"
    items = [
        {"type": "function_call_output", "output": page},
        {"type": "message", "role": "user", "content": "继续"},
        {"type": "function_call_output", "output": page},
        {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "行程 " + ("天 " * 400)}]},
    ]
    changed = namespace["apply_search_page_compaction"](items)
    assert changed == 1
    assert "[compacted source]" in items[0]["output"]
    assert items[2]["output"] == page
    assert "行程 " in items[3]["content"][0]["text"]


if __name__ == "__main__":
    test_patch_inserts_marker_once()
    test_helpers_compact_old_page()
    print("ok")
