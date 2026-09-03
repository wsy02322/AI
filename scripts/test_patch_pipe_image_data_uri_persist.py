#!/usr/bin/env python3
"""Unit tests for the ST-13 pipe + guard patches (no live instance required)."""

from __future__ import annotations

import asyncio
import re
import unittest

import patch_guard_image_context_data_uri as guard_patch
import patch_pipe_image_data_uri_persist as pipe_patch

BIG_B64 = "A" * 4096
DATA_URI = f"data:image/png;base64,{BIG_B64}"
FILE_URL = "/api/v1/files/abc-123/content"


def _load_materialize(*, storage_works: bool):
    """Rebuild `_materialize_image_entry` around the patched hunk, at live indentation.

    The hunk sits 16 spaces deep in the pipe, so the surrounding scaffold has to keep
    that exact nesting or the replacement would only compile by accident.
    """
    head = [
        "def _make(STORAGE_WORKS):",
        "        async def _materialize_image_from_str(text):",
        '            if text.startswith("data:"):',
        '                return "/api/v1/files/stored/content" if STORAGE_WORKS else None',
        "            return text",
        "",
        "        async def _materialize_image_entry(entry):",
        "            if entry is None:",
        "                return None",
        "            if isinstance(entry, str):",
        "                return await _materialize_image_from_str(entry)",
        "            if isinstance(entry, dict):",
    ]
    tail = [
        "                        nested = await _materialize_image_entry(candidate)",
        "                        if nested:",
        "                            return nested",
        '                for key in ("b64_json", "b64", "base64"):',
        "                    val = entry.get(key)",
        "                    if isinstance(val, str) and val.strip():",
        '                        return "/api/v1/files/from-b64/content" if STORAGE_WORKS else None',
        "            return None",
        "",
        "        return _materialize_image_entry",
    ]
    src = "\n".join(head) + "\n" + pipe_patch.NEW_URL_BRANCH + "\n".join(tail) + "\n"
    ns: dict = {}
    exec(compile(src, "<pipe-hunk>", "exec"), ns)
    return ns["_make"](storage_works)


def _load_guard():
    """Exec the patched guard module and return its Filter instance."""
    patched = guard_patch.patch_content(GUARD_FIXTURE)
    ns: dict = {}
    exec(compile(patched, "<guard>", "exec"), ns)
    return ns["Filter"]()


# Trimmed copy of the live guard (2026-09-03) -- the hunks this patch anchors on.
GUARD_FIXTURE = '''
import re
from typing import Any, Optional

_DATA_IMG_MD = re.compile(r"!\\[[^\\]]*\\]\\((?:data:image/[^)]+|/api/v1/files/[^)]+)\\)", re.I)


class Filter:
    def inlet(self, body: dict, __model__: Optional[dict] = None) -> dict:
        if not isinstance(body, dict):
            return body

        def _is_target_model() -> bool:
            return "-image" in str(body.get("model") or "").lower()

        if not _is_target_model():
            return body

        messages = body.get("messages")
        if not isinstance(messages, list) or len(messages) < 2:
            return body

        def _has_image(msg: dict) -> bool:
            content = msg.get("content")
            if isinstance(content, str):
                return "data:image" in content or "/api/v1/files/" in content
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") in {"image_url", "input_image", "image"}:
                        return True
            return False

        def _strip_images(msg: dict, note: str) -> None:
            content = msg.get("content")
            if isinstance(content, str):
                if "data:image" in content or "/api/v1/files/" in content:
                    msg["content"] = _DATA_IMG_MD.sub(note, content).strip() or note
                return
            if not isinstance(content, list):
                return
            kept = []
            for block in content:
                if not isinstance(block, dict):
                    kept.append(block)
                    continue
                if block.get("type") in {"image_url", "input_image", "image"}:
                    continue
                if block.get("type") in {"text", "input_text"}:
                    text = block.get("text")
                    if isinstance(text, str) and ("data:image" in text or "/api/v1/files/" in text):
                        block = dict(block)
                        block["text"] = _DATA_IMG_MD.sub(note, text).strip() or note
                kept.append(block)
            msg["content"] = kept if kept else note

        last_user_idx = None
        for i in range(len(messages) - 1, -1, -1):
            if isinstance(messages[i], dict) and messages[i].get("role") == "user":
                last_user_idx = i
                break
        if last_user_idx is None:
            return body

        keep_indices = {last_user_idx}
        for i in range(last_user_idx - 1, -1, -1):
            msg = messages[i]
            if isinstance(msg, dict) and msg.get("role") == "assistant" and _has_image(msg):
                keep_indices.add(i)
                break

        note = "[Earlier image omitted to reduce context size]"
        for i, msg in enumerate(messages):
            if isinstance(msg, dict) and i not in keep_indices and _has_image(msg):
                _strip_images(msg, note)
        return body
'''


class PipePatchTests(unittest.TestCase):
    def test_hunk_unique_and_marker_added(self) -> None:
        patched = pipe_patch.patch_content(pipe_patch.OLD_URL_BRANCH)
        self.assertIn(pipe_patch.MARKER, patched)
        self.assertIn("_materialize_image_from_str(candidate_url)", patched)

    def test_idempotent(self) -> None:
        once = pipe_patch.patch_content(pipe_patch.OLD_URL_BRANCH)
        self.assertEqual(once, pipe_patch.patch_content(once))

    def test_aborts_on_mismatch(self) -> None:
        with self.assertRaises(SystemExit):
            pipe_patch.patch_content("nothing to anchor on")

    def test_data_uri_is_stored(self) -> None:
        fn = _load_materialize(storage_works=True)
        got = asyncio.run(fn({"image_url": {"url": DATA_URI}}))
        self.assertEqual(got, "/api/v1/files/stored/content")

    def test_data_uri_falls_back_when_storage_down(self) -> None:
        fn = _load_materialize(storage_works=False)
        self.assertEqual(asyncio.run(fn({"url": DATA_URI})), DATA_URI)

    def test_http_and_file_urls_unchanged(self) -> None:
        fn = _load_materialize(storage_works=True)
        self.assertEqual(asyncio.run(fn({"url": "https://cdn.example/x.png"})), "https://cdn.example/x.png")
        self.assertEqual(asyncio.run(fn({"url": FILE_URL})), FILE_URL)
        self.assertEqual(asyncio.run(fn({"url": "  relative/path.png  "})), "relative/path.png")

    def test_b64_branch_still_reached(self) -> None:
        fn = _load_materialize(storage_works=True)
        self.assertEqual(asyncio.run(fn({"b64_json": BIG_B64})), "/api/v1/files/from-b64/content")


class GuardPatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.filter = _load_guard()

    def _run(self, messages: list[dict]) -> list[dict]:
        body = {"model": "google/gemini-3.1-flash-image", "messages": messages}
        return self.filter.inlet(body)["messages"]

    def test_marker_and_compiles(self) -> None:
        patched = guard_patch.patch_content(GUARD_FIXTURE)
        self.assertIn(guard_patch.MARKER, patched)
        self.assertEqual(patched, guard_patch.patch_content(patched))

    def test_canvas_data_uri_is_dropped(self) -> None:
        out = self._run(
            [
                {"role": "user", "content": "draw a frog"},
                {"role": "assistant", "content": f"![Generated image 1]({DATA_URI})"},
                {"role": "user", "content": "make it night"},
            ]
        )
        self.assertNotIn("data:image", out[1]["content"])
        self.assertIn("Start a new chat", out[1]["content"])

    def test_canvas_file_url_is_kept(self) -> None:
        out = self._run(
            [
                {"role": "user", "content": "draw a frog"},
                {"role": "assistant", "content": f"![Generated image 1]({FILE_URL})"},
                {"role": "user", "content": "make it night"},
            ]
        )
        self.assertIn(FILE_URL, out[1]["content"])

    def test_newest_user_message_untouched(self) -> None:
        user_content = [
            {"type": "text", "text": "edit this"},
            {"type": "image_url", "image_url": {"url": DATA_URI}},
        ]
        out = self._run(
            [
                {"role": "assistant", "content": f"![Generated image 1]({FILE_URL})"},
                {"role": "user", "content": user_content},
            ]
        )
        self.assertEqual(out[-1]["content"], user_content)

    def test_older_images_still_stripped(self) -> None:
        out = self._run(
            [
                {"role": "user", "content": "one"},
                {"role": "assistant", "content": f"![old]({FILE_URL})"},
                {"role": "user", "content": "two"},
                {"role": "assistant", "content": f"![new]({FILE_URL})"},
                {"role": "user", "content": "three"},
            ]
        )
        self.assertNotIn(FILE_URL, out[1]["content"])
        self.assertIn(FILE_URL, out[3]["content"])

    def test_bare_data_uri_without_markdown(self) -> None:
        out = self._run(
            [
                {"role": "user", "content": "draw"},
                {"role": "assistant", "content": DATA_URI},
                {"role": "user", "content": "again"},
            ]
        )
        self.assertNotIn("data:image", out[1]["content"])

    def test_canvas_image_block_data_uri_dropped(self) -> None:
        out = self._run(
            [
                {"role": "user", "content": "draw"},
                {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "here you go"},
                        {"type": "image_url", "image_url": {"url": DATA_URI}},
                    ],
                },
                {"role": "user", "content": "again"},
            ]
        )
        blocks = out[1]["content"]
        self.assertTrue(all(b.get("type") != "image_url" for b in blocks))
        self.assertIn("here you go", blocks[0]["text"])

    def test_non_image_model_untouched(self) -> None:
        messages = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": f"![x]({DATA_URI})"},
            {"role": "user", "content": "again"},
        ]
        body = {"model": "x-ai/grok-4.6", "messages": messages}
        self.assertIn("data:image", self.filter.inlet(body)["messages"][1]["content"])

    def test_no_data_uri_survives_anywhere(self) -> None:
        out = self._run(
            [
                {"role": "user", "content": f"![a]({DATA_URI})"},
                {"role": "assistant", "content": f"![b]({DATA_URI})"},
                {"role": "user", "content": f"prefix ![c]({DATA_URI}) suffix"},
                {"role": "assistant", "content": f"![d]({DATA_URI})"},
                {"role": "user", "content": "final"},
            ]
        )
        replayed = "".join(str(m["content"]) for m in out)
        self.assertNotIn("data:image", replayed)
        self.assertFalse(re.search(r"base64,A{100}", replayed))


if __name__ == "__main__":
    unittest.main()
