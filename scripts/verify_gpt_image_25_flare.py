#!/usr/bin/env python3
"""Accept GPT Image 2.5 Flare as public Images-API model. GPT Image 2 must stay public.

Optional live smoke: VERIFY_IMAGE_SMOKE=1 (default) sends one short generate via chat.
Does not public Sunburst. Does not require picker == ACTIVE_MODEL_IDS.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import GPT_IMAGE_25_FLARE_DESCRIPTION, GPT_IMAGE_25_FLARE_ID, PIPE

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
OPENWEBUI_PASSWORD = os.environ.get("OPENWEBUI_PASSWORD")
IMAGE2_ID = f"{PIPE}.openai.gpt-image-2"
SUNBURST_ID = f"{PIPE}.openai.gpt-image-2.5-sunburst"
SMOKE = os.environ.get("VERIFY_IMAGE_SMOKE", "1") != "0"


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


def is_public(grants: list) -> bool:
    return any(g.get("principal_id") == "*" and g.get("permission") == "read" for g in (grants or []))


def get_model(h: dict[str, str], model_id: str) -> dict:
    resp = requests.get(
        f"{OPENWEBUI_URL}/api/v1/models/model",
        headers=h,
        params={"id": model_id},
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"get {model_id}: {resp.status_code} {resp.text[:200]}")
    return resp.json()


def _has_image(payload: Any) -> bool:
    text = json.dumps(payload, ensure_ascii=False)
    if "data:image/" in text or "image/png" in text or "image/jpeg" in text:
        return True
    if "/api/v1/files/" in text or "files/" in text and ".png" in text:
        return True
    if isinstance(payload, dict):
        msg = ((payload.get("choices") or [{}])[0].get("message") or {})
        if msg.get("images"):
            return True
        content = msg.get("content")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and (
                    part.get("type") in ("image_url", "image") or part.get("image_url")
                ):
                    return True
        if isinstance(content, str) and ("![](" in content or "data:image" in content):
            return True
    return False


def main() -> int:
    h = headers(signin())
    errors: list[str] = []
    oks: list[str] = []

    flare = get_model(h, GPT_IMAGE_25_FLARE_ID)
    image2 = get_model(h, IMAGE2_ID)
    for label, model, want_public in (
        ("flare", flare, True),
        ("image-2", image2, True),
    ):
        if model.get("is_active") is False:
            errors.append(f"{label} inactive")
        else:
            oks.append(f"{label} active")
        if is_public(model.get("access_grants") or []) != want_public:
            errors.append(f"{label} public={is_public(model.get('access_grants') or [])} want {want_public}")
        else:
            oks.append(f"{label} public")
        caps = (model.get("meta") or {}).get("capabilities") or {}
        if label == "flare":
            for key in ("code_interpreter", "web_search", "builtin_tools", "terminal"):
                if caps.get(key):
                    errors.append(f"flare {key} still true")
            if caps.get("builtin_tools") is not False:
                errors.append(f"flare builtin_tools={caps.get('builtin_tools')} want false")
            else:
                oks.append("flare image caps stripped")
            desc = (model.get("meta") or {}).get("description") or ""
            if desc != GPT_IMAGE_25_FLARE_DESCRIPTION:
                errors.append(f"flare description mismatch: {desc[:80]}")
            else:
                oks.append("flare description")

    sun = requests.get(
        f"{OPENWEBUI_URL}/api/v1/models/model",
        headers=h,
        params={"id": SUNBURST_ID},
        timeout=30,
    )
    if sun.status_code == 200:
        if is_public(sun.json().get("access_grants") or []):
            errors.append("sunburst unexpectedly public")
        else:
            oks.append("sunburst not public")

    runtime = requests.get(f"{OPENWEBUI_URL}/api/models", headers=h, timeout=90).json().get("data") or []
    runtime_ids = {m["id"] for m in runtime}
    if GPT_IMAGE_25_FLARE_ID not in runtime_ids:
        errors.append("flare missing from runtime picker")
    else:
        oks.append("flare in picker")
    if IMAGE2_ID not in runtime_ids:
        errors.append("image-2 missing from runtime picker")
    else:
        oks.append("image-2 still in picker")

    if SMOKE:
        payload = {
            "model": GPT_IMAGE_25_FLARE_ID,
            "messages": [
                {
                    "role": "user",
                    "content": "Generate a simple image: a solid red circle on a white background. No text.",
                }
            ],
            "stream": False,
        }
        resp = requests.post(
            f"{OPENWEBUI_URL}/api/chat/completions",
            headers=h,
            json=payload,
            timeout=240,
        )
        text = (resp.text or "")[:500]
        if resp.status_code != 200:
            errors.append(f"smoke flare {resp.status_code} {text}")
        elif "cannot be used with the chat/completions endpoint" in text:
            errors.append(f"smoke flare still on chat endpoint {text}")
        elif not _has_image(resp.json()):
            errors.append(f"smoke flare 200 but no image payload {text}")
        else:
            oks.append(f"smoke flare {resp.status_code} image")
    else:
        print("INFO image smoke skipped (VERIFY_IMAGE_SMOKE=0)")

    for msg in oks:
        print(f"OK  {msg}")
    for msg in errors:
        print(f"ERR {msg}")
    print(f"verify flare: {len(oks)} ok, {len(errors)} err")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
