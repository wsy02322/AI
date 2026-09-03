#!/usr/bin/env python3
"""ST-13: store generated-image data URIs instead of handing them back inline.

Root cause (2026-09-03, error id 77de6621c4ab134c):
  `_materialize_image_entry` returns the string from the dict `url` / `image_url` /
  `imageUrl` / `content_url` keys verbatim, so a provider that answers with
  {"image_url": {"url": "data:image/png;base64,..."}} lands a multi-MB data URI in
  `![Generated image N](...)`. The next turn replays that assistant text verbatim
  (`_append_assistant_text_chunks`), so base64 is billed as text tokens:
    400 INVALID_ARGUMENT The input token count exceeds the maximum ... 131072.

The pipe already stores base64 coming through `b64_json` and through the plain-string
entry point, and its own `_to_input_image` documents that inline payloads are always
saved to storage. This patch closes that inconsistency for the dict `url` branch only.

Storage failure keeps the raw data URI (image stays visible); the paired guard patch
IMAGE_CONTEXT_DATA_URI_CAP_V1 keeps such a URI out of the next request.

Merge-safe: content-only Function update; never touches valves / API_KEY.
Leaves http(s), /api/v1/files/ and relative URLs untouched.
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

MARKER = "IMAGE_DATA_URI_PERSIST_V1"

OLD_URL_BRANCH = '''                for key in ("url", "image_url", "imageUrl", "content_url"):
                    candidate = entry.get(key)
                    if isinstance(candidate, str) and candidate.strip():
                        return candidate.strip()
                    if isinstance(candidate, dict):
'''

NEW_URL_BRANCH = '''                for key in ("url", "image_url", "imageUrl", "content_url"):
                    candidate = entry.get(key)
                    if isinstance(candidate, str) and candidate.strip():
                        # IMAGE_DATA_URI_PERSIST_V1: a data: URI returned here is
                        # rendered into markdown and replayed as text on the next
                        # turn, which overflows the model's context window. Store it
                        # like the b64_json branch below; keep the raw URI when
                        # storage is unavailable so the image still renders.
                        candidate_url = candidate.strip()
                        if candidate_url.startswith("data:"):
                            return await _materialize_image_from_str(candidate_url) or candidate_url
                        return candidate_url
                    if isinstance(candidate, dict):
'''

REPLACEMENTS: list[tuple[str, str, str]] = [
    ("url-branch", OLD_URL_BRANCH, NEW_URL_BRANCH),
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
    parser.add_argument("--dry-run", action="store_true", help="Patch in memory; do not POST")
    parser.add_argument("--from-file", default="", help="Patch this file instead of the live Pipe")
    parser.add_argument("--write-patched", default="", help="With --dry-run, write patched content here")
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
    print(f"pipe={pipe_name}")
    print(f"sha256[:12] before={content_sha12(original)} after={content_sha12(new_content)}")
    print(f"marker={MARKER} present={MARKER in new_content}")
    for keep in ("COMPARE_CROSS_MODEL_REASONING_V1", "FABLE_UNSIGNED_SUMMARY_V1"):
        print(f"kept marker {keep} present={keep in new_content}")

    if new_content == original:
        print("already patched; no content change" if MARKER in original else "no content change")
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
        json={"id": PIPE_ID, "name": pipe_name, "meta": meta, "content": new_content},
        timeout=180,
    )
    if resp.status_code != 200:
        raise SystemExit(f"update pipe: {resp.status_code} {resp.text[:500]}")
    print(f"pipe content updated {MARKER}")
    print("API_KEY not touched (content-only update)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
