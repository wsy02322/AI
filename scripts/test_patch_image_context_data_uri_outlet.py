#!/usr/bin/env python3
"""Unit tests for ST-14 data-URI outlet rewrite (no live instance required)."""

from __future__ import annotations

import ast
import base64
import unittest

from patch_image_context_data_uri_outlet import (
    HELPERS,
    MARKER,
    MARKER_V1,
    MARKER_V2,
    METHODS,
    looks_glued_markdown,
    looks_like_b64_chunk,
    parse_data_uri,
    patch_content,
    repair_glued_markdown,
    rewrite_assistant_text,
    rewrite_content,
    rewrite_stream_delta,
)

# 1x1 PNG
_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
_PNG_URI = f"data:image/png;base64,{_PNG_B64}"
_PNG_BYTES = base64.b64decode(_PNG_B64)

_GUARD_STUB = '''"""
title: OR Image Context Guard
author: admin
id: openrouter_image_context_guard
description: Trim historical images in multi-turn image chats to avoid context token overflows.
version: 0.1.0
"""

import re
from typing import Any, Optional

class Filter:
    def inlet(self, body: dict) -> dict:
        return body
'''


class RewriteTests(unittest.TestCase):
    def test_parse_valid_png(self) -> None:
        raw, mime = parse_data_uri(_PNG_URI)
        self.assertEqual(mime, "image/png")
        self.assertEqual(raw, _PNG_BYTES)

    def test_closed_markdown_strips_keeps_links(self) -> None:
        text = (
            f"前言\n\n![路线概览图]({_PNG_URI})\n\n"
            "[在高德打开 碌曲县→迭部县](https://uri.amap.com/navigation?from=1&to=2)\n"
            "后记"
        )
        out = rewrite_assistant_text(text, persist_fn=lambda raw, mime: "/api/v1/files/abc/content")
        self.assertNotIn("data:image", out)
        self.assertNotIn("/api/v1/files/abc/content", out)
        self.assertNotIn("路线概览图](", out)
        self.assertIn("https://uri.amap.com/navigation?from=1&to=2", out)
        self.assertIn("前言", out)
        self.assertIn("后记", out)

    def test_unclosed_markdown_strip(self) -> None:
        text = (
            "每天开多少、住哪儿。\n\n"
            "![路线概览图](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAlgAAAGQCAM"
        )
        out = rewrite_assistant_text(text)
        self.assertNotIn("data:image", out)
        self.assertNotIn("路线概览图](", out)
        self.assertIn("每天开多少", out)

    def test_unclosed_valid_png_is_stripped(self) -> None:
        text = f"hello\n![路线概览图]({_PNG_URI}"
        out = rewrite_assistant_text(
            text, persist_fn=lambda raw, mime: "/api/v1/files/map/content"
        )
        self.assertEqual(out, "hello")
        self.assertNotIn("/api/v1/files/", out)

    def test_link_without_bang(self) -> None:
        text = f"[路线概览图]({_PNG_URI})"
        out = rewrite_assistant_text(text)
        self.assertEqual(out, "")

    def test_truncated_png_stripped(self) -> None:
        text = "见下图 ![路线概览图](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAlgAAAGQCAMAAABF6+6q)"
        out = rewrite_assistant_text(text)
        self.assertNotIn("data:image", out)
        self.assertIn("见下图", out)

    def test_output_list_rewritten(self) -> None:
        content = [
            {"type": "message", "content": [{"type": "output_text", "text": f"x ![]({_PNG_URI})"}]}
        ]
        out = rewrite_content(content, persist_fn=lambda raw, mime: "/api/v1/files/z/content")
        self.assertEqual(out[0]["content"][0]["text"], "x")
        self.assertNotIn("data:image", out[0]["content"][0]["text"])
        self.assertNotIn("/api/v1/files/", out[0]["content"][0]["text"])

    def test_file_markdown_kept(self) -> None:
        text = "done\n![路线概览图](/api/v1/files/abc/content)"
        self.assertEqual(rewrite_assistant_text(text), text)

    def test_b64_chunk_heuristic(self) -> None:
        self.assertTrue(looks_like_b64_chunk("iVBORw0KGgoAAAANSUhEUgAA"))
        self.assertFalse(looks_like_b64_chunk("每天开多少、住哪儿"))


class StreamLayoutTests(unittest.TestCase):
    def test_stream_delta_keeps_trailing_newlines(self) -> None:
        chunks = [
            "返回威海。\n",
            "\n",
            "# 一、建议日期骨架\n",
            "\n",
            "| 日期 | 行程 | 住宿 | 定位 |\n",
            "|---|---|---|---|\n",
            "| **9/18** | 玛曲 | 同仁① | 草原 |\n",
        ]
        glued_v2 = "".join(chunk.rstrip() for chunk in chunks)
        self.assertIn("威海。#", glued_v2)
        out = "".join(rewrite_stream_delta(chunk) for chunk in chunks)
        self.assertIn("返回威海。\n\n# 一、建议日期骨架\n", out)
        self.assertIn("| 定位 |\n|---|---|---|---|\n", out)
        self.assertNotIn("---#", out)
        self.assertNotIn("||---|", out)

    def test_stream_does_not_eat_incomplete_markdown_link(self) -> None:
        chunk = "[在高德打开 碌曲县→迭部县]("
        self.assertEqual(rewrite_stream_delta(chunk), chunk)

    def test_stream_still_strips_data_uri_chunk(self) -> None:
        chunk = f"见 ![x]({_PNG_URI})\n"
        out = rewrite_stream_delta(chunk)
        self.assertNotIn("data:image", out)
        self.assertIn("见", out)


class LayoutRepairTests(unittest.TestCase):
    def test_repairs_glued_heading_and_table(self) -> None:
        glued = (
            "返回威海。---# 一、建议日期骨架| 日期 | 行程 | 住宿 | 定位 ||---|---|---|---|\n"
            "| **9/18** | 玛曲→河南县午餐→同仁 | 同仁① | 草原转人文 || **9/19** | 隆务寺 | 同仁② | 重点① |\n"
        )
        self.assertTrue(looks_glued_markdown(glued))
        out = repair_glued_markdown(glued)
        self.assertFalse(looks_glued_markdown(out))
        self.assertIn("\n# 一、建议日期骨架\n", out)
        self.assertIn("| 日期 | 行程 | 住宿 | 定位 |\n|---|---|---|---|\n", out)
        self.assertIn("| **9/18** | 玛曲→河南县午餐→同仁 | 同仁① | 草原转人文 |\n| **9/19** |", out)
        self.assertEqual(repair_glued_markdown(out), out)

    def test_repairs_glued_list_and_subheadings(self) -> None:
        glued = (
            "以后我固定按下面格式输出：1. **一句话结论**2. **住宿骨架**3. **每段只写：路线**\n"
            "重新排一遍。---# 玛曲 → 阿左旗##1. 一句话路线\n"
        )
        out = repair_glued_markdown(glued)
        self.assertIn("输出：\n1. **一句话结论**\n2. **住宿骨架**\n3. **每段只写：路线**", out)
        self.assertIn("# 玛曲 → 阿左旗\n\n## 1. 一句话路线", out)
        self.assertNotIn("---#", out)
        self.assertNotIn("##1.", out)

    def test_keeps_amap_links_and_footnotes(self) -> None:
        text = (
            "导航 [海晏→同宝山](https://uri.amap.com/navigation?from=1&to=2) 结束。\n\n"
            "[0001HNJE8MEW9NW7B4DH]: #\n"
        )
        out = repair_glued_markdown(text)
        self.assertIn("https://uri.amap.com/navigation?from=1&to=2", out)
        self.assertIn("[0001HNJE8MEW9NW7B4DH]: #", out)
        self.assertEqual(out, text)

    def test_does_not_split_opening_bold(self) -> None:
        text = "上一版把**路线、景点、道路**混在一起。\n"
        out = repair_glued_markdown(text)
        self.assertIn("把**路线、景点、道路**", out)
        self.assertNotIn("**\n\n路线", out)


class PatchTests(unittest.TestCase):
    def test_patch_inserts_marker_and_hooks(self) -> None:
        patched = patch_content(_GUARD_STUB)
        self.assertIn(MARKER, patched)
        self.assertNotIn(MARKER_V1, patched)
        self.assertNotIn(MARKER_V2, patched)
        self.assertIn("async def stream(", patched)
        self.assertIn("async def outlet(", patched)
        self.assertIn("def inlet(", patched)
        ast.parse(patched)

    def test_patch_is_idempotent(self) -> None:
        once = patch_content(_GUARD_STUB)
        twice = patch_content(once)
        self.assertEqual(once, twice)

    def test_v1_upgrades_to_v3_strip_only(self) -> None:
        v1 = (
            '"""\ndescription: Trim historical image chats; persist-or-strip assistant inline data-URI markdown (ST-14).\n"""\n'
            "import re\nfrom typing import Optional\n"
            "# DATA_URI_OUTLET_V1\n"
            "class Filter:\n"
            "    def inlet(self, body: dict) -> dict:\n"
            "        return body\n"
            "    async def _outlet_persist_image(self, raw: bytes, mime: str, user_id: str | None) -> str | None:\n"
            "        if not raw or not user_id:\n"
            "            return None\n"
            "        return \"x\"\n"
            "    def _emit(self, alt, url):\n"
            "        if True:\n"
            "                return f\"![{alt}]({url})\"\n"
        )
        upgraded = patch_content(v1)
        self.assertIn(MARKER, upgraded)
        self.assertNotIn(MARKER_V1, upgraded)
        self.assertNotIn('return f"![{alt}]({url})"', upgraded)
        self.assertIn("return None", upgraded)
        ast.parse(upgraded)

    def test_v2_upgrades_to_v3_stream_safe(self) -> None:
        v2 = (
            "# DATA_URI_OUTLET_V2 — strip assistant inline data:image markdown; keep http(s) links.\n"
            "def _outlet_rewrite_text(text: str, persist_map=None) -> str:\n"
            "    del persist_map\n"
            "    if not isinstance(text, str):\n"
            "        return text\n"
            '    if "data:image" not in text.lower():\n'
            '        return _OUTLET_DANGLING_MD.sub("", text).rstrip()\n'
            "    return text\n"
            "class Filter:\n"
            "    def inlet(self, body: dict) -> dict:\n"
            "        return body\n"
            "    async def stream(self, event):\n"
            "        async def clean_delta(text: str) -> str:\n"
            "            rewritten = _outlet_rewrite_text(text, {})\n"
            '            if "data:image" in text.lower() or rewritten != text:\n'
            "                return rewritten\n"
            "            return rewritten\n"
            "        return event\n"
        )
        upgraded = patch_content(v2)
        self.assertIn(MARKER, upgraded)
        self.assertNotIn(MARKER_V2, upgraded)
        self.assertNotIn('_OUTLET_DANGLING_MD.sub("", text).rstrip()', upgraded)
        self.assertNotIn("or rewritten != text", upgraded)
        ast.parse(upgraded)

    def test_injected_helpers_keep_newlines_without_data_uri(self) -> None:
        ns: dict = {"re": __import__("re")}
        exec(HELPERS, ns)
        rewrite = ns["_outlet_rewrite_text"]
        chunk = "返回威海。\n"
        self.assertEqual(rewrite(chunk, {}), chunk)
        text = (
            f"见 ![x]({_PNG_URI})\n"
            "[在高德打开](https://uri.amap.com/navigation?from=1&to=2)"
        )
        out = rewrite(text, {"anything": "/api/v1/files/q/content"})
        self.assertNotIn("data:image", out)
        self.assertNotIn("/api/v1/files/", out)
        self.assertIn("https://uri.amap.com/navigation?from=1&to=2", out)

    def test_methods_are_indented_class_body(self) -> None:
        self.assertTrue(METHODS.lstrip("\n").startswith("    def _outlet_meta_key"))


if __name__ == "__main__":
    unittest.main()
