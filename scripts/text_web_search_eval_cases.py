"""ST-14 eval cases. v1 is historical; EVAL-B is the correction suite."""

from __future__ import annotations

from typing import Any

from text_web_search_eval_oracle import FETCH_URL

V1_CASES: list[dict[str, Any]] = [
    {
        "id": "freshness",
        "suite": "eval-v1",
        "family": "explicit_search",
        "repeats": 1,
        "expect_search": True,
        "prompt": (
            "What official product news did OpenAI announce this week? "
            "Include at least one live source URL."
        ),
    },
    {
        "id": "official",
        "suite": "eval-v1",
        "family": "explicit_search",
        "repeats": 1,
        "expect_search": True,
        "required_domains": ["anthropic.com"],
        "prompt": (
            "What is the current official API pricing for Claude Opus on Anthropic's own site? "
            "Use anthropic.com sources and include the exact page URL."
        ),
    },
    {
        "id": "url_fetch",
        "suite": "eval-v1",
        "family": "v1_url_fetch",
        "repeats": 1,
        "expect_fetch": True,
        "required_needles": [":online", "deprecated"],
        "required_domains": ["openrouter.ai"],
        "prompt": (
            "Read https://openrouter.ai/docs/guides/features/server-tools/web-search "
            "and quote the sentence that says the :online variant is deprecated."
        ),
    },
    {
        "id": "conflict",
        "suite": "eval-v1",
        "family": "conflict",
        "repeats": 1,
        "expect_search": True,
        "expect_conflict": True,
        "required_domains": ["openrouter.ai"],
        "prompt": (
            "OpenRouter's current docs say the :online model suffix for web search is deprecated. "
            "Some third-party pages still tell people to append :online. "
            "Compare the official OpenRouter documentation with at least one other current page. "
            "If they disagree, say so clearly and cite both URLs."
        ),
    },
    {
        "id": "zh_synth",
        "suite": "eval-v1",
        "family": "explicit_search",
        "repeats": 1,
        "expect_search": True,
        "expect_chinese": True,
        "required_domains": ["openrouter.ai"],
        "prompt": (
            "用中文说明 OpenRouter 现在对网页搜索的官方推荐做法是什么，"
            "还要不要在模型名后面加 :online。"
            "请引用英文官方文档，并在中文回答里保留原文 URL。"
        ),
    },
    {
        "id": "idle",
        "suite": "eval-v1",
        "family": "no_search_control",
        "repeats": 1,
        "prompt": "What is 17 × 23? Give the product and one short sentence about the arithmetic.",
    },
]

EVAL_B_CASES: list[dict[str, Any]] = [
    {
        "id": "implicit_openai_week",
        "suite": "eval-b",
        "family": "implicit_freshness",
        "repeats": 2,
        "prompt": "OpenAI 这周发布了什么重要产品？",
    },
    {
        "id": "implicit_claude_price",
        "suite": "eval-b",
        "family": "implicit_freshness",
        "repeats": 2,
        "prompt": "Claude Opus 现在的 API 输入输出价格是多少？",
    },
    {
        "id": "implicit_or_web",
        "suite": "eval-b",
        "family": "implicit_freshness",
        "repeats": 2,
        "prompt": "OpenRouter 目前推荐怎样给普通聊天模型增加网页搜索？",
    },
    {
        "id": "control_rewrite",
        "suite": "eval-b",
        "family": "no_search_control",
        "repeats": 1,
        "prompt": (
            "Rewrite this paragraph in simpler English, keeping the same facts. "
            "Do not add new facts: Photosynthesis converts light energy into chemical energy "
            "in plants. Chlorophyll absorbs mainly blue and red light. The overall reaction "
            "produces glucose and oxygen from carbon dioxide and water."
        ),
    },
    {
        "id": "control_eternal",
        "suite": "eval-b",
        "family": "no_search_control",
        "repeats": 1,
        "prompt": (
            "What is the derivative of x squared with respect to x? "
            "Answer with the expression and one short sentence."
        ),
    },
    {
        "id": "fetch_github_latest",
        "suite": "eval-b",
        "family": "dynamic_fetch",
        "repeats": 2,
        "needs_oracle": True,
        "prompt": (
            f"Read {FETCH_URL} and report the JSON fields tag_name and published_at "
            "exactly as they appear. Keep the full input URL in your answer."
        ),
    },
]

CASES = V1_CASES
CANARY_CASE_IDS = ("implicit_openai_week", "control_rewrite", "fetch_github_latest")


def cases_for_suite(suite: str) -> list[dict[str, Any]]:
    if suite == "eval-v1":
        return list(V1_CASES)
    if suite == "eval-b":
        return list(EVAL_B_CASES)
    raise KeyError(suite)


def case_by_id(case_id: str) -> dict[str, Any]:
    for case in [*V1_CASES, *EVAL_B_CASES]:
        if case["id"] == case_id:
            return case
    raise KeyError(case_id)
