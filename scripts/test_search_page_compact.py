#!/usr/bin/env python3
"""Unit tests for search_page_compact (no live OWUI)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from search_page_compact import compact_search_pages


def test_keeps_current_turn_full() -> None:
    page = "西北公路 " + ("路况 " * 900) + " https://example.com/a"
    body = {
        "input": [
            {"type": "function_call_output", "call_id": "old", "output": page},
            {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "继续"}]},
            {"type": "function_call_output", "call_id": "now", "output": page},
        ]
    }
    compact_search_pages(body)
    items = body["input"]
    assert "西北公路" in items[0]["output"]
    assert "[compacted source]" in items[0]["output"]
    assert "https://example.com/a" in items[0]["output"]
    assert len(items[0]["output"]) < 2000
    assert items[2]["output"] == page


def test_no_model_allowlist() -> None:
    body = {
        "model": "some-future-model-xyz",
        "input": [
            {
                "type": "function_call_output",
                "output": "标题\n" + ("段落 " * 900) + "\nhttps://a.com/x",
            },
            {"type": "message", "role": "user", "content": "继续"},
        ],
    }
    compact_search_pages(body)
    assert "[compacted source]" in body["input"][0]["output"]
    assert "https://a.com/x" in body["input"][0]["output"]


def test_leaves_reasoning_alone() -> None:
    thought = "内部推理 " * 400
    body = {
        "input": [
            {"type": "reasoning", "summary": [{"type": "summary_text", "text": thought}]},
            {"type": "message", "role": "user", "content": "继续"},
        ]
    }
    compact_search_pages(body)
    assert body["input"][0]["summary"][0]["text"] == thought


def test_leaves_assistant_answer_alone() -> None:
    itinerary = "行程安排 " + ("第几天去某处。 " * 200)
    body = {
        "input": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": itinerary}],
            },
            {"type": "message", "role": "user", "content": "继续"},
        ]
    }
    compact_search_pages(body)
    assert body["input"][0]["content"][0]["text"] == itinerary


def test_short_page_untouched() -> None:
    body = {
        "input": [
            {"type": "function_call_output", "output": "短结果 https://a.com"},
            {"type": "message", "role": "user", "content": "继续"},
        ]
    }
    compact_search_pages(body)
    assert body["input"][0]["output"] == "短结果 https://a.com"


def test_already_compacted_stays() -> None:
    text = "[compacted source]\n已经压过 " + ("x" * 3000)
    body = {
        "input": [
            {"type": "function_call_output", "output": text},
            {"type": "message", "role": "user", "content": "继续"},
        ]
    }
    compact_search_pages(body)
    assert body["input"][0]["output"] == text


if __name__ == "__main__":
    test_keeps_current_turn_full()
    test_no_model_allowlist()
    test_leaves_reasoning_alone()
    test_leaves_assistant_answer_alone()
    test_short_page_untouched()
    test_already_compacted_stays()
    print("ok")
