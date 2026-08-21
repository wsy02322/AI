#!/usr/bin/env python3
"""S2′: retry-strip cross-model encrypted reasoning in the OpenRouter Pipe.

Does NOT change PERSIST_REASONING_TOKENS (same-model replay stays on).
Does NOT strip on every request (that would equal persist=disabled).
Merge-safe: content-only Function update; never touches valves / API_KEY.

Landing (agreed S2′, refined for Pipe having no per-message producer model):
  Expand _should_retry_dropping_signed_reasoning so a 400 or 404 whose text
  contains the OpenRouter cross-model phrases triggers the existing
  _strip_replayed_reasoning() + one internal retry.

  Why retry-only, not "if multi-model then strip first":
  In a compare chat both columns are "multi-model". Proactive strip would
  also drop Grok's own ciphertext when Grok continues — tax on the column
  that OpenRouter would have accepted. Retry only fires on the column that
  actually got rejected.
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

MARKER = "COMPARE_CROSS_MODEL_REASONING_V1"

OLD_RETRY = '''        if getattr(error, "status", None) != 400:
            return False
        target_model = getattr(responses_body, "api_model", None)
        if not (isinstance(target_model, str) and target_model.strip()):
            target_model = str(getattr(responses_body, "model", "") or "")
        if not _is_anthropic_model_id(target_model):
            return False
        message_candidates = [
            error.upstream_message,
            error.openrouter_message,
            str(error),
        ]
        is_signature_error = False
        for message in message_candidates:
            if not isinstance(message, str):
                continue
            lowered = message.lower()
            if ("signature" in lowered and "thinking" in lowered) or (
                "thinking block" in lowered and "cannot be modified" in lowered
            ):
                is_signature_error = True
                break
        if not is_signature_error:
            return False
'''

NEW_RETRY = '''        # COMPARE_CROSS_MODEL_REASONING_V1
        # OpenRouter binds encrypted reasoning to the producing endpoint.
        # Streaming wrappers may report status 400 even when the HTTP status was 404.
        status = getattr(error, "status", None)
        if status not in (400, 404):
            return False
        target_model = getattr(responses_body, "api_model", None)
        if not (isinstance(target_model, str) and target_model.strip()):
            target_model = str(getattr(responses_body, "model", "") or "")
        message_candidates = [
            error.upstream_message,
            error.openrouter_message,
            getattr(error, "reason", None),
            str(error),
            getattr(error, "raw_body", None),
        ]
        is_signature_error = False
        is_cross_model_error = False
        for message in message_candidates:
            if not isinstance(message, str):
                continue
            lowered = message.lower()
            if (
                "produced under a different model" in lowered
                or "encrypted reasoning" in lowered
                or "compaction content" in lowered
            ):
                is_cross_model_error = True
                break
            if ("signature" in lowered and "thinking" in lowered) or (
                "thinking block" in lowered and "cannot be modified" in lowered
            ):
                is_signature_error = True
                break
        if is_cross_model_error:
            if not self._strip_replayed_reasoning(responses_body):
                return False
            self.logger.info(
                "Retrying without replayed encrypted reasoning for model '%s' after a cross-model OpenRouter reject (COMPARE_CROSS_MODEL_REASONING_V1).",
                responses_body.model,
            )
            return True
        if not _is_anthropic_model_id(target_model):
            return False
        if not is_signature_error:
            return False
'''


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
    if OLD_RETRY not in content:
        raise SystemExit("retry gate mismatch; abort to avoid corrupting Pipe")
    return content.replace(OLD_RETRY, NEW_RETRY, 1)


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
    print("pipe content updated COMPARE_CROSS_MODEL_REASONING_V1")
    print("API_KEY not touched (content-only update)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
