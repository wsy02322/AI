"""Natural-language cases for the ST-14 read-only quality baseline."""

from __future__ import annotations

from typing import Any

CASES: list[dict[str, Any]] = [
    {
        "id": "freshness",
        "expect_search": True,
        "expect_fetch": False,
        "prompt": (
            "What official product news did OpenAI announce this week? "
            "Include at least one live source URL."
        ),
    },
    {
        "id": "official",
        "expect_search": True,
        "expect_fetch": False,
        "required_domains": ["anthropic.com"],
        "prompt": (
            "What is the current official API pricing for Claude Opus on Anthropic's own site? "
            "Use anthropic.com sources and include the exact page URL."
        ),
    },
    {
        "id": "url_fetch",
        "expect_search": False,
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
        "expect_search": True,
        "expect_fetch": False,
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
        "expect_search": True,
        "expect_fetch": False,
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
        "expect_search": False,
        "expect_fetch": False,
        "prompt": "What is 17 × 23? Give the product and one short sentence about the arithmetic.",
    },
]


def case_by_id(case_id: str) -> dict[str, Any]:
    for case in CASES:
        if case["id"] == case_id:
            return case
    raise KeyError(case_id)
