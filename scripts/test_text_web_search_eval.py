#!/usr/bin/env python3
"""Unit tests for ST-14 quality scoring. No live calls."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import PIPE
from text_web_search_eval import recommend_next_step, score_case, summarize
from text_web_search_eval_cases import CASES, case_by_id
from text_web_search_ops import collect_source_urls, has_search_evidence, usage_cost_usd


def _source_event(url: str) -> dict:
    return {"event": {"type": "source", "data": {"source": {"url": url}}}}


def _action_event(action: str, description: str = "") -> dict:
    return {"event": {"data": {"action": action, "description": description}}}


def _result(*, text: str, usage: dict | None = None, events: list | None = None, status: int = 200) -> dict:
    return {"status": status, "text": text, "usage": usage or {}, "events": events or [], "blob": "", "error": ""}


class EvalScoringTests(unittest.TestCase):
    def test_case_ids_match_plan(self) -> None:
        self.assertEqual(
            [case["id"] for case in CASES],
            ["freshness", "official", "url_fetch", "conflict", "zh_synth", "idle"],
        )

    def test_collect_source_urls_and_cost(self) -> None:
        events = [_source_event("https://www.anthropic.com/pricing"), _action_event("web_search", "Searching")]
        self.assertEqual(collect_source_urls(events), ["https://www.anthropic.com/pricing"])
        self.assertEqual(usage_cost_usd({"cost": 0.07}), 0.07)
        self.assertEqual(usage_cost_usd({"cost_details": {"upstream_inference_cost": 0.02}}), 0.02)

    def test_freshness_requires_hard_search_evidence(self) -> None:
        case = case_by_id("freshness")
        memory = score_case(
            case,
            _result(text="OpenAI announced something. https://openai.com/news"),
            model_id=f"{PIPE}.x-ai.grok-4.6",
        )
        self.assertFalse(memory["searched"])
        self.assertFalse(memory["search_ok"])
        self.assertFalse(memory["passed"])

        live = score_case(
            case,
            _result(
                text="OpenAI announced something. https://openai.com/news",
                usage={"server_tool_use": {"web_search_requests": 2}, "cost": 0.04},
                events=[_source_event("https://openai.com/news")],
            ),
            model_id=f"{PIPE}.x-ai.grok-4.6",
        )
        self.assertTrue(live["searched"])
        self.assertTrue(live["passed"])
        self.assertFalse(live["over_cost_cap"])

    def test_idle_fails_on_search_events(self) -> None:
        case = case_by_id("idle")
        ok = score_case(case, _result(text="391. Multiply 17 by 23."), model_id=f"{PIPE}.openai.gpt-5.6-sol")
        self.assertTrue(ok["passed"])
        bad = score_case(
            case,
            _result(
                text="391",
                usage={"server_tool_use": {"web_search_requests": 1}},
                events=[_action_event("web_search")],
            ),
            model_id=f"{PIPE}.openai.gpt-5.6-sol",
        )
        self.assertFalse(bad["passed"])

    def test_anthropic_fetch_accepts_search_plus_quote(self) -> None:
        case = case_by_id("url_fetch")
        row = score_case(
            case,
            _result(
                text="The :online variant is deprecated. https://openrouter.ai/docs/guides/features/server-tools/web-search",
                usage={"server_tool_use": {"web_search_requests": 1}},
                events=[_action_event("web_search")],
            ),
            model_id=f"{PIPE}.anthropic.claude-opus-5",
        )
        self.assertFalse(row["fetched"])
        self.assertTrue(row["anthropic_fetch_ok"])
        self.assertTrue(row["fetch_ok"])
        self.assertTrue(row["passed"])

        grok = score_case(
            case,
            _result(
                text="The :online variant is deprecated. https://openrouter.ai/docs/guides/features/server-tools/web-search",
                usage={"server_tool_use": {"web_search_requests": 1}},
                events=[_action_event("web_search")],
            ),
            model_id=f"{PIPE}.x-ai.grok-4.6",
        )
        self.assertFalse(grok["fetch_ok"])

    def test_fetch_hard_evidence_passes_non_anthropic(self) -> None:
        case = case_by_id("url_fetch")
        row = score_case(
            case,
            _result(
                text="Quote: the :online variant is deprecated. https://openrouter.ai/docs/guides/features/server-tools/web-search",
                usage={"server_tool_use": {"web_fetch_requests": 1, "tool_calls_executed": 1}},
                events=[_action_event("web_fetch", "Fetching web page…")],
            ),
            model_id=f"{PIPE}.google.gemini-3.8-flash",
        )
        self.assertTrue(row["fetched"])
        self.assertTrue(row["passed"])

    def test_zh_and_conflict(self) -> None:
        zh = score_case(
            case_by_id("zh_synth"),
            _result(
                text="官方不再推荐 :online。文档：https://openrouter.ai/docs/guides/features/server-tools/web-search",
                events=[_action_event("web_search"), _source_event("https://openrouter.ai/docs/guides/features/server-tools/web-search")],
                usage={"server_tool_use": {"web_search_requests": 1}},
            ),
            model_id=f"{PIPE}.google.gemini-3.1-pro-preview",
        )
        self.assertTrue(zh["chinese_ok"])
        self.assertTrue(zh["passed"])

        conflict = score_case(
            case_by_id("conflict"),
            _result(
                text=(
                    "Official docs say :online is deprecated. "
                    "A blog still recommends it; they disagree. "
                    "https://openrouter.ai/docs/guides/features/server-tools/web-search "
                    "https://example.com/blog"
                ),
                events=[_source_event("https://openrouter.ai/docs/guides/features/server-tools/web-search")],
                usage={"server_tool_use": {"web_search_requests": 2}},
            ),
            model_id=f"{PIPE}.openai.gpt-5.6-sol-pro",
        )
        self.assertTrue(conflict["conflict_ok"])
        self.assertTrue(conflict["passed"])

    def test_recommend_bands(self) -> None:
        self.assertEqual(
            recommend_next_step({"auto_search_rate": 0.4, "idle_false_positive_rate": 0.0, "citation_rate": 0.8, "cost_over_cap_rate": 0.0})["choice"],
            "controller",
        )
        self.assertEqual(
            recommend_next_step({"auto_search_rate": 0.8, "idle_false_positive_rate": 0.0, "citation_rate": 0.8, "cost_over_cap_rate": 0.5})["choice"],
            "tune_thresholds",
        )
        self.assertEqual(
            recommend_next_step({"auto_search_rate": 0.8, "idle_false_positive_rate": 0.0, "citation_rate": 0.6, "cost_over_cap_rate": 0.0})["choice"],
            "filter_guidance",
        )
        self.assertEqual(
            recommend_next_step({"auto_search_rate": 0.8, "idle_false_positive_rate": 0.0, "citation_rate": 0.9, "cost_over_cap_rate": 0.0})["choice"],
            "hold",
        )

    def test_summarize_counts_idle_false_positives(self) -> None:
        rows = [
            {
                "case_id": "freshness",
                "model_id": "m",
                "searched": True,
                "fetched": False,
                "citation_ok": True,
                "domain_ok": True,
                "fetch_ok": True,
                "passed": True,
                "over_cost_cap": False,
                "cost_usd": 0.01,
            },
            {
                "case_id": "official",
                "model_id": "m",
                "searched": False,
                "fetched": False,
                "citation_ok": False,
                "domain_ok": False,
                "fetch_ok": True,
                "passed": False,
                "over_cost_cap": False,
                "cost_usd": 0.01,
            },
            {
                "case_id": "conflict",
                "model_id": "m",
                "searched": True,
                "fetched": False,
                "citation_ok": True,
                "domain_ok": True,
                "fetch_ok": True,
                "passed": True,
                "over_cost_cap": False,
                "cost_usd": 0.01,
            },
            {
                "case_id": "zh_synth",
                "model_id": "m",
                "searched": True,
                "fetched": False,
                "citation_ok": True,
                "domain_ok": True,
                "fetch_ok": True,
                "passed": True,
                "over_cost_cap": False,
                "cost_usd": 0.01,
            },
            {
                "case_id": "url_fetch",
                "model_id": "m",
                "searched": False,
                "fetched": True,
                "citation_ok": True,
                "domain_ok": True,
                "fetch_ok": True,
                "passed": True,
                "over_cost_cap": False,
                "cost_usd": 0.02,
            },
            {
                "case_id": "idle",
                "model_id": "m",
                "searched": True,
                "fetched": False,
                "citation_ok": True,
                "domain_ok": True,
                "fetch_ok": True,
                "passed": False,
                "over_cost_cap": False,
                "cost_usd": 0.01,
            },
        ]
        summary = summarize(rows)
        self.assertEqual(summary["auto_search_rate"], 0.75)
        self.assertEqual(summary["idle_false_positive_rate"], 1.0)
        self.assertEqual(summary["recommendation"]["choice"], "controller")

    def test_has_search_evidence_ignores_bare_https_in_text(self) -> None:
        result = _result(text="See https://example.com")
        self.assertFalse(has_search_evidence(result))


if __name__ == "__main__":
    unittest.main()
