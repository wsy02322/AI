#!/usr/bin/env python3
"""Unit tests for S2′ Pipe retry-gate patch (no live instance required)."""

from __future__ import annotations

import unittest

from patch_pipe_cross_model_reasoning import MARKER, NEW_RETRY, OLD_RETRY, patch_content


class FakeError:
    def __init__(
        self,
        status: int,
        *,
        upstream_message: str | None = None,
        openrouter_message: str | None = None,
        reason: str | None = None,
        raw_body: str | None = None,
        text: str = "",
    ) -> None:
        self.status = status
        self.upstream_message = upstream_message
        self.openrouter_message = openrouter_message
        self.reason = reason
        self.raw_body = raw_body
        self._text = text or (upstream_message or openrouter_message or "")

    def __str__(self) -> str:
        return self._text


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


def _is_anthropic_model_id(model_id: str) -> bool:
    lowered = (model_id or "").lower()
    return "anthropic" in lowered or "claude" in lowered


def _load_retry_method():
    """Exec the patched method body against a tiny stub class."""
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
        + NEW_RETRY
        + "\n"
        "        if not self._strip_replayed_reasoning(responses_body):\n"
        "            return False\n"
        "        return True\n"
    )
    ns: dict = {"_is_anthropic_model_id": _is_anthropic_model_id}
    exec(stub, ns)
    mgr = ns["ReasoningConfigManager"]()
    mgr.logger = FakeLogger()
    return mgr


BOUND_INPUT = [
    {"type": "message", "role": "user", "content": "hi"},
    {
        "type": "message",
        "role": "assistant",
        "content": "hello",
        "reasoning_details": [{"type": "reasoning.encrypted", "data": "cipher"}],
    },
]


class PatchContentTests(unittest.TestCase):
    def test_replaces_retry_gate_once(self) -> None:
        source = "prefix\n" + OLD_RETRY + "\nsuffix _sanitize_request_input stays\n"
        patched = patch_content(source)
        self.assertIn(MARKER, patched)
        self.assertIn("status not in (400, 404)", patched)
        self.assertIn("produced under a different model", patched)
        self.assertNotIn("if getattr(error, \"status\", None) != 400:", patched)
        self.assertIn("_sanitize_request_input stays", patched)
        self.assertEqual(patched.count(MARKER), 2)  # comment + log line

    def test_idempotent(self) -> None:
        source = "prefix\n" + OLD_RETRY + "\n"
        once = patch_content(source)
        twice = patch_content(once)
        self.assertEqual(once, twice)

    def test_aborts_on_mismatch(self) -> None:
        with self.assertRaises(SystemExit):
            patch_content("no retry gate here")


class RetryGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mgr = _load_retry_method()

    def test_cross_model_404_strips_and_retries(self) -> None:
        body = FakeBody("anthropic/claude-opus-5", [dict(item) for item in BOUND_INPUT])
        err = FakeError(
            404,
            upstream_message=(
                "This request contains encrypted reasoning or compaction content "
                "that was produced under a different model."
            ),
        )
        self.assertTrue(self.mgr._should_retry_dropping_signed_reasoning(err, body))
        self.assertTrue(all("reasoning_details" not in x for x in body.input if isinstance(x, dict)))
        self.assertTrue(any(MARKER in line for line in self.mgr.logger.infos))

    def test_cross_model_streaming_400_also_retries(self) -> None:
        body = FakeBody("openai/gpt-5.6-sol-pro", [dict(item) for item in BOUND_INPUT])
        err = FakeError(400, openrouter_message="encrypted reasoning produced under a different model")
        self.assertTrue(self.mgr._should_retry_dropping_signed_reasoning(err, body))

    def test_phrase_in_raw_body_only(self) -> None:
        body = FakeBody("x-ai/grok-4.6", [dict(item) for item in BOUND_INPUT])
        err = FakeError(404, raw_body='{"error":{"message":"compaction content that was produced under a different model"}}')
        self.assertTrue(self.mgr._should_retry_dropping_signed_reasoning(err, body))

    def test_same_model_unrelated_400_does_not_strip(self) -> None:
        body = FakeBody("anthropic/claude-opus-5", [dict(item) for item in BOUND_INPUT])
        original = [dict(item) for item in body.input]
        err = FakeError(400, upstream_message="rate limit exceeded")
        self.assertFalse(self.mgr._should_retry_dropping_signed_reasoning(err, body))
        self.assertEqual(body.input, original)

    def test_status_500_ignored(self) -> None:
        body = FakeBody("anthropic/claude-opus-5", [dict(item) for item in BOUND_INPUT])
        err = FakeError(500, upstream_message="produced under a different model")
        self.assertFalse(self.mgr._should_retry_dropping_signed_reasoning(err, body))

    def test_anthropic_signature_400_still_retries(self) -> None:
        body = FakeBody("anthropic/claude-opus-5", [dict(item) for item in BOUND_INPUT])
        err = FakeError(400, upstream_message="thinking block signature does not match")
        self.assertTrue(self.mgr._should_retry_dropping_signed_reasoning(err, body))
        self.assertTrue(all("reasoning_details" not in x for x in body.input if isinstance(x, dict)))

    def test_no_bound_items_means_no_retry(self) -> None:
        body = FakeBody(
            "anthropic/claude-opus-5",
            [{"type": "message", "role": "user", "content": "hi"}],
        )
        err = FakeError(404, upstream_message="produced under a different model")
        self.assertFalse(self.mgr._should_retry_dropping_signed_reasoning(err, body))


if __name__ == "__main__":
    unittest.main()
