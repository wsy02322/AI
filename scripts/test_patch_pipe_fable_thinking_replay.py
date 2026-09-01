#!/usr/bin/env python3
"""Unit tests for Fable unsigned-summary Pipe patch (no live instance required)."""

from __future__ import annotations

import unittest

from patch_pipe_fable_thinking_replay import (
    MARKER,
    NEW_INCLUDE,
    NEW_RETRY_MATCH,
    NEW_UNSIGNED,
    OLD_RETRY_MATCH,
    OLD_UNSIGNED,
    REPLACEMENTS,
    patch_content,
)


def _clean_str(value):
    return value.strip() if isinstance(value, str) else ""


def _load_unsigned():
    ns: dict = {"Any": object, "_clean_str": _clean_str}
    exec(
        "from typing import Any\n" + NEW_UNSIGNED,
        ns,
    )
    return ns["_reasoning_item_unsigned"], ns["_reasoning_crypto_fields"]


def _load_strip():
    unsigned, _ = _load_unsigned()
    ns: dict = {
        "Any": object,
        "_clean_str": _clean_str,
        "_reasoning_item_unsigned": unsigned,
    }
    exec(
        "from typing import Any\n"
        + '''
def _detail_unsigned_text(detail):
    if not isinstance(detail, dict) or detail.get("type") != "reasoning.text":
        return False
    if _clean_str(detail.get("signature")):
        return False
    text = detail.get("text")
    return isinstance(text, str) and bool(text.strip())

def _strip_unreplayable_anthropic_reasoning(items):
    drop_idx = set()
    span = []
    tainted = False
    for idx, item in enumerate(items):
        if isinstance(item, dict) and item.get("type") == "reasoning":
            span.append(idx)
            if _reasoning_item_unsigned(item):
                tainted = True
        elif isinstance(item, dict) and item.get("type") == "message" and item.get("role") == "user":
            if tainted:
                drop_idx.update(span)
            span = []
            tainted = False
    if tainted:
        drop_idx.update(span)
    out = []
    changed = bool(drop_idx)
    for idx, item in enumerate(items):
        if idx in drop_idx:
            continue
        if isinstance(item, dict) and isinstance(item.get("reasoning_details"), list):
            if any(_detail_unsigned_text(d) for d in item["reasoning_details"]):
                changed = True
                item = {k: v for k, v in item.items() if k != "reasoning_details"}
        out.append(item)
    return out if changed else items
''',
        ns,
    )
    return ns["_strip_unreplayable_anthropic_reasoning"]


def _is_anthropic_model_id(model_id: str) -> bool:
    lowered = (model_id or "").lower()
    return "anthropic" in lowered or "claude" in lowered


class FakeError:
    def __init__(self, status: int, *, upstream_message: str | None = None) -> None:
        self.status = status
        self.upstream_message = upstream_message
        self.openrouter_message = None
        self.reason = None
        self.raw_body = None

    def __str__(self) -> str:
        return self.upstream_message or ""


class FakeBody:
    def __init__(self, model: str, input_items: list) -> None:
        self.model = model
        self.api_model = model
        self.input = input_items


class FakeLogger:
    def __init__(self) -> None:
        self.infos: list[str] = []

    def info(self, msg: str, *args) -> None:
        self.infos.append(msg % args if args else msg)


def _load_retry_method():
    stub = (
        "class ReasoningConfigManager:\n"
        "    def _strip_replayed_reasoning(self, responses_body):\n"
        "        input_items = getattr(responses_body, 'input', None)\n"
        "        if not isinstance(input_items, list):\n"
        "            return False\n"
        "        changed = False\n"
        "        cleaned = []\n"
        "        for item in input_items:\n"
        "            if isinstance(item, dict):\n"
        "                if item.get('type') == 'reasoning':\n"
        "                    changed = True\n"
        "                    continue\n"
        "                if 'reasoning_details' in item:\n"
        "                    item = {k: v for k, v in item.items() if k != 'reasoning_details'}\n"
        "                    changed = True\n"
        "            cleaned.append(item)\n"
        "        if changed:\n"
        "            responses_body.input = cleaned\n"
        "        return changed\n"
        "    def _should_retry_dropping_signed_reasoning(self, error, responses_body):\n"
        "        status = getattr(error, 'status', None)\n"
        "        if status not in (400, 404):\n"
        "            return False\n"
        "        target_model = getattr(responses_body, 'api_model', None)\n"
        "        if not (isinstance(target_model, str) and target_model.strip()):\n"
        "            target_model = str(getattr(responses_body, 'model', '') or '')\n"
        "        message_candidates = [\n"
        "            error.upstream_message,\n"
        "            error.openrouter_message,\n"
        "            getattr(error, 'reason', None),\n"
        "            str(error),\n"
        "            getattr(error, 'raw_body', None),\n"
        "        ]\n"
        "        is_signature_error = False\n"
        "        is_cross_model_error = False\n"
        "        for message in message_candidates:\n"
        "            if not isinstance(message, str):\n"
        "                continue\n"
        "            lowered = message.lower()\n"
        "            if (\n"
        "                'produced under a different model' in lowered\n"
        "                or 'encrypted reasoning' in lowered\n"
        "                or 'compaction content' in lowered\n"
        "            ):\n"
        "                is_cross_model_error = True\n"
        "                break\n"
        + NEW_RETRY_MATCH
        + "        if is_cross_model_error:\n"
        "            if not self._strip_replayed_reasoning(responses_body):\n"
        "                return False\n"
        "            return True\n"
        "        if not _is_anthropic_model_id(target_model):\n"
        "            return False\n"
        "        if not is_signature_error:\n"
        "            return False\n"
        "        if not self._strip_replayed_reasoning(responses_body):\n"
        "            return False\n"
        "        return True\n"
    )
    ns: dict = {"_is_anthropic_model_id": _is_anthropic_model_id}
    exec(stub, ns)
    mgr = ns["ReasoningConfigManager"]()
    mgr.logger = FakeLogger()
    return mgr


class PatchContentTests(unittest.TestCase):
    def test_each_hunk_is_distinct_in_fixture(self) -> None:
        source = "".join(old for _, old, _ in REPLACEMENTS)
        patched = patch_content(source)
        self.assertIn(MARKER, patched)
        self.assertIn("reasoning.encrypted_content", patched)
        self.assertIn("reasoning_crypto_by_id", patched)
        self.assertNotIn("if not isinstance(content, list):\n        return False", patched)

    def test_idempotent(self) -> None:
        source = "".join(old for _, old, _ in REPLACEMENTS)
        once = patch_content(source)
        twice = patch_content(once)
        self.assertEqual(once, twice)

    def test_aborts_on_mismatch(self) -> None:
        with self.assertRaises(SystemExit):
            patch_content("no fable hunks here")

    def test_unsigned_hunk_keeps_surrounding(self) -> None:
        source = "prefix\n" + OLD_UNSIGNED + "\nsuffix stays\n" + "".join(
            old for name, old, _ in REPLACEMENTS if name != "unsigned"
        )
        patched = patch_content(source)
        self.assertIn("prefix", patched)
        self.assertIn("suffix stays", patched)


class UnsignedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.unsigned, self.crypto = _load_unsigned()
        self.strip = _load_strip()

    def test_summary_only_is_unsigned(self) -> None:
        item = {
            "type": "reasoning",
            "id": "rs_tmp_abc",
            "summary": [{"type": "summary_text", "text": "thinking about lunch"}],
        }
        self.assertTrue(self.unsigned(item))

    def test_empty_shell_is_unsigned(self) -> None:
        self.assertTrue(self.unsigned({"type": "reasoning", "id": "rs_1"}))

    def test_encrypted_content_is_signed(self) -> None:
        self.assertFalse(
            self.unsigned(
                {
                    "type": "reasoning",
                    "id": "rs_1",
                    "summary": [{"type": "summary_text", "text": "x"}],
                    "encrypted_content": "gAAAAA",
                }
            )
        )

    def test_signature_is_signed(self) -> None:
        self.assertFalse(
            self.unsigned({"type": "reasoning", "signature": "sig-bytes", "summary": []})
        )

    def test_content_part_signature_is_signed(self) -> None:
        self.assertFalse(
            self.unsigned(
                {
                    "type": "reasoning",
                    "content": [
                        {
                            "type": "reasoning_text",
                            "text": "hi",
                            "signature": "sig",
                        }
                    ],
                }
            )
        )

    def test_strip_drops_summary_only_span(self) -> None:
        items = [
            {"type": "message", "role": "user", "content": "q1"},
            {
                "type": "reasoning",
                "id": "rs_tmp_1",
                "summary": [{"type": "summary_text", "text": "plan"}],
            },
            {"type": "message", "role": "assistant", "content": "a1"},
            {"type": "message", "role": "user", "content": "q2"},
        ]
        out = self.strip(items)
        self.assertEqual(len(out), 3)
        self.assertTrue(all(x.get("type") != "reasoning" for x in out))

    def test_strip_keeps_encrypted_span(self) -> None:
        items = [
            {
                "type": "reasoning",
                "id": "rs_1",
                "encrypted_content": "cipher",
                "summary": [{"type": "summary_text", "text": "plan"}],
            },
            {"type": "message", "role": "assistant", "content": "a1"},
        ]
        self.assertEqual(self.strip(items), items)

    def test_crypto_fields_copy(self) -> None:
        carried = self.crypto(
            {
                "type": "reasoning",
                "id": "rs_1",
                "encrypted_content": "cipher",
                "signature": "sig",
                "format": "anthropic-claude-v1",
                "summary": [{"type": "summary_text", "text": "ui"}],
            }
        )
        self.assertEqual(
            carried,
            {
                "encrypted_content": "cipher",
                "signature": "sig",
                "format": "anthropic-claude-v1",
            },
        )


class IncludeTests(unittest.TestCase):
    def test_appends_include(self) -> None:
        helper = NEW_INCLUDE.split("def apply_context_transforms", 1)[0]
        ns: dict = {"Any": object}
        exec("from typing import Any\n" + helper, ns)
        body = type("Body", (), {"include": None})()
        ns["_ensure_reasoning_encrypted_include"](body)
        self.assertEqual(body.include, ["reasoning.encrypted_content"])
        body.include = ["file_search_call.results"]
        ns["_ensure_reasoning_encrypted_include"](body)
        self.assertEqual(
            body.include,
            ["file_search_call.results", "reasoning.encrypted_content"],
        )


class RetryGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mgr = _load_retry_method()

    def test_fable_cannot_be_modified_retries(self) -> None:
        body = FakeBody(
            "anthropic/claude-fable-5",
            [
                {"type": "message", "role": "user", "content": "hi"},
                {
                    "type": "reasoning",
                    "id": "rs_tmp_1",
                    "summary": [{"type": "summary_text", "text": "plan"}],
                },
            ],
        )
        err = FakeError(
            400,
            upstream_message=(
                "messages.1.content.1: `thinking` or `redacted_thinking` blocks "
                "in the latest assistant message cannot be modified."
            ),
        )
        self.assertTrue(self.mgr._should_retry_dropping_signed_reasoning(err, body))
        self.assertTrue(all(x.get("type") != "reasoning" for x in body.input if isinstance(x, dict)))

    def test_old_thinking_block_phrase_still_retries(self) -> None:
        body = FakeBody(
            "anthropic/claude-opus-5",
            [{"type": "reasoning", "encrypted_content": "x"}],
        )
        err = FakeError(400, upstream_message="thinking block signature does not match")
        self.assertTrue(self.mgr._should_retry_dropping_signed_reasoning(err, body))

    def test_unrelated_400_does_not_retry(self) -> None:
        body = FakeBody("anthropic/claude-fable-5", [{"type": "reasoning", "id": "rs"}])
        original = list(body.input)
        err = FakeError(400, upstream_message="rate limit exceeded")
        self.assertFalse(self.mgr._should_retry_dropping_signed_reasoning(err, body))
        self.assertEqual(body.input, original)

    def test_cross_model_branch_untouched(self) -> None:
        body = FakeBody(
            "anthropic/claude-opus-5",
            [{"type": "message", "reasoning_details": [{"type": "reasoning.encrypted", "data": "c"}]}],
        )
        err = FakeError(404, upstream_message="encrypted reasoning produced under a different model")
        self.assertTrue(self.mgr._should_retry_dropping_signed_reasoning(err, body))


class FixtureLiveHunks(unittest.TestCase):
    def test_old_retry_still_in_s2_script(self) -> None:
        # Composability: S2′ still writes the pre-C phrase; this patch upgrades it.
        self.assertIn("thinking block", OLD_RETRY_MATCH)
        self.assertIn("redacted_thinking", NEW_RETRY_MATCH)


if __name__ == "__main__":
    unittest.main()
