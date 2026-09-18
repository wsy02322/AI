#!/usr/bin/env python3
"""ST-14 live probes: Guard marker + no leftover data:image in the reported chat."""

from __future__ import annotations

import os
import sys
import time
import uuid

import requests

from patch_image_context_data_uri_outlet import (
    GUARD_ID,
    MARKER,
    rewrite_assistant_text,
)

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
CHAT_ID = os.environ.get("ST14_CHAT_ID", "10079dd9-278d-4b7c-8aef-5c9cdc7ff29c")


def _login_candidates() -> list[str]:
    candidates: list[str] = []
    for value in (os.environ.get("OPENWEBUI_USERNAME"), os.environ.get("OPENWEBUI_EMAIL")):
        if value and value not in candidates:
            candidates.append(value)
    return candidates


def signin() -> str:
    if not OPENWEBUI_URL or not os.environ.get("OPENWEBUI_PASSWORD"):
        raise SystemExit("Missing OPENWEBUI_URL / OPENWEBUI_PASSWORD")
    last = ""
    for ident in _login_candidates():
        resp = requests.post(
            f"{OPENWEBUI_URL}/api/v1/auths/signin",
            json={"email": ident, "password": os.environ["OPENWEBUI_PASSWORD"]},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()["token"]
        last = f"{resp.status_code} {resp.text[:160]}"
        if resp.status_code == 429:
            time.sleep(8)
    raise SystemExit(f"signin failed: {last}")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.oks: list[str] = []

    def ok(self, msg: str) -> None:
        self.oks.append(msg)
        print(f"OK  {msg}")

    def err(self, msg: str) -> None:
        self.errors.append(msg)
        print(f"ERR {msg}")


def main() -> int:
    r = Report()
    token = signin()
    h = {"Authorization": f"Bearer {token}"}
    fn = requests.get(f"{OPENWEBUI_URL}/api/v1/functions/id/{GUARD_ID}", headers=h, timeout=60)
    if fn.status_code != 200:
        r.err(f"get guard {fn.status_code}")
    else:
        guard = fn.json()
        content = guard.get("content") or ""
        if not guard.get("is_active"):
            r.err("guard inactive")
        else:
            r.ok("guard active")
        if not guard.get("is_global"):
            r.err("guard not global")
        else:
            r.ok("guard global")
        if MARKER not in content:
            r.err(f"guard missing {MARKER}")
        else:
            r.ok(f"guard has {MARKER}")
        if "async def outlet(" not in content or "async def stream(" not in content:
            r.err("guard missing stream/outlet")
        else:
            r.ok("guard stream+outlet present")
        if "def inlet(" not in content or "_is_target_model" not in content:
            r.err("guard inlet/image-target logic missing")
        else:
            r.ok("guard inlet still image-target")

    sample = "见 [路线概览图](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAlgAAA"
    cleaned = rewrite_assistant_text(sample)
    if "data:image" in cleaned or "iVBORw0KGgo" in cleaned:
        r.err("local rewrite still leaks truncated data URI")
    else:
        r.ok("local rewrite strips truncated data URI")

    probe_id = None
    try:
        created = requests.post(
            f"{OPENWEBUI_URL}/api/v1/chats/new",
            headers=h,
            json={"chat": {"title": "ST-14 outlet probe"}},
            timeout=30,
        )
        if created.status_code != 200:
            r.err(f"probe chat create {created.status_code}")
        else:
            probe_id = created.json()["id"]
            mid = str(uuid.uuid4())
            png = (
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
            )
            junk = (
                "见下图 "
                f"![路线概览图](data:image/png;base64,{png})\n"
                "[在高德打开 碌曲县→迭部县](https://uri.amap.com/navigation?from=1&to=2)"
            )
            completed = requests.post(
                f"{OPENWEBUI_URL}/api/chat/completed",
                headers=h,
                json={
                    "model": "open_webui_openrouter_integration.anthropic.claude-opus-5",
                    "messages": [
                        {"role": "user", "content": "画个图"},
                        {"role": "assistant", "content": junk},
                    ],
                    "chat_id": probe_id,
                    "id": mid,
                    "session_id": "st14-verify",
                },
                timeout=60,
            )
            if completed.status_code != 200:
                r.err(f"outlet completed {completed.status_code} {completed.text[:160]}")
            else:
                asst = ((completed.json().get("messages") or [{}])[-1] or {}).get("content")
                if not isinstance(asst, str) or "data:image" in asst or "iVBORw" in asst:
                    r.err(f"outlet did not strip data URI: {asst!r:.180}")
                elif "/api/v1/files/" in asst:
                    r.err(f"outlet persisted an image file URL: {asst!r:.180}")
                elif "uri.amap.com" not in asst:
                    r.err(f"outlet dropped the Gaode link: {asst!r:.180}")
                elif "见下图" not in asst:
                    r.err(f"outlet stripped too much: {asst!r:.180}")
                else:
                    r.ok("live outlet strips data-URI image and keeps the Gaode link")
    finally:
        if probe_id:
            requests.delete(f"{OPENWEBUI_URL}/api/v1/chats/{probe_id}", headers=h, timeout=30)

    chat = requests.get(f"{OPENWEBUI_URL}/api/v1/chats/{CHAT_ID}", headers=h, timeout=60)
    if chat.status_code != 200:
        r.err(f"get chat {CHAT_ID} {chat.status_code}")
    else:
        blob = chat.text
        data = chat.json()
        hist = ((data.get("chat") or {}).get("history") or {}).get("messages") or {}
        content_leak = False
        has_map_text = False
        for msg in hist.values():
            if not isinstance(msg, dict) or msg.get("role") != "assistant":
                continue
            content = msg.get("content") or ""
            if "路线概览图" in str(content) or "碌曲" in str(content) or "威海" in str(content):
                has_map_text = True
            if isinstance(content, str) and ("data:image" in content or "iVBORw0KGgo" in content):
                content_leak = True
            if isinstance(content, str) and "/api/v1/files/" in content and "路线概览图" in content:
                r.err(f"chat {CHAT_ID} still has a replacement image markdown")
        if content_leak:
            r.err(f"chat {CHAT_ID} visible content still has data-URI junk")
        else:
            r.ok(f"chat {CHAT_ID} visible content has no data-URI junk")
        if "data:image" in blob:
            r.ok("note: Responses output blob may still store the original URI; visible content is clean")
        if has_map_text:
            r.ok("chat still has the useful route text")
        if "uri.amap.com" in blob or "micropigeon.com/nav" in blob:
            r.ok("chat kept the previous Gaode / nav links")

    print(f"{len(r.oks)} ok / {len(r.errors)} err")
    return 1 if r.errors else 0


if __name__ == "__main__":
    sys.exit(main())
