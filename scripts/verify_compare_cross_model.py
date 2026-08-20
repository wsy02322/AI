#!/usr/bin/env python3
"""Live ST-10 regression: Grok persisted reasoning must not 404 Opus.

The compare 404 is not visible on /api/chat/completions without chat_id.
OWUI queues those as tasks; the Pipe persists reasoning artifacts and
embeds an empty-link marker like `[0001…]: #` in the assistant text.
A later Opus turn in the same chat replays that artifact (Grok ciphertext)
into /responses input → OpenRouter 404 unless S2′ retries after stripping.

Evidence of retry (not a hard assert): Opus usage.input_tokens ≈ 2× the
status-line input, because the rejected payload is sent again.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import DEFAULT_MODEL_PRIMARY, DEFAULT_MODEL_SECONDARY, PIPE

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
OPENWEBUI_PASSWORD = os.environ.get("OPENWEBUI_PASSWORD")


def _login_candidates() -> list[str]:
    candidates: list[str] = []
    for value in (os.environ.get("OPENWEBUI_USERNAME"), os.environ.get("OPENWEBUI_EMAIL")):
        if value and value not in candidates:
            candidates.append(value)
    return candidates


def signin() -> str:
    last = ""
    for ident in _login_candidates():
        resp = requests.post(
            f"{OPENWEBUI_URL}/api/v1/auths/signin",
            json={"email": ident, "password": OPENWEBUI_PASSWORD},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()["token"]
        last = f"{resp.status_code} {resp.text[:160]}"
        if resp.status_code == 429:
            time.sleep(8)
    raise SystemExit(f"signin failed: {last}")


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


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


def _has_artifact_marker(text: str) -> bool:
    return "]: #" in (text or "")


def _cross_model_reject(text: str) -> bool:
    blob = (text or "").lower()
    return (
        "produced under a different model" in blob
        or "encrypted reasoning" in blob
        or "compaction content" in blob
    )


def _status_input_tokens(msg: dict) -> int | None:
    for item in msg.get("statusHistory") or []:
        if not isinstance(item, dict):
            continue
        desc = str(item.get("description") or "")
        if "Input:" not in desc:
            continue
        try:
            after = desc.split("Input:", 1)[1]
            num = after.split(",", 1)[0].strip().split()[0]
            return int(num)
        except (IndexError, ValueError):
            return None
    return None


def complete_via_chat(
    h: dict[str, str],
    chat_id: str,
    model: str,
    messages: list,
    msg_id: str,
    timeout: int = 180,
) -> dict:
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/chat/completions",
        headers=h,
        json={
            "model": model,
            "messages": messages,
            "stream": True,
            "include_reasoning": True,
            "chat_id": chat_id,
            "id": msg_id,
            "session_id": str(uuid.uuid4()),
        },
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"enqueue {model} {resp.status_code} {resp.text[:300]}")
    deadline = time.time() + timeout
    last: dict = {}
    while time.time() < deadline:
        detail = requests.get(f"{OPENWEBUI_URL}/api/v1/chats/{chat_id}", headers=h, timeout=30).json()
        hist = ((detail.get("chat") or {}).get("history") or {}).get("messages") or {}
        last = hist.get(msg_id) or {}
        content = last.get("content") or ""
        if last.get("done") and str(content).strip():
            return last
        time.sleep(1.5)
    raise RuntimeError(f"timeout waiting for {model} message {msg_id}: {json.dumps(last)[:400]}")


def main() -> int:
    if not OPENWEBUI_URL or not OPENWEBUI_PASSWORD:
        raise SystemExit("Missing OPENWEBUI_URL / OPENWEBUI_PASSWORD")
    h = headers(signin())
    r = Report()

    persist = requests.get(
        f"{OPENWEBUI_URL}/api/v1/functions/id/{PIPE}/valves",
        headers=h,
        timeout=30,
    )
    if persist.status_code == 200:
        value = persist.json().get("PERSIST_REASONING_TOKENS")
        if value not in (None, "", "conversation"):
            r.err(f"PERSIST_REASONING_TOKENS={value} want conversation (or unset default)")
        else:
            r.ok(f"PERSIST_REASONING_TOKENS={value or 'unset→conversation'}")

    chat = requests.post(
        f"{OPENWEBUI_URL}/api/v1/chats/new",
        headers=h,
        json={
            "chat": {
                "title": "st10-compare-cross-model",
                "models": [DEFAULT_MODEL_PRIMARY, DEFAULT_MODEL_SECONDARY],
                "history": {"messages": {}, "currentId": None},
                "messages": [],
            }
        },
        timeout=30,
    )
    if chat.status_code != 200:
        r.err(f"create chat {chat.status_code} {chat.text[:200]}")
        print(f"\ncompare: {len(r.oks)} ok, {len(r.errors)} err")
        return 1
    chat_id = chat.json()["id"]
    user_text = "Think carefully: 89 multiplied by 97. Reply with the integer only."
    user_id = str(uuid.uuid4())
    grok_id = str(uuid.uuid4())

    grok_msg = complete_via_chat(
        h,
        chat_id,
        DEFAULT_MODEL_PRIMARY,
        [{"role": "user", "content": user_text, "id": user_id}],
        grok_id,
    )
    grok_text = grok_msg.get("content") or ""
    if not grok_text.strip():
        r.err("grok turn1 empty")
    elif not _has_artifact_marker(grok_text):
        r.err(f"grok turn1 missing persist marker; cannot exercise 404 path: {grok_text[:160]!r}")
    else:
        r.ok(f"grok turn1 200 marker=yes text={grok_text.splitlines()[0][:80]!r}")

    if r.errors:
        print(f"\ncompare: {len(r.oks)} ok, {len(r.errors)} err")
        for e in r.errors:
            print(f"  - {e}")
        return 1

    history = [
        {"role": "user", "content": user_text, "id": user_id},
        {
            "role": "assistant",
            "content": grok_text,
            "id": grok_id,
            "model": DEFAULT_MODEL_PRIMARY,
        },
        {"role": "user", "content": "Reply with the single word OK."},
    ]

    opus_id = str(uuid.uuid4())
    opus_msg = complete_via_chat(h, chat_id, DEFAULT_MODEL_SECONDARY, history, opus_id)
    opus_text = opus_msg.get("content") or ""
    opus_blob = json.dumps(opus_msg)
    if _cross_model_reject(opus_text + opus_blob):
        r.err(f"opus follow-up still cross-model reject: {opus_text[:400]!r}")
    elif not opus_text.strip():
        r.err("opus follow-up empty")
    else:
        r.ok(f"opus follow-up 200 text={opus_text.splitlines()[0][:80]!r}")

    status_in = _status_input_tokens(opus_msg)
    usage_in = (opus_msg.get("usage") or {}).get("input_tokens")
    if isinstance(status_in, int) and isinstance(usage_in, int) and status_in > 0:
        if usage_in == status_in * 2:
            r.ok(f"opus usage {usage_in} == 2× status input {status_in} (internal retry)")
        else:
            print(f"INFO opus usage.input_tokens={usage_in} status_input={status_in} (retry fingerprint optional)")

    grok2_id = str(uuid.uuid4())
    grok2_msg = complete_via_chat(h, chat_id, DEFAULT_MODEL_PRIMARY, history, grok2_id)
    grok2_text = grok2_msg.get("content") or ""
    if _cross_model_reject(grok2_text):
        r.err(f"grok same-model follow-up reject: {grok2_text[:300]!r}")
    elif not grok2_text.strip():
        r.err("grok same-model follow-up empty")
    else:
        r.ok(f"grok same-model follow-up 200 text={grok2_text.splitlines()[0][:80]!r}")

    print(f"\ncompare: {len(r.oks)} ok, {len(r.errors)} err")
    for e in r.errors:
        print(f"  - {e}")
    return 1 if r.errors else 0


if __name__ == "__main__":
    sys.exit(main())
