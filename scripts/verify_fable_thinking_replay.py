#!/usr/bin/env python3
"""Live ST-11: Fable same-model follow-up must not 400 on unsigned thinking."""

from __future__ import annotations

import json
import os
import sys
import time
import uuid

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import PIPE

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
OPENWEBUI_PASSWORD = os.environ.get("OPENWEBUI_PASSWORD")
FABLE_MODEL = f"{PIPE}.anthropic.claude-fable-5.1"


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


def _thinking_modified_error(text: str) -> bool:
    blob = (text or "").lower()
    return "cannot be modified" in blob and "thinking" in blob


def _reasoning_items(msg: dict) -> list[dict]:
    items: list[dict] = []
    output = msg.get("output")
    if isinstance(output, list):
        for item in output:
            if isinstance(item, dict) and item.get("type") == "reasoning":
                items.append(item)
    return items


def _has_crypto(item: dict) -> bool:
    enc = item.get("encrypted_content")
    sig = item.get("signature")
    return (isinstance(enc, str) and bool(enc.strip())) or (isinstance(sig, str) and bool(sig.strip()))


def complete_via_chat(
    h: dict[str, str],
    chat_id: str,
    model: str,
    messages: list,
    msg_id: str,
    timeout: int = 240,
) -> dict:
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/chat/completions",
        headers=h,
        json={
            "model": model,
            "messages": messages,
            "stream": True,
            "include_reasoning": True,
            "reasoning_effort": "high",
            "reasoning": {"effort": "high", "exclude": False},
            "chat_id": chat_id,
            "id": msg_id,
            "session_id": str(uuid.uuid4()),
        },
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"enqueue {model} {resp.status_code} {resp.text[:400]}")
    deadline = time.time() + timeout
    last: dict = {}
    while time.time() < deadline:
        detail = requests.get(f"{OPENWEBUI_URL}/api/v1/chats/{chat_id}", headers=h, timeout=30).json()
        hist = ((detail.get("chat") or {}).get("history") or {}).get("messages") or {}
        last = hist.get(msg_id) or {}
        content = last.get("content") or ""
        blob = content if isinstance(content, str) else json.dumps(content)
        if last.get("done") and (str(blob).strip() or last.get("error")):
            return last
        time.sleep(1.5)
    raise RuntimeError(f"timeout waiting for {model} message {msg_id}: {json.dumps(last)[:500]}")


def main() -> int:
    if not OPENWEBUI_URL or not OPENWEBUI_PASSWORD:
        raise SystemExit("Missing OPENWEBUI_URL / OPENWEBUI_PASSWORD")
    h = headers(signin())
    r = Report()

    fn = requests.get(f"{OPENWEBUI_URL}/api/v1/functions/id/{PIPE}", headers=h, timeout=60)
    if fn.status_code != 200:
        r.err(f"get pipe {fn.status_code}")
        print(f"\nfable: {len(r.oks)} ok, {len(r.errors)} err")
        return 1
    content = fn.json().get("content") or ""
    if "FABLE_UNSIGNED_SUMMARY_V1" not in content:
        r.err("Pipe missing FABLE_UNSIGNED_SUMMARY_V1")
    else:
        r.ok("Pipe marker FABLE_UNSIGNED_SUMMARY_V1")
    if "reasoning.encrypted_content" not in content:
        r.err("Pipe missing reasoning.encrypted_content include")
    else:
        r.ok("Pipe requests reasoning.encrypted_content")
    if "COMPARE_CROSS_MODEL_REASONING_V1" not in content:
        r.err("S2′ marker COMPARE_CROSS_MODEL_REASONING_V1 missing")
    else:
        r.ok("S2′ marker still present")

    persist = requests.get(f"{OPENWEBUI_URL}/api/v1/functions/id/{PIPE}/valves", headers=h, timeout=30)
    if persist.status_code == 200:
        value = persist.json().get("PERSIST_REASONING_TOKENS")
        if value not in (None, "", "conversation"):
            r.err(f"PERSIST_REASONING_TOKENS={value} want conversation")
        else:
            r.ok(f"PERSIST_REASONING_TOKENS={value or 'unset→conversation'}")

    chat = requests.post(
        f"{OPENWEBUI_URL}/api/v1/chats/new",
        headers=h,
        json={
            "chat": {
                "title": "st11-fable-thinking-replay",
                "models": [FABLE_MODEL],
                "history": {"messages": {}, "currentId": None},
                "messages": [],
            }
        },
        timeout=30,
    )
    if chat.status_code != 200:
        r.err(f"create chat {chat.status_code} {chat.text[:200]}")
        print(f"\nfable: {len(r.oks)} ok, {len(r.errors)} err")
        return 1
    chat_id = chat.json()["id"]
    user_text = (
        "Plan a 4-course plant-based tasting menu that is filling, high-protein, and uses leftover "
        "chickpeas, kale, and day-old bread. For each course give one sentence why it satisfies hunger. "
        "Think through nutrition and texture tradeoffs before answering."
    )
    user_id = str(uuid.uuid4())
    asst_id = str(uuid.uuid4())

    turn1 = complete_via_chat(
        h,
        chat_id,
        FABLE_MODEL,
        [{"role": "user", "content": user_text, "id": user_id}],
        asst_id,
    )
    turn1_text = turn1.get("content") or ""
    turn1_blob = json.dumps(turn1)
    if _thinking_modified_error(str(turn1_text) + turn1_blob):
        r.err(f"fable turn1 cannot-be-modified: {str(turn1_text)[:300]!r}")
    elif not str(turn1_text).strip():
        r.err("fable turn1 empty")
    else:
        r.ok(f"fable turn1 200 text={str(turn1_text).splitlines()[0][:80]!r}")

    reasoning = _reasoning_items(turn1)
    crypto_n = sum(1 for item in reasoning if _has_crypto(item))
    details = (turn1.get("usage") or {}).get("output_tokens_details") or {}
    reasoning_tokens = details.get("reasoning_tokens")
    if reasoning:
        r.ok(f"fable turn1 output reasoning={len(reasoning)} with_crypto={crypto_n} tokens={reasoning_tokens}")
        if crypto_n == 0:
            r.err("fable turn1 reasoning items lack signature/encrypted_content (A failed)")
        else:
            keys = sorted({k for item in reasoning for k in item.keys()})
            print(f"INFO turn1 has signature/ciphertext; turn2 exercises replay (A); item_keys={keys}")
    else:
        print(f"INFO turn1 message.output has no reasoning items (reasoning_tokens={reasoning_tokens}); follow-up still must succeed")

    if r.errors:
        print(f"\nfable: {len(r.oks)} ok, {len(r.errors)} err")
        for e in r.errors:
            print(f"  - {e}")
        return 1

    history = [
        {"role": "user", "content": user_text, "id": user_id},
        {
            "role": "assistant",
            "content": turn1_text,
            "id": asst_id,
            "model": FABLE_MODEL,
        },
        {"role": "user", "content": "Make the second course spicier and keep it plant-based. One short paragraph."},
    ]
    asst2_id = str(uuid.uuid4())
    turn2 = complete_via_chat(h, chat_id, FABLE_MODEL, history, asst2_id)
    turn2_text = turn2.get("content") or ""
    turn2_blob = json.dumps(turn2)
    if _thinking_modified_error(str(turn2_text) + turn2_blob):
        r.err(f"fable follow-up cannot-be-modified: {str(turn2_text)[:400]!r}")
    elif not str(turn2_text).strip():
        r.err("fable follow-up empty")
    else:
        r.ok(f"fable follow-up 200 text={str(turn2_text).splitlines()[0][:80]!r}")

    turn2_reasoning = _reasoning_items(turn2)
    if turn2_reasoning:
        unsigned = [item for item in turn2_reasoning if not _has_crypto(item)]
        if unsigned and crypto_n:
            print(f"INFO follow-up output has {len(unsigned)} summary-only reasoning item(s)")
        r.ok(f"fable follow-up output reasoning={len(turn2_reasoning)}")

    print(f"\nfable: {len(r.oks)} ok, {len(r.errors)} err")
    for e in r.errors:
        print(f"  - {e}")
    return 1 if r.errors else 0


if __name__ == "__main__":
    sys.exit(main())
