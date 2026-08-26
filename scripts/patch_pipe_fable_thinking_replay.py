#!/usr/bin/env python3
"""Fable / Anthropic same-model follow-up: persist ciphertext, strip unsigned summaries.

Root cause: Pipe emitted summary-only reasoning items (no signature / encrypted_content).
OWUI replayed them as thinking blocks → OpenRouter/Anthropic 400:
  thinking or redacted_thinking blocks in the latest assistant message cannot be modified.

Does NOT change PERSIST_REASONING_TOKENS (same-model replay stays on).
Merge-safe: content-only Function update; never touches valves / API_KEY.

Landing (agreed A+A′+B+C):
  A  Copy encrypted_content / signature / reasoning_details onto emitted reasoning items.
  A′ Request include=["reasoning.encrypted_content"] on /responses.
  B  Treat summary-only / unsigned reasoning as unreplayable (strip all-or-nothing).
  C  Retry gate matches `thinking` / `redacted_thinking` + cannot be modified.

Keep COMPARE_CROSS_MODEL_REASONING_V1 intact. Apply this after S2′ on a fresh Pipe.
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

MARKER = "FABLE_UNSIGNED_SUMMARY_V1"

OLD_UNSIGNED = '''def _reasoning_item_unsigned(item: dict[str, Any]) -> bool:
    """True for a /responses reasoning item that is plaintext thinking with no
    signature and no encrypted payload -- unreplayable to Anthropic."""
    if _clean_str(item.get("signature")) or _clean_str(item.get("encrypted_content")):
        return False
    content = item.get("content")
    if not isinstance(content, list):
        return False
    has_text = False
    for part in content:
        if not isinstance(part, dict):
            continue
        if _clean_str(part.get("signature")) or _clean_str(part.get("encrypted_content")):
            return False
        if part.get("type") == "reasoning_text" and isinstance(part.get("text"), str) and part["text"].strip():
            has_text = True
    return has_text
'''

NEW_UNSIGNED = '''def _reasoning_crypto_fields(item: Any) -> dict[str, Any]:
    """Copy replayable reasoning ciphertext/signature off a provider item.
    FABLE_UNSIGNED_SUMMARY_V1.
    """
    if not isinstance(item, dict):
        return {}
    carried: dict[str, Any] = {}
    for key in ("encrypted_content", "signature", "format"):
        val = item.get(key)
        if isinstance(val, str) and val.strip():
            carried[key] = val
    details = item.get("reasoning_details")
    if isinstance(details, list) and details:
        carried["reasoning_details"] = details
    return carried


def _reasoning_item_unsigned(item: dict[str, Any]) -> bool:
    """True for a /responses reasoning item that is plaintext thinking with no
    signature and no encrypted payload -- unreplayable to Anthropic."""
    # FABLE_UNSIGNED_SUMMARY_V1: summary-only items (no content list) are still
    # thinking blocks; treating them as signed caused Anthropic 400
    # "thinking or redacted_thinking blocks ... cannot be modified".
    if _clean_str(item.get("signature")) or _clean_str(item.get("encrypted_content")):
        return False
    content = item.get("content")
    if isinstance(content, list):
        for part in content:
            if not isinstance(part, dict):
                continue
            if _clean_str(part.get("signature")) or _clean_str(part.get("encrypted_content")):
                return False
    return True
'''

OLD_RETRY_MATCH = '''            if ("signature" in lowered and "thinking" in lowered) or (
                "thinking block" in lowered and "cannot be modified" in lowered
            ):
                is_signature_error = True
                break
'''

NEW_RETRY_MATCH = '''            if (
                ("signature" in lowered and "thinking" in lowered)
                or (
                    "cannot be modified" in lowered
                    and ("thinking" in lowered or "redacted_thinking" in lowered)
                )
            ):
                # FABLE_UNSIGNED_SUMMARY_V1: match `thinking` / `redacted_thinking`
                # blocks, not only the singular phrase "thinking block".
                is_signature_error = True
                break
'''

OLD_INCLUDE = '''def apply_context_transforms(responses_body: "ResponsesBody", *, auto_context_trimming: bool) -> None:
    """Set context trimming fields when not already explicitly configured."""
    if not auto_context_trimming:
'''

NEW_INCLUDE = '''def _ensure_reasoning_encrypted_include(responses_body: "ResponsesBody") -> None:
    """Ask OpenRouter /responses for replayable reasoning ciphertext.
    FABLE_UNSIGNED_SUMMARY_V1.
    """
    existing = getattr(responses_body, "include", None)
    include = [entry for entry in existing if isinstance(entry, str)] if isinstance(existing, list) else []
    if "reasoning.encrypted_content" not in include:
        include.append("reasoning.encrypted_content")
    responses_body.include = include


def apply_context_transforms(responses_body: "ResponsesBody", *, auto_context_trimming: bool) -> None:
    """Set context trimming fields when not already explicitly configured."""
    _ensure_reasoning_encrypted_include(responses_body)
    if not auto_context_trimming:
'''

OLD_CRYPTO_BUF = '''        reasoning_stream_buffers: dict[str, str] = {}
        reasoning_stream_completed: set[str] = set()
        reasoning_display: dict[str, dict[str, Any]] = {}
'''

NEW_CRYPTO_BUF = '''        reasoning_stream_buffers: dict[str, str] = {}
        reasoning_stream_completed: set[str] = set()
        reasoning_display: dict[str, dict[str, Any]] = {}
        reasoning_crypto_by_id: dict[str, dict[str, Any]] = {}
'''

OLD_EMIT_ITEM = '''            await event_emitter(
                {
                    "type": "response.output_item.added",
                    "item": {
                        "type": "reasoning",
                        "id": item_id,
                        "summary": [{"type": "summary_text", "text": text}],
                        "status": "completed",
                        "started_at": state["wall_open"],
                        "ended_at": time.time(),
                        "duration": duration,
                    },
                }
            )
'''

NEW_EMIT_ITEM = '''            item: dict[str, Any] = {
                "type": "reasoning",
                "id": item_id,
                "summary": [{"type": "summary_text", "text": text}],
                "status": "completed",
                "started_at": state["wall_open"],
                "ended_at": time.time(),
                "duration": duration,
            }
            crypto = reasoning_crypto_by_id.get(item_id) or reasoning_crypto_by_id.get(key)
            if crypto:
                item.update(crypto)
            await event_emitter(
                {
                    "type": "response.output_item.added",
                    "item": item,
                }
            )
'''

OLD_ADDED_REASONING = '''                        if item_type == "reasoning":
                            iid = item.get("id")
                            if isinstance(iid, str) and iid:
                                active_reasoning_item_id = iid
                            continue
'''

NEW_ADDED_REASONING = '''                        if item_type == "reasoning":
                            iid = item.get("id")
                            if isinstance(iid, str) and iid:
                                active_reasoning_item_id = iid
                            crypto = _reasoning_crypto_fields(item)
                            if crypto and isinstance(iid, str) and iid:
                                reasoning_crypto_by_id.setdefault(iid, {}).update(crypto)
                            continue
'''

OLD_DONE_REASONING = '''                        if item_type == "reasoning":
                            should_persist = valves.PERSIST_REASONING_TOKENS in {"next_reply", "conversation"}
'''

NEW_DONE_REASONING = '''                        if item_type == "reasoning":
                            crypto = _reasoning_crypto_fields(item)
                            rid = item.get("id")
                            if crypto and isinstance(rid, str) and rid:
                                reasoning_crypto_by_id.setdefault(rid, {}).update(crypto)
                            should_persist = valves.PERSIST_REASONING_TOKENS in {"next_reply", "conversation"}
'''

OLD_FINAL_OUTPUT = '''                for item in final_response.get("output", []):
                    item_type = item.get("type")
                    if item_type == "reasoning" and (item.get("encrypted_content") or item.get("signature")):
                        continuation_input_items.append(item)
                        reasoning_count += 1
'''

NEW_FINAL_OUTPUT = '''                for item in final_response.get("output", []):
                    if isinstance(item, dict) and item.get("type") == "reasoning":
                        crypto = _reasoning_crypto_fields(item)
                        rid = item.get("id")
                        if crypto and isinstance(rid, str) and rid:
                            reasoning_crypto_by_id.setdefault(rid, {}).update(crypto)
                    item_type = item.get("type")
                    if item_type == "reasoning" and (item.get("encrypted_content") or item.get("signature")):
                        continuation_input_items.append(item)
                        reasoning_count += 1
'''

REPLACEMENTS: list[tuple[str, str, str]] = [
    ("unsigned", OLD_UNSIGNED, NEW_UNSIGNED),
    ("retry-match", OLD_RETRY_MATCH, NEW_RETRY_MATCH),
    ("include", OLD_INCLUDE, NEW_INCLUDE),
    ("crypto-buf", OLD_CRYPTO_BUF, NEW_CRYPTO_BUF),
    ("emit-item", OLD_EMIT_ITEM, NEW_EMIT_ITEM),
    ("added-reasoning", OLD_ADDED_REASONING, NEW_ADDED_REASONING),
    ("done-reasoning", OLD_DONE_REASONING, NEW_DONE_REASONING),
    ("final-output", OLD_FINAL_OUTPUT, NEW_FINAL_OUTPUT),
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
    print(f"s2_marker=COMPARE_CROSS_MODEL_REASONING_V1 present={'COMPARE_CROSS_MODEL_REASONING_V1' in new_content}")
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
    print("pipe content updated FABLE_UNSIGNED_SUMMARY_V1")
    print("API_KEY not touched (content-only update)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
