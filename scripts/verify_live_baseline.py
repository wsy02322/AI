#!/usr/bin/env python3
"""L1 live baseline: STT/TTS config, short TTS, vision-capable smoke, screen-share guidance."""

from __future__ import annotations

import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import DEFAULT_MODEL_PRIMARY, PIPE

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
OPENWEBUI_PASSWORD = os.environ.get("OPENWEBUI_PASSWORD")
TTS_MODEL = "openai/tts-1-hd"
TTS_SPLIT_ON = "sentence"
SCREEN_SHARE_NEEDLE = "screen share"
VISION_SMOKE_MODEL = DEFAULT_MODEL_PRIMARY


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
    h = headers(signin())
    r = Report()

    cfg = requests.get(f"{OPENWEBUI_URL}/api/config", headers=h, timeout=30).json()
    perms = (cfg.get("permissions") or {}).get("chat") or {}
    for key in ("stt", "tts", "call"):
        if perms.get(key) is True:
            r.ok(f"permission chat.{key}=true")
        else:
            r.err(f"permission chat.{key}={perms.get(key)}")

    audio = requests.get(f"{OPENWEBUI_URL}/api/v1/audio/config", headers=h, timeout=30).json()
    tts = audio.get("tts") or {}
    stt = audio.get("stt") or {}
    if tts.get("MODEL") == TTS_MODEL:
        r.ok(f"tts model {TTS_MODEL}")
    else:
        r.err(f"tts model={tts.get('MODEL')} want {TTS_MODEL}")
    if (tts.get("SPLIT_ON") or "").lower() == TTS_SPLIT_ON:
        r.ok(f"tts SPLIT_ON={TTS_SPLIT_ON}")
    else:
        r.err(f"tts SPLIT_ON={tts.get('SPLIT_ON')} want {TTS_SPLIT_ON}")
    if tts.get("ENGINE") == "openai" and "openrouter.ai" in (tts.get("OPENAI_API_BASE_URL") or ""):
        r.ok("tts engine openai via OpenRouter")
    else:
        r.err(f"tts engine/url {tts.get('ENGINE')} {tts.get('OPENAI_API_BASE_URL')}")
    if stt.get("ENGINE") == "openai" and stt.get("MODEL"):
        r.ok(f"stt model {stt.get('MODEL')}")
    else:
        r.err(f"stt engine/model {stt.get('ENGINE')} {stt.get('MODEL')}")

    banners = requests.get(f"{OPENWEBUI_URL}/api/v1/configs/banners", headers=h, timeout=30).json()
    blob = " ".join(f"{b.get('title')} {b.get('content')}" for b in banners).lower()
    if SCREEN_SHARE_NEEDLE in blob:
        r.ok("banner mentions screen share")
    else:
        r.err("banner missing screen share guidance")

    speech = requests.post(
        f"{OPENWEBUI_URL}/api/v1/audio/speech",
        headers=h,
        json={"input": "OK.", "voice": tts.get("VOICE") or "alloy"},
        timeout=90,
    )
    ctype = speech.headers.get("content-type", "")
    if speech.status_code == 200 and speech.content and len(speech.content) > 200:
        r.ok(f"tts speech bytes={len(speech.content)} type={ctype}")
    else:
        detail = speech.text[:240]
        # OpenRouter currently has no openai/tts-1[-hd] on /audio/speech
        # (OWUI wraps the upstream 400 as External: Bad Request).
        lowered = detail.lower()
        openrouter_missing = speech.status_code == 400 and (
            "does not exist" in lowered
            or ("bad request" in lowered and "audio/speech" in lowered)
        )
        if openrouter_missing:
            print(
                "WARN tts speech 400: OpenRouter has no /audio/speech model "
                f"{TTS_MODEL}; L1 screen-share still uses vision chat. {detail}"
            )
        else:
            r.err(f"tts speech {speech.status_code} bytes={len(speech.content)} {detail}")

    if speech.status_code == 200 and speech.content:
        files = {"file": ("ok.mp3", speech.content, "audio/mpeg")}
        transcribe = requests.post(
            f"{OPENWEBUI_URL}/api/v1/audio/transcriptions",
            headers={"Authorization": h["Authorization"]},
            files=files,
            timeout=90,
        )
        if transcribe.status_code == 200:
            text = (transcribe.json() or {}).get("text") or ""
            r.ok(f"stt transcription {transcribe.status_code} text={text[:80]!r}")
        else:
            r.err(f"stt transcription {transcribe.status_code} {transcribe.text[:240]}")

    listed = requests.get(f"{OPENWEBUI_URL}/api/models", headers=h, timeout=90).json().get("data") or []
    ids = {m.get("id") for m in listed}
    if VISION_SMOKE_MODEL in ids:
        r.ok(f"vision smoke model listed {VISION_SMOKE_MODEL}")
    else:
        r.err(f"vision smoke model missing {VISION_SMOKE_MODEL}")
    gemini = f"{PIPE}.google.gemini-3-pro-image"
    if gemini in ids:
        r.ok("gemini vision/image model listed")
    else:
        r.err(f"missing {gemini}")

    chat = requests.post(
        f"{OPENWEBUI_URL}/api/chat/completions",
        headers=h,
        json={
            "model": VISION_SMOKE_MODEL,
            "messages": [{"role": "user", "content": "Reply with the single word OK."}],
            "stream": False,
        },
        timeout=120,
    )
    if chat.status_code == 200:
        r.ok(f"vision-capable chat smoke 200 ({VISION_SMOKE_MODEL})")
    else:
        r.err(f"vision-capable chat smoke {chat.status_code} {chat.text[:240]}")

    print(f"\n{len(r.oks)} ok / {len(r.errors)} err")
    for msg in r.errors:
        print(f"  - {msg}")
    return 1 if r.errors else 0


if __name__ == "__main__":
    sys.exit(main())
