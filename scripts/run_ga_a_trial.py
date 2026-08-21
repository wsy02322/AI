#!/usr/bin/env python3
"""GA-A: gpt-audio vs MiniMax L1 TTS smoke (no Call/public changes)."""

from __future__ import annotations

import base64
import json
import os
import sys
import time
from typing import Any

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import PIPE

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
OPENWEBUI_PASSWORD = os.environ.get("OPENWEBUI_PASSWORD")
TEST_SENTENCE = "OK，这是音频测试。"
GPT_AUDIO_MINI = f"{PIPE}.openai.gpt-audio-mini"
GPT_AUDIO = f"{PIPE}.openai.gpt-audio"
ARTIFACT_DIR = os.environ.get("GA_A_ARTIFACT_DIR", "/opt/cursor/artifacts")


def _login_candidates() -> list[str]:
    candidates: list[str] = []
    for value in (os.environ.get("OPENWEBUI_USERNAME"), os.environ.get("OPENWEBUI_EMAIL")):
        if value and value not in candidates:
            candidates.append(value)
    return candidates


def signin() -> str:
    if not OPENWEBUI_URL or not OPENWEBUI_PASSWORD:
        raise SystemExit("Missing OPENWEBUI_URL / OPENWEBUI_PASSWORD")
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


def _save_bytes(path: str, data: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def test_minimax_tts(h: dict[str, str]) -> dict[str, Any]:
    t0 = time.perf_counter()
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/audio/speech",
        headers=h,
        json={"input": TEST_SENTENCE, "voice": "alloy"},
        timeout=120,
    )
    wall = round(time.perf_counter() - t0, 2)
    result: dict[str, Any] = {
        "label": "MiniMax L1",
        "http": resp.status_code,
        "wall_s": wall,
        "has_playable_audio": False,
        "bytes": len(resp.content or b""),
        "content_type": resp.headers.get("content-type", ""),
        "usage": None,
        "note": "",
    }
    if resp.status_code == 200 and len(resp.content or b"") > 200:
        result["has_playable_audio"] = True
        _save_bytes(f"{ARTIFACT_DIR}/ga_a_minimax_l1.mp3", resp.content)
    else:
        result["note"] = (resp.text or "")[:400]
    return result


def _collect_stream_audio(resp: requests.Response) -> tuple[bytes, str, dict[str, Any] | None]:
    audio_b64_parts: list[str] = []
    text_parts: list[str] = []
    usage: dict[str, Any] | None = None
    raw_lines: list[str] = []
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        payload = line[6:].strip()
        if payload == "[DONE]":
            break
        raw_lines.append(payload[:500])
        try:
            chunk = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if chunk.get("usage"):
            usage = chunk["usage"]
        choices = chunk.get("choices") or []
        if not choices:
            continue
        delta = choices[0].get("delta") or {}
        if delta.get("content"):
            text_parts.append(str(delta["content"]))
        audio = delta.get("audio") or {}
        if audio.get("data"):
            audio_b64_parts.append(str(audio["data"]))
        message = choices[0].get("message") or {}
        msg_audio = message.get("audio") or {}
        if msg_audio.get("data"):
            audio_b64_parts.append(str(msg_audio["data"]))
        if message.get("content"):
            text_parts.append(str(message["content"]))
    audio_bytes = b""
    if audio_b64_parts:
        audio_bytes = base64.b64decode("".join(audio_b64_parts))
    return audio_bytes, "".join(text_parts).strip(), usage


def test_gpt_audio(h: dict[str, str], model_id: str, label: str) -> dict[str, Any]:
    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "user",
                "content": f"请用一句话口头说：{TEST_SENTENCE}",
            }
        ],
        "modalities": ["text", "audio"],
        "audio": {"voice": "alloy", "format": "wav"},
        "stream": True,
    }
    t0 = time.perf_counter()
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/chat/completions",
        headers=h,
        json=payload,
        timeout=180,
        stream=True,
    )
    wall = round(time.perf_counter() - t0, 2)
    result: dict[str, Any] = {
        "label": label,
        "model": model_id,
        "http": resp.status_code,
        "wall_s": wall,
        "has_playable_audio": False,
        "bytes": 0,
        "content_type": resp.headers.get("content-type", ""),
        "usage": None,
        "text": "",
        "note": "",
    }
    if resp.status_code != 200:
        body = resp.text[:800] if not resp.raw.closed else ""
        try:
            body = resp.content[:800].decode("utf-8", errors="replace")
        except Exception:
            pass
        result["note"] = body
        return result

    audio_bytes, text, usage = _collect_stream_audio(resp)
    result["bytes"] = len(audio_bytes)
    result["text"] = text[:240]
    result["usage"] = usage
    if len(audio_bytes) > 200:
        result["has_playable_audio"] = True
        safe = label.replace(" ", "_").lower()
        _save_bytes(f"{ARTIFACT_DIR}/ga_a_{safe}.wav", audio_bytes)
    elif text:
        result["note"] = "text-only response (no audio bytes in stream)"
    else:
        result["note"] = "empty stream (no text, no audio)"
    return result


def main() -> int:
    h = headers(signin())
    results: list[dict[str, Any]] = []

    print(f"GA-A sentence: {TEST_SENTENCE!r}")
    minimax = test_minimax_tts(h)
    results.append(minimax)
    print(json.dumps(minimax, ensure_ascii=False, indent=2))

    mini = test_gpt_audio(h, GPT_AUDIO_MINI, "gpt-audio-mini")
    results.append(mini)
    print(json.dumps(mini, ensure_ascii=False, indent=2))

    if not mini.get("has_playable_audio"):
        full = test_gpt_audio(h, GPT_AUDIO, "gpt-audio")
        results.append(full)
        print(json.dumps(full, ensure_ascii=False, indent=2))

    summary_path = f"{ARTIFACT_DIR}/ga_a_results.json"
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({"sentence": TEST_SENTENCE, "results": results}, f, ensure_ascii=False, indent=2)
    print(f"\nWrote {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
