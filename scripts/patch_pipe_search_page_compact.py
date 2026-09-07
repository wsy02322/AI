#!/usr/bin/env python3
"""T1: compact old function_call_output pages on Pipe outbound input.

No model allowlist. Current-turn pages (after the last user message) stay
full. Reasoning and assistant answers are not touched. Content-only Function
update; never touches valves / API_KEY.

Apply after S2′ / ST-11. Marker already present → no-op.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time

import requests

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
PIPE_ID = "open_webui_openrouter_integration"

MARKER = "SEARCH_PAGE_COMPACT_V1"

OLD_HELPERS = """    return omitted_call_ids


# -- core.errors --------------------------------------------------------------
"""

NEW_HELPERS = '''    return omitted_call_ids


def apply_search_page_compaction(items: list[Any]) -> int:
    """SEARCH_PAGE_COMPACT_V1: shrink old oversized function_call_output pages.

    No model allowlist. Items at/after the last user message stay full.
    Reasoning and assistant answers are never rewritten.
    """
    if not isinstance(items, list):
        return 0
    compact_after = 2500
    excerpt_chars = 900
    max_urls = 8
    prefix = "[compacted source]"
    url_re = re.compile(r"https?://[^\\s\\]\\)\\\"']+", re.I)
    last_user = -1
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        if item.get("role") == "user" or (item.get("type") == "message" and item.get("role") == "user"):
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
        if not isinstance(text, str) or len(text) <= compact_after or text.startswith(prefix):
            continue
        excerpt = text[:excerpt_chars]
        if " " in excerpt:
            excerpt = excerpt.rsplit(" ", 1)[0]
        urls: list[str] = []
        for match in url_re.findall(text):
            url = match.rstrip(".,;:)")
            if url not in urls:
                urls.append(url)
            if len(urls) >= max_urls:
                break
        parts = [prefix, excerpt.strip()]
        if urls:
            parts.append("URLs: " + " ".join(urls))
        item["output"] = "\\n".join(parts)
        changed += 1
    return changed


# -- core.errors --------------------------------------------------------------
'''

OLD_CALL = """    omitted_call_ids = apply_replay_tool_output_budget(
        normalized,
        model_id=model_for_budget,
        logger=pipe.logger,
    )

    validated = _validate_tool_call_pairs(normalized, logger=pipe.logger)
    pairs_changed = validated is not normalized

    if removed or stripped_any or omitted_call_ids or pairs_changed or (items is not original_items) or (sanitized is not items):
"""

NEW_CALL = """    omitted_call_ids = apply_replay_tool_output_budget(
        normalized,
        model_id=model_for_budget,
        logger=pipe.logger,
    )
    # SEARCH_PAGE_COMPACT_V1
    compacted_pages = apply_search_page_compaction(normalized)
    if compacted_pages:
        pipe.logger.debug(
            "Sanitized provider input: compacted %d oversized replayed page(s).",
            compacted_pages,
        )

    validated = _validate_tool_call_pairs(normalized, logger=pipe.logger)
    pairs_changed = validated is not normalized

    if removed or stripped_any or omitted_call_ids or compacted_pages or pairs_changed or (items is not original_items) or (sanitized is not items):
"""

REPLACEMENTS: list[tuple[str, str, str]] = [
    ("helpers", OLD_HELPERS, NEW_HELPERS),
    ("call", OLD_CALL, NEW_CALL),
]


def _login_candidates() -> list[str]:
    candidates: list[str] = []
    for value in (os.environ.get("OPENWEBUI_USERNAME"), os.environ.get("OPENWEBUI_EMAIL")):
        if value and value not in candidates:
            candidates.append(value)
    return candidates


def signin() -> str:
    password = os.environ.get("OPENWEBUI_PASSWORD")
    last = ""
    for ident in _login_candidates():
        resp = requests.post(
            f"{OPENWEBUI_URL}/api/v1/auths/signin",
            json={"email": ident, "password": password},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()["token"]
        last = f"{resp.status_code} {resp.text[:160]}"
        if resp.status_code == 429:
            time.sleep(8)
    raise SystemExit(f"signin failed: {last}")


def patch_content(content: str) -> str:
    if MARKER in content:
        return content
    for name, old, new in REPLACEMENTS:
        count = content.count(old)
        if count != 1:
            raise SystemExit(
                f"hunk {name} mismatch (count={count}); abort to avoid corrupting Pipe"
            )
        content = content.replace(old, new, 1)
    if MARKER not in content:
        raise SystemExit("patch applied but marker missing; abort")
    return content


def content_sha12(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch live Pipe (or --from-file) and patch in memory; do not POST",
    )
    parser.add_argument(
        "--from-file",
        default="",
        help="Patch this file instead of fetching live Pipe content",
    )
    parser.add_argument(
        "--write-patched",
        default="",
        help="With --dry-run, write patched content to this path",
    )
    args = parser.parse_args()

    if args.from_file:
        with open(args.from_file, encoding="utf-8") as fh:
            original = fh.read()
        pipe_name = os.path.basename(args.from_file)
        meta: dict = {}
    else:
        if not OPENWEBUI_URL:
            raise SystemExit("OPENWEBUI_URL missing")
        token = signin()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        fn = requests.get(f"{OPENWEBUI_URL}/api/v1/functions/id/{PIPE_ID}", headers=headers, timeout=60)
        if fn.status_code != 200:
            raise SystemExit(f"get pipe: {fn.status_code} {fn.text[:300]}")
        pipe = fn.json()
        original = pipe["content"]
        pipe_name = pipe.get("name")
        meta = pipe.get("meta") or {}

    new_content = patch_content(original)
    before = content_sha12(original)
    after = content_sha12(new_content)
    print(f"pipe={pipe_name}")
    print(f"sha256[:12] before={before} after={after}")
    print(f"marker={MARKER} present={MARKER in new_content}")
    if new_content == original:
        if MARKER in original:
            print("already patched; no content change")
        else:
            print("no content change")
        return 0
    if args.write_patched:
        with open(args.write_patched, "w", encoding="utf-8") as fh:
            fh.write(new_content)
        print(f"wrote {args.write_patched}")
    if args.dry_run:
        print("dry-run: not POSTing")
        return 0

    token = signin()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/functions/id/{PIPE_ID}/update",
        headers=headers,
        json={
            "id": PIPE_ID,
            "name": pipe_name,
            "meta": meta,
            "content": new_content,
        },
        timeout=180,
    )
    if resp.status_code != 200:
        raise SystemExit(f"update pipe: {resp.status_code} {resp.text[:500]}")
    print("pipe content updated SEARCH_PAGE_COMPACT_V1")
    print("API_KEY not touched (content-only update)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
