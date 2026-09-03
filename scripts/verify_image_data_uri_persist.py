#!/usr/bin/env python3
"""ST-13 acceptance: generated images land as file URLs, and inline ones can't 400.

Probes
  1. Pipe carries IMAGE_DATA_URI_PERSIST_V1 (and the older markers are intact).
  2. openrouter_image_context_guard carries IMAGE_CONTEXT_DATA_URI_CAP_V1, still global.
  3. Pipe valves ST-4/5/6 unchanged (read-only; this script never writes).
  4. E2E: generate one image; the reply must cite /api/v1/files/ and carry no data URI.
  5. E2E: replay that reply to Nano Banana 2 with a text-only edit -> 200
     (this is the exact turn that produced error id 77de6621c4ab134c).
  6. Synthetic: a ~2MB inline data URI in history -> 200, because the guard strips it.

Probes 4 and 5 each spend one image generation. During a provider outage they can fail
with 429/503; that is an upstream problem, not an ST-13 regression -- rerun later.

Usage: VERIFY_SMOKE=0 skips probes 4-6 (marker/config checks only).
"""

from __future__ import annotations

import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import GUARD_PATCH_MARKERS, PIPE, PIPE_PATCH_MARKERS, PIPE_VALVES_FALSE

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
OPENWEBUI_PASSWORD = os.environ.get("OPENWEBUI_PASSWORD")
SMOKE = os.environ.get("VERIFY_SMOKE", "1") != "0"

GUARD_ID = "openrouter_image_context_guard"
IMAGE_MODEL = f"{PIPE}.qwen.qwen-image-3-pro"
EDIT_MODEL = f"{PIPE}.google.gemini-3.1-flash-image"

# ~2MB of base64: as text that is far past a 131072-token window on its own.
SYNTHETIC_DATA_URI = "data:image/png;base64," + ("A" * 2_000_000)


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

    def info(self, msg: str) -> None:
        print(f"INFO {msg}")


def _login_candidates() -> list[str]:
    out: list[str] = []
    for value in (os.environ.get("OPENWEBUI_USERNAME"), os.environ.get("OPENWEBUI_EMAIL")):
        if value and value not in out:
            out.append(value)
    return out


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


def chat(h: dict, model: str, messages: list[dict], timeout: int = 300):
    return requests.post(
        f"{OPENWEBUI_URL}/api/chat/completions",
        headers=h,
        json={"model": model, "messages": messages, "stream": False},
        timeout=timeout,
    )


def reply_text(resp: requests.Response) -> str:
    try:
        choices = resp.json().get("choices") or []
        return (choices[0].get("message") or {}).get("content") or ""
    except (ValueError, IndexError, AttributeError):
        return ""


def main() -> int:
    r = Report()
    token = signin()
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    pipe = requests.get(f"{OPENWEBUI_URL}/api/v1/functions/id/{PIPE}", headers=h, timeout=60)
    content = pipe.json().get("content") or "" if pipe.status_code == 200 else ""
    if not content:
        r.err(f"pipe fetch failed {pipe.status_code}")
    for marker in PIPE_PATCH_MARKERS:
        if marker in content:
            r.ok(f"pipe marker {marker}")
        else:
            r.err(f"pipe missing marker {marker}")

    guard = requests.get(f"{OPENWEBUI_URL}/api/v1/functions/id/{GUARD_ID}", headers=h, timeout=60)
    guard_json = guard.json() if guard.status_code == 200 else {}
    guard_content = guard_json.get("content") or ""
    marker = GUARD_PATCH_MARKERS[GUARD_ID]
    if marker in guard_content:
        r.ok(f"guard marker {marker}")
    else:
        r.err(f"guard missing marker {marker}")
    if guard_json.get("is_active") and guard_json.get("is_global"):
        r.ok("guard active + global")
    else:
        r.err(f"guard flags active={guard_json.get('is_active')} global={guard_json.get('is_global')}")

    valves = requests.get(
        f"{OPENWEBUI_URL}/api/v1/functions/id/{PIPE}/valves", headers=h, timeout=30
    ).json()
    drifted = [k for k in PIPE_VALVES_FALSE if valves.get(k) is not False]
    if drifted:
        r.err(f"pipe valves drifted {drifted}")
    else:
        r.ok("pipe valves ST-4/5/6 unchanged")
    if valves.get("API_KEY"):
        r.ok("pipe API_KEY still configured")
    else:
        r.err("pipe API_KEY missing")

    if not SMOKE:
        r.info("VERIFY_SMOKE=0: skipping E2E probes 4-6")
        return _finish(r)

    gen = chat(h, IMAGE_MODEL, [{"role": "user", "content": "a plain red circle, white background"}])
    if gen.status_code != 200:
        r.err(f"image generate {gen.status_code} {gen.text[:200]}")
        return _finish(r)
    art = reply_text(gen)
    r.info(f"generated reply chars={len(art)}")
    if "data:image" in art:
        r.err(f"reply still inlines a data URI (chars={len(art)})")
    else:
        r.ok("reply carries no data URI")
    if "/api/v1/files/" in art:
        r.ok("reply cites OWUI file storage")
    else:
        r.err("reply has no /api/v1/files/ reference")
    if len(art) < 4096:
        r.ok(f"reply small enough to replay ({len(art)} chars)")
    else:
        r.err(f"reply too large to replay ({len(art)} chars)")

    followup = chat(
        h,
        EDIT_MODEL,
        [
            {"role": "user", "content": "a plain red circle, white background"},
            {"role": "assistant", "content": art},
            {"role": "user", "content": "make the circle blue, keep everything else identical"},
        ],
    )
    if followup.status_code == 200:
        r.ok("Nano Banana 2 follow-up on the generated canvas 200")
    else:
        r.err(f"follow-up {followup.status_code} {followup.text[:240]}")

    synthetic = chat(
        h,
        EDIT_MODEL,
        [
            {"role": "user", "content": "draw a frog"},
            {"role": "assistant", "content": f"![Generated image 1]({SYNTHETIC_DATA_URI})"},
            {"role": "user", "content": "make it night"},
        ],
    )
    if synthetic.status_code == 200:
        r.ok("2MB inline data URI in history 200 (guard stripped it)")
    else:
        r.err(f"synthetic data URI {synthetic.status_code} {synthetic.text[:240]}")

    return _finish(r)


def _finish(r: Report) -> int:
    print(f"\n{len(r.oks)} ok / {len(r.errors)} err")
    for err in r.errors:
        print(f"  - {err}")
    return 1 if r.errors else 0


if __name__ == "__main__":
    sys.exit(main())
