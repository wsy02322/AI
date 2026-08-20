#!/usr/bin/env python3
"""Live regression: Grok encrypted reasoning must not 404 when replayed to Opus.

Uses /api/chat/completions (no UI). Success = Opus returns 200 after being
fed Grok's previous assistant turn including reasoning_details.
Same-model Grok follow-up must also still succeed (persist not globally off).
"""

from __future__ import annotations

import json
import os
import sys
import time

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


def _message_blob(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {}
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        msg = (choices[0] or {}).get("message") or {}
        if isinstance(msg, dict):
            return msg
    data = payload.get("data")
    if isinstance(data, dict):
        return data
    return {}


def _extract_reasoning_details(payload: dict) -> list:
    msg = _message_blob(payload)
    details = msg.get("reasoning_details")
    if isinstance(details, list) and details:
        return details
    for key in ("reasoning_details", "reasoning"):
        value = payload.get(key)
        if isinstance(value, list) and value:
            return value
    return []


def _extract_text(payload: dict) -> str:
    msg = _message_blob(payload)
    content = msg.get("content")
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
        joined = "".join(parts).strip()
        if joined:
            return joined
    if isinstance(payload.get("content"), str):
        return payload["content"]
    return (json.dumps(payload)[:400] if payload else "")


def chat(h: dict[str, str], model: str, messages: list, timeout: int = 180) -> tuple[int, dict, str]:
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/chat/completions",
        headers=h,
        json={
            "model": model,
            "messages": messages,
            "stream": False,
            "include_reasoning": True,
        },
        timeout=timeout,
    )
    try:
        payload = resp.json()
    except Exception:
        payload = {"raw": resp.text[:2000]}
    text = _extract_text(payload) if resp.status_code == 200 else (resp.text or "")[:800]
    return resp.status_code, payload, text


def _looks_like_cross_model_404(status: int, text: str) -> bool:
    blob = (text or "").lower()
    return status in (400, 404) or "produced under a different model" in blob or "encrypted reasoning" in blob


def main() -> int:
    if not OPENWEBUI_URL or not OPENWEBUI_PASSWORD:
        raise SystemExit("Missing OPENWEBUI_URL / OPENWEBUI_PASSWORD")
    h = headers(signin())
    errors: list[str] = []
    oks: list[str] = []

    user1 = "What is 17 multiplied by 19? Reply with the integer only."
    status, grok_payload, grok_text = chat(
        h,
        DEFAULT_MODEL_PRIMARY,
        [{"role": "user", "content": user1}],
        timeout=240,
    )
    if status != 200:
        errors.append(f"grok turn1 {status} {grok_text[:300]}")
        print("ERR " + errors[-1])
        print(f"\ncompare: {len(oks)} ok, {len(errors)} err")
        return 1
    oks.append(f"grok turn1 200 text={grok_text[:80]!r}")
    print("OK  " + oks[-1])

    details = _extract_reasoning_details(grok_payload)
    print(f"INFO grok reasoning_details n={len(details)} types={[d.get('type') if isinstance(d, dict) else type(d).__name__ for d in details[:6]]}")
    grok_msg: dict = {"role": "assistant", "content": grok_text or "323"}
    if details:
        grok_msg["reasoning_details"] = details
    else:
        print("WARN grok returned no reasoning_details; cross-model 404 path may not be exercised")

    user2 = "Reply with the single word OK."
    history = [
        {"role": "user", "content": user1},
        grok_msg,
        {"role": "user", "content": user2},
    ]

    opus_status, opus_payload, opus_text = chat(h, DEFAULT_MODEL_SECONDARY, history, timeout=240)
    blob = json.dumps(opus_payload)[:1200]
    if opus_status != 200:
        errors.append(f"opus follow-up {opus_status} {opus_text[:400]}")
        print("ERR " + errors[-1])
        if _looks_like_cross_model_404(opus_status, blob + opus_text):
            print("INFO this is the original compare 404; retry gate did not recover")
    elif "produced under a different model" in (opus_text + blob).lower():
        errors.append("opus 200 but error text still contains cross-model reject")
        print("ERR " + errors[-1])
    else:
        oks.append(f"opus follow-up 200 text={opus_text[:80]!r}")
        print("OK  " + oks[-1])

    grok2_status, _, grok2_text = chat(h, DEFAULT_MODEL_PRIMARY, history, timeout=240)
    if grok2_status != 200:
        errors.append(f"grok same-model follow-up {grok2_status} {grok2_text[:300]}")
        print("ERR " + errors[-1])
    else:
        oks.append(f"grok same-model follow-up 200 text={grok2_text[:80]!r}")
        print("OK  " + oks[-1])

    persist = requests.get(
        f"{OPENWEBUI_URL}/api/v1/functions/id/{PIPE}/valves",
        headers=h,
        timeout=30,
    )
    if persist.status_code == 200:
        value = persist.json().get("PERSIST_REASONING_TOKENS")
        if value != "conversation":
            errors.append(f"PERSIST_REASONING_TOKENS={value} want conversation")
            print("ERR " + errors[-1])
        else:
            oks.append("PERSIST_REASONING_TOKENS=conversation")
            print("OK  " + oks[-1])

    print(f"\ncompare: {len(oks)} ok, {len(errors)} err")
    for e in errors:
        print(f"  - {e}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
