"""Compact oversized replayed tool/page text. No model allowlist.

Only function_call_output items before the last user message are compacted.
Current-turn tool pages stay full. Reasoning and assistant answers are never
touched. Used by the Pipe sanitizer and unit tests.
"""

from __future__ import annotations

import re
from typing import Any

SEARCH_PAGE_COMPACT_V1 = "SEARCH_PAGE_COMPACT_V1"
COMPACT_AFTER_CHARS = 2500
EXCERPT_CHARS = 900
MAX_URLS = 8
_URL_RE = re.compile(r"https?://[^\s\]\)\"']+", re.I)
_COMPACT_PREFIX = "[compacted source]"


def extract_urls(text: str) -> list[str]:
    seen: list[str] = []
    for match in _URL_RE.findall(text or ""):
        url = match.rstrip(".,;:)")
        if url not in seen:
            seen.append(url)
        if len(seen) >= MAX_URLS:
            break
    return seen


def compact_tool_output_text(text: str) -> str:
    if not isinstance(text, str) or len(text) <= COMPACT_AFTER_CHARS:
        return text
    if text.startswith(_COMPACT_PREFIX):
        return text
    excerpt = text[:EXCERPT_CHARS]
    if " " in excerpt:
        excerpt = excerpt.rsplit(" ", 1)[0]
    urls = extract_urls(text)
    parts = [_COMPACT_PREFIX, excerpt.strip()]
    if urls:
        parts.append("URLs: " + " ".join(urls))
    return "\n".join(parts)


def _is_user_item(item: dict[str, Any]) -> bool:
    if item.get("role") == "user":
        return True
    return item.get("type") == "message" and item.get("role") == "user"


def apply_search_page_compaction(items: list[Any]) -> int:
    """Mutate old oversized function_call_output pages. Returns items changed."""
    if not isinstance(items, list):
        return 0
    last_user = -1
    for index, item in enumerate(items):
        if isinstance(item, dict) and _is_user_item(item):
            last_user = index
    changed = 0
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        if last_user >= 0 and index >= last_user:
            continue
        if item.get("type") != "function_call_output":
            continue
        text = item.get("output")
        if not isinstance(text, str):
            continue
        compacted = compact_tool_output_text(text)
        if compacted == text:
            continue
        item["output"] = compacted
        changed += 1
    return changed


def compact_search_pages(body: dict[str, Any] | None) -> int:
    """Compact body['input'] in place. No-op when input is missing."""
    if not isinstance(body, dict):
        return 0
    items = body.get("input")
    if not isinstance(items, list):
        return 0
    return apply_search_page_compaction(items)
