#!/usr/bin/env python3
"""Unit tests for ST-14 EVAL-B scoring and runner helpers. No live model calls."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import PIPE, TEXT_WEB_SEARCH_CANARY_MODEL_ID
from run_text_web_search_eval import (
    SUITE_VERSION,
    _select_models,
    _short,
    append_jsonl,
    atomic_write,
    build_manifest,
    expand_jobs,
    final_exit,
    job_key,
    jobs_complete,
    load_jsonl_rows,
    manifest_mismatch,
    recount_hard_errors,
)
from text_web_search_eval import recommend_from_gates, score_case, score_stored_row, summarize_eval_b
from text_web_search_eval_cases import (
    CANARY_CASE_IDS,
    EVAL_B_CASES,
    FETCH_DIAG_CASES,
    V1_CASES,
    case_by_id,
    cases_for_suite,
)
from text_web_search_eval_oracle import FETCH_URL, OracleError, oracle_answer_ok, oracle_fields_in_text
from text_web_search_ops import fetch_called_hard, search_called


def _source_event(url: str) -> dict:
    return {"event": {"type": "source", "data": {"source": {"url": url}}}}


def _action_event(action: str = "", description: str = "", done: bool | None = None) -> dict:
    return {"event": {"data": {"action": action or None, "description": description, "done": done}}}


def _result(*, text: str, usage: dict | None = None, events: list | None = None, status: int = 200) -> dict:
    return {"status": status, "text": text, "usage": usage or {}, "events": events or [], "blob": "", "error": ""}


class EvalBTests(unittest.TestCase):
    def test_suites_and_canary_ids(self) -> None:
        self.assertEqual([case["id"] for case in V1_CASES], ["freshness", "official", "url_fetch", "conflict", "zh_synth", "idle"])
        self.assertEqual(len(EVAL_B_CASES), 6)
        self.assertEqual(sum(int(case["repeats"]) for case in EVAL_B_CASES), 10)
        self.assertEqual(cases_for_suite("eval-b")[0]["id"], "implicit_openai_week")
        self.assertTrue(set(CANARY_CASE_IDS) <= {case["id"] for case in EVAL_B_CASES})
        self.assertEqual(len(FETCH_DIAG_CASES), 6)
        self.assertEqual(SUITE_VERSION["eval-b"], "eval-b-v2")

    def test_implicit_prompts_avoid_instruction_words(self) -> None:
        forbidden = ("请搜索", "引用来源", "给 URL", "查官网", "source URL", "official website")
        for case in EVAL_B_CASES:
            if case["family"] != "implicit_freshness":
                continue
            for needle in forbidden:
                self.assertNotIn(needle, case["prompt"], case["id"])

    def test_source_url_is_not_search(self) -> None:
        result = _result(text="see https://example.com", events=[_source_event("https://example.com")])
        self.assertFalse(search_called(result))
        implicit = score_case(case_by_id("implicit_openai_week"), result, model_id=f"{PIPE}.x-ai.grok-4.6")
        self.assertFalse(implicit["search_called"])
        self.assertFalse(implicit["search_ok"])
        self.assertFalse(implicit["passed"])

    def test_bare_https_in_text_is_not_search(self) -> None:
        self.assertFalse(search_called(_result(text="See https://example.com")))

    def test_search_usage_or_action_counts(self) -> None:
        usage = _result(text="x", usage={"server_tool_use": {"web_search_requests": 1}})
        action = _result(text="x", events=[_action_event("web_search", "Searching")])
        self.assertTrue(search_called(usage))
        self.assertTrue(search_called(action))

    def test_fetch_soft_vs_hard(self) -> None:
        soft = _result(text="x", events=[_action_event("", "Fetching web page…", done=False)])
        hard = _result(
            text="x",
            usage={"server_tool_use": {"web_fetch_requests": 1}},
            events=[_action_event("web_fetch", "Fetching web page…", done=True)],
        )
        self.assertFalse(fetch_called_hard(soft))
        self.assertTrue(fetch_called_hard(hard))

    def test_conflict_needs_two_domains_and_disagreement(self) -> None:
        case = case_by_id("conflict")
        fake = score_case(
            case,
            _result(
                text="The :online variant is deprecated. https://openrouter.ai/docs/guides/features/server-tools/web-search",
                usage={"server_tool_use": {"web_search_requests": 1}},
                events=[_action_event("web_search"), _source_event("https://openrouter.ai/docs/guides/features/server-tools/web-search")],
            ),
            model_id=f"{PIPE}.openai.gpt-5.6-sol",
        )
        self.assertFalse(fake["conflict_ok"])
        self.assertFalse(fake["passed"])

        good = score_case(
            case,
            _result(
                text=(
                    "Official docs and a blog disagree. "
                    "https://openrouter.ai/docs/guides/features/server-tools/web-search "
                    "https://example.com/old-guide"
                ),
                usage={"server_tool_use": {"web_search_requests": 2}},
                events=[
                    _action_event("web_search"),
                    _source_event("https://openrouter.ai/docs/guides/features/server-tools/web-search"),
                    _source_event("https://example.com/old-guide"),
                ],
            ),
            model_id=f"{PIPE}.openai.gpt-5.6-sol",
        )
        self.assertTrue(good["conflict_ok"])
        self.assertTrue(good["passed"])

    def test_score_stored_conflict_row(self) -> None:
        row = score_stored_row(
            case_by_id("conflict"),
            {
                "status": 200,
                "model_id": f"{PIPE}.x-ai.grok-4.6",
                "web_search_requests": 1,
                "text_excerpt": "The :online variant is deprecated. https://openrouter.ai/docs",
                "source_urls": ["https://openrouter.ai/docs"],
                "text_urls": ["https://openrouter.ai/docs"],
                "actions": [{"action": "web_search"}],
            },
        )
        self.assertFalse(row["conflict_ok"])

    def test_control_fails_on_search_or_soft_fetch(self) -> None:
        case = case_by_id("control_eternal")
        ok = score_case(case, _result(text="2x. Power rule."), model_id=f"{PIPE}.openai.gpt-5.6-sol")
        self.assertTrue(ok["passed"])
        bad = score_case(
            case,
            _result(text="2x", usage={"server_tool_use": {"web_search_requests": 1}}, events=[_action_event("web_search")]),
            model_id=f"{PIPE}.openai.gpt-5.6-sol",
        )
        self.assertFalse(bad["passed"])

    def test_dynamic_fetch_uses_oracle_not_prompt_leak(self) -> None:
        case = case_by_id("fetch_github_latest")
        oracle = {
            "url": FETCH_URL,
            "tag_name": "v0.6.43",
            "published_at": "2026-09-01T12:00:00Z",
            "published_day": "2026-09-01",
        }
        wrong = score_case(
            case,
            _result(text=f"I read {FETCH_URL} and the tag is v0.1.0 published 2020-01-01."),
            model_id=f"{PIPE}.google.gemini-3.8-flash",
            oracle=oracle,
        )
        self.assertFalse(wrong["answer_ok"])
        self.assertTrue(wrong["url_ok"])
        self.assertFalse(wrong["passed"])

        quoted = score_case(
            case,
            _result(
                text=f"tag_name=v0.6.43 published_at=2026-09-01T12:00:00Z {FETCH_URL}",
                events=[_action_event("web_fetch", "Fetching web page…", done=True)],
                usage={"server_tool_use": {"web_fetch_requests": 1}},
            ),
            model_id=f"{PIPE}.google.gemini-3.8-flash",
            oracle=oracle,
        )
        self.assertTrue(quoted["answer_ok"])
        self.assertTrue(quoted["passed"])

    def test_anthropic_fetch_telemetry_unknown_does_not_fake_hard_fetch(self) -> None:
        case = case_by_id("fetch_github_latest")
        oracle = {
            "url": FETCH_URL,
            "tag_name": "v0.6.43",
            "published_at": "2026-09-01T12:00:00Z",
            "published_day": "2026-09-01",
        }
        row = score_case(
            case,
            _result(text=f"tag_name v0.6.43 published_at 2026-09-01T12:00:00Z {FETCH_URL}"),
            model_id=f"{PIPE}.anthropic.claude-opus-5",
            oracle=oracle,
        )
        self.assertTrue(row["answer_ok"])
        self.assertFalse(row["fetch_called_hard"])
        self.assertTrue(row["telemetry_unobservable"])
        self.assertTrue(row["passed"])

    def test_oracle_requires_exact_rfc3339_and_tag_token(self) -> None:
        oracle = {
            "url": FETCH_URL,
            "tag_name": "v0.11.3",
            "published_at": "2026-08-31T14:55:53Z",
            "published_day": "2026-08-31",
        }
        self.assertTrue(
            oracle_answer_ok(
                'tag_name="v0.11.3" published_at="2026-08-31T14:55:53Z"',
                oracle,
            )
        )
        self.assertFalse(oracle_answer_ok("tag v0.11.3 on 2026-08-31", oracle))
        self.assertFalse(oracle_answer_ok('published_at="2026-08-31T14:55:00Z" tag v0.11.3', oracle))
        self.assertFalse(oracle_fields_in_text("latest is v0.11.30", oracle)["tag_ok"])
        self.assertTrue(oracle_fields_in_text("latest is v0.11.3,", oracle)["tag_ok"])
        self.assertTrue(oracle_fields_in_text(f"see {FETCH_URL}", oracle)["url_ok"])

        case = case_by_id("fetch_github_latest")
        approx = score_case(
            case,
            _result(text=f"tag_name v0.11.3 published_at 2026-08-31T14:55:00Z {FETCH_URL}"),
            model_id=f"{PIPE}.anthropic.claude-opus-5",
            oracle=oracle,
        )
        self.assertFalse(approx["answer_ok"])
        self.assertFalse(approx["passed"])
        self.assertFalse(approx["fetch_reported_failure"])

    def test_fetch_reported_failure_is_not_transport(self) -> None:
        case = case_by_id("fetch_github_latest")
        oracle = {
            "url": FETCH_URL,
            "tag_name": "v0.11.3",
            "published_at": "2026-08-31T14:55:53Z",
            "published_day": "2026-08-31",
        }
        row = score_case(
            case,
            _result(text=f"I was unable to fetch {FETCH_URL} — the request failed."),
            model_id=f"{PIPE}.anthropic.claude-opus-5",
            oracle=oracle,
        )
        self.assertTrue(row["ok_http"])
        self.assertTrue(row["chat_transport_ok"])
        self.assertTrue(row["fetch_reported_failure"])
        self.assertFalse(row["fetch_called_hard"])
        self.assertFalse(row["answer_ok"])
        self.assertFalse(row["passed"])

    def test_oracle_helpers(self) -> None:
        oracle = {
            "url": FETCH_URL,
            "tag_name": "v1.2.3",
            "published_at": "2026-02-03T00:00:00Z",
            "published_day": "2026-02-03",
        }
        self.assertTrue(oracle_answer_ok("release v1.2.3 on 2026-02-03T00:00:00Z", oracle))
        self.assertFalse(oracle_answer_ok("release 1.2.3 on 2026-02-03", oracle))
        self.assertTrue(oracle_fields_in_text(f"see {FETCH_URL}", oracle)["url_ok"])

    def test_request_cost_is_not_a_tool_cap_verdict(self) -> None:
        row = score_case(
            case_by_id("implicit_openai_week"),
            _result(text="news", usage={"server_tool_use": {"web_search_requests": 1}, "cost": 0.2}, events=[_action_event("web_search")]),
            model_id=f"{PIPE}.x-ai.grok-4.6",
        )
        self.assertEqual(row["request_total_cost_usd"], 0.2)
        self.assertNotIn("over_cost_cap", row)
        summary = summarize_eval_b([row])
        self.assertNotIn("cost_over_cap_rate", summary)
        self.assertEqual(summary["cost"]["p50"], 0.2)
        self.assertNotEqual(summary["recommendation"]["choice"], "tune_thresholds")

    def test_gates_and_recommendation(self) -> None:
        self.assertEqual(recommend_from_gates({"implicit_freshness": "green", "dynamic_fetch": "green", "no_search_control": "green"})["choice"], "hold")
        self.assertEqual(recommend_from_gates({"implicit_freshness": "green", "dynamic_fetch": "red", "no_search_control": "green"})["choice"], "diagnose_fetch")
        self.assertEqual(recommend_from_gates({"implicit_freshness": "green", "dynamic_fetch": "yellow", "no_search_control": "green"})["choice"], "diagnose_fetch")
        self.assertEqual(recommend_from_gates({"implicit_freshness": "yellow", "dynamic_fetch": "green", "no_search_control": "green"})["choice"], "provider_guidance")
        self.assertEqual(recommend_from_gates({"implicit_freshness": "red", "dynamic_fetch": "green", "no_search_control": "green"})["choice"], "controller_or_guidance")

    def test_summarize_counts_implicit_and_controls(self) -> None:
        implicit_rows = []
        for i in range(42):
            implicit_rows.append(
                {
                    "family": "implicit_freshness",
                    "suite": "eval-b",
                    "model_id": f"m{i % 7}",
                    "search_ok": i < 38,
                    "passed": i < 38,
                    "request_total_cost_usd": 0.02,
                }
            )
        controls = [{"family": "no_search_control", "model_id": "m0", "search_ok": True, "passed": True, "request_total_cost_usd": 0.01}] * 21
        fetches = [
            {
                "family": "dynamic_fetch",
                "model_id": "m0",
                "answer_ok": True,
                "url_ok": True,
                "ok_http": True,
                "passed": True,
                "telemetry_unobservable": False,
                "request_total_cost_usd": 0.01,
            }
        ] * 14
        summary = summarize_eval_b(implicit_rows + controls + fetches)
        self.assertEqual(summary["gates"]["implicit_freshness"], "green")
        self.assertEqual(summary["gates"]["no_search_control"], "green")
        self.assertEqual(summary["gates"]["dynamic_fetch"], "green")
        self.assertEqual(summary["chat_transport_ok"], 14)
        self.assertNotIn("fetch_http_ok", summary)
        self.assertEqual(summary["fetch_hard_evidence"], 0)

        fetches_red = [{**row, "answer_ok": False} for row in fetches[:4]] + fetches[4:]
        red = summarize_eval_b(implicit_rows + controls + fetches_red)
        self.assertEqual(red["oracle_answer_ok"], 10)
        self.assertEqual(red["gates"]["dynamic_fetch"], "red")
        self.assertEqual(red["recommendation"]["choice"], "diagnose_fetch")

    def test_model_selector_and_jobs(self) -> None:
        self.assertEqual(_short(TEXT_WEB_SEARCH_CANARY_MODEL_ID), "gemini-3.8-flash")
        self.assertEqual(_select_models("gemini-3.8-flash", suite="eval-b")[0], TEXT_WEB_SEARCH_CANARY_MODEL_ID)
        jobs = expand_jobs(
            [TEXT_WEB_SEARCH_CANARY_MODEL_ID],
            [case_by_id("implicit_openai_week"), case_by_id("control_rewrite")],
            seed=14,
            canary=True,
        )
        self.assertEqual(len(jobs), 2)
        self.assertEqual({job_key(m, c["id"], r) for m, c, r in jobs}, {
            job_key(TEXT_WEB_SEARCH_CANARY_MODEL_ID, "implicit_openai_week", 0),
            job_key(TEXT_WEB_SEARCH_CANARY_MODEL_ID, "control_rewrite", 0),
        })

    def test_atomic_write_and_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.json"
            atomic_write(path, {"ok": True})
            self.assertTrue(json.loads(path.read_text())["ok"])
            self.assertFalse(path.with_name("out.json.tmp").exists())
        self.assertEqual(final_exit(hard_errors=1, complete=True, strict=False, gates={"x": "green"}), 2)
        self.assertEqual(final_exit(hard_errors=0, complete=False, strict=False, gates={"x": "green"}), 2)
        self.assertEqual(final_exit(hard_errors=0, complete=True, strict=True, gates={"x": "yellow"}), 1)
        self.assertEqual(final_exit(hard_errors=0, complete=True, strict=False, gates={"x": "yellow"}), 0)

    def test_resume_recounts_hard_errors_and_rejects_bad_manifest(self) -> None:
        rows = [
            {"model_id": "m0", "case_id": "a", "repeat_id": 0, "ok_http": False, "chat_transport_ok": False},
            {"model_id": "m0", "case_id": "b", "repeat_id": 0, "ok_http": True, "chat_transport_ok": True},
        ]
        self.assertEqual(recount_hard_errors(rows), 1)
        self.assertTrue(jobs_complete(rows, ["m0|a|0", "m0|b|0"]))
        self.assertFalse(jobs_complete(rows, ["m0|a|0", "m0|b|0", "m0|c|0"]))
        expected = build_manifest(
            suite="eval-b",
            seed=14,
            models=["m0"],
            cases=[{"id": "a"}, {"id": "b"}],
            jobs=[("m0", {"id": "a"}, 0), ("m0", {"id": "b"}, 0)],
            filter_sha="abc123abc123",
        )
        self.assertIsNone(manifest_mismatch(expected, expected))
        bad = dict(expected)
        bad["suite_version"] = "eval-b"
        self.assertEqual(manifest_mismatch(bad, expected), "manifest suite_version mismatch")
        self.assertEqual(manifest_mismatch(None, expected), "missing campaign manifest")

    def test_jsonl_ignores_trailing_incomplete_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rows.jsonl"
            append_jsonl(path, {"id": 1})
            with path.open("a", encoding="utf-8") as handle:
                handle.write('{"id": 2, "broken"')
            rows = load_jsonl_rows(path)
            self.assertEqual(rows, [{"id": 1}])

    def test_oracle_error_stops_before_model(self) -> None:
        with patch("text_web_search_eval_oracle.requests.get") as mocked:
            mocked.return_value.status_code = 403
            mocked.return_value.text = "rate limited"
            from text_web_search_eval_oracle import fetch_github_latest_oracle

            with self.assertRaises(OracleError):
                fetch_github_latest_oracle()


if __name__ == "__main__":
    unittest.main()
