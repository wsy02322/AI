#!/usr/bin/env python3
"""ST-13 backstop: keep inline data URIs out of the retained image canvas.

`openrouter_image_context_guard` keeps the newest user message plus the nearest
previous assistant image, and strips images from everything older. That retained
canvas is replayed verbatim, so when it is an inline `data:image/...;base64,...`
markdown blob (see patch_pipe_image_data_uri_persist.py) it lands in the prompt as
text and overflows a 128k window on its own.

This patch strips only `data:` images from the retained canvas. File-backed images
(`/api/v1/files/...`) stay: the pipe forwards those as image parts, which cost ~1k
tokens instead of ~1M. No size threshold -- 1MB of base64 already exceeds 131072.

The newest user message is never touched. Everything else keeps its behaviour.
Content-only Function update; valves are not written.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time

import requests

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
GUARD_ID = "openrouter_image_context_guard"

MARKER = "IMAGE_CONTEXT_DATA_URI_CAP_V1"

OLD_RE = '''_DATA_IMG_MD = re.compile(r"!\\[[^\\]]*\\]\\((?:data:image/[^)]+|/api/v1/files/[^)]+)\\)", re.I)
'''

NEW_RE = '''_DATA_IMG_MD = re.compile(r"!\\[[^\\]]*\\]\\((?:data:image/[^)]+|/api/v1/files/[^)]+)\\)", re.I)
# IMAGE_CONTEXT_DATA_URI_CAP_V1: data-URI-only variant, used on the retained canvas.
_DATA_URI_MD = re.compile(r"!\\[[^\\]]*\\]\\(data:image/[^)]+\\)", re.I)
'''

OLD_STRIP_DEF = '''        def _strip_images(msg: dict, note: str) -> None:
'''

NEW_STRIP_DEF = '''        def _block_is_data_uri(block: dict) -> bool:
            payload = block.get("image_url") or block.get("url") or block.get("image")
            if isinstance(payload, dict):
                payload = payload.get("url")
            return isinstance(payload, str) and payload.strip().lower().startswith("data:")

        def _replace_data_uris(text: str, note: str) -> str:
            cleaned = _DATA_URI_MD.sub(note, text).strip()
            # A bare data URI outside markdown would survive the substitution.
            return note if "data:image" in cleaned else (cleaned or note)

        def _strip_data_uris(msg: dict, note: str) -> None:
            """Drop inline data: images, keep file-backed ones."""
            content = msg.get("content")
            if isinstance(content, str):
                if "data:image" in content:
                    msg["content"] = _replace_data_uris(content, note)
                return
            if not isinstance(content, list):
                return
            kept = []
            for block in content:
                if not isinstance(block, dict):
                    kept.append(block)
                    continue
                if block.get("type") in {"image_url", "input_image", "image"}:
                    if _block_is_data_uri(block):
                        continue
                    kept.append(block)
                    continue
                if block.get("type") in {"text", "input_text"}:
                    text = block.get("text")
                    if isinstance(text, str) and "data:image" in text:
                        block = dict(block)
                        block["text"] = _replace_data_uris(text, note)
                kept.append(block)
            msg["content"] = kept if kept else note

        def _strip_images(msg: dict, note: str) -> None:
'''

OLD_TAIL = '''        note = "[Earlier image omitted to reduce context size]"
        for i, msg in enumerate(messages):
            if isinstance(msg, dict) and i not in keep_indices and _has_image(msg):
                _strip_images(msg, note)
        return body
'''

NEW_TAIL = '''        note = (
            "[Earlier image omitted to fit the model's context. Start a new chat and "
            "attach only the image you want to edit.]"
        )
        for i, msg in enumerate(messages):
            if isinstance(msg, dict) and i not in keep_indices and _has_image(msg):
                _strip_images(msg, note)

        # IMAGE_CONTEXT_DATA_URI_CAP_V1: the retained canvas is replayed verbatim, so
        # an inline data URI is billed as text and overflows the window on its own.
        canvas_note = (
            "[Previous image omitted: it was stored inline and is too large for the "
            "model's context. Start a new chat and attach only the image you want to edit.]"
        )
        for i in keep_indices:
            if i == last_user_idx:
                continue
            msg = messages[i]
            if isinstance(msg, dict):
                _strip_data_uris(msg, canvas_note)
        return body
'''

REPLACEMENTS: list[tuple[str, str, str]] = [
    ("data-uri-re", OLD_RE, NEW_RE),
    ("strip-helpers", OLD_STRIP_DEF, NEW_STRIP_DEF),
    ("canvas-tail", OLD_TAIL, NEW_TAIL),
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
                f"hunk {name} mismatch (count={count}); abort to avoid corrupting guard"
            )
        content = content.replace(old, new, 1)
    if MARKER not in content:
        raise SystemExit("patch applied but marker missing; abort")
    compile(content, "<guard>", "exec")
    return content


def content_sha12(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Patch in memory; do not POST")
    parser.add_argument("--from-file", default="", help="Patch this file instead of the live guard")
    parser.add_argument("--write-patched", default="", help="With --dry-run, write patched content here")
    args = parser.parse_args()

    if args.from_file:
        with open(args.from_file, encoding="utf-8") as fh:
            original = fh.read()
        name = os.path.basename(args.from_file)
        meta: dict = {}
    else:
        if not OPENWEBUI_URL:
            raise SystemExit("OPENWEBUI_URL missing")
        token = signin()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        fn = requests.get(f"{OPENWEBUI_URL}/api/v1/functions/id/{GUARD_ID}", headers=headers, timeout=60)
        if fn.status_code != 200:
            raise SystemExit(f"get guard: {fn.status_code} {fn.text[:300]}")
        guard = fn.json()
        original = guard["content"]
        name = guard.get("name")
        meta = guard.get("meta") or {}

    new_content = patch_content(original)
    print(f"guard={name}")
    print(f"sha256[:12] before={content_sha12(original)} after={content_sha12(new_content)}")
    print(f"marker={MARKER} present={MARKER in new_content}")

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
        f"{OPENWEBUI_URL}/api/v1/functions/id/{GUARD_ID}/update",
        headers=headers,
        json={"id": GUARD_ID, "name": name, "meta": meta, "content": new_content},
        timeout=120,
    )
    if resp.status_code != 200:
        raise SystemExit(f"update guard: {resp.status_code} {resp.text[:500]}")
    print(f"guard content updated {MARKER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
