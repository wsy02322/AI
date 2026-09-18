#!/usr/bin/env python3
"""ST-14 live probes: Guard marker + no leftover data:image in the reported chat."""

from __future__ import annotations

import os
import sys
import time

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

    chat = requests.get(f"{OPENWEBUI_URL}/api/v1/chats/{CHAT_ID}", headers=h, timeout=60)
    if chat.status_code != 200:
        r.err(f"get chat {CHAT_ID} {chat.status_code}")
    else:
        blob = chat.text
        if "data:image" in blob:
            r.err(f"chat {CHAT_ID} still contains data:image")
        else:
            r.ok(f"chat {CHAT_ID} has no data:image")
        if "/api/v1/files/" in blob and "路线概览图" in blob:
            r.ok("chat map rewritten to file URL")
        elif "路线概览图" in blob:
            r.ok("chat map markdown stripped (no leftover URI)")
        else:
            r.ok("chat no longer shows the data-URI dump")

    print(f"{len(r.oks)} ok / {len(r.errors)} err")
    return 1 if r.errors else 0


if __name__ == "__main__":
    sys.exit(main())
