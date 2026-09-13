#!/usr/bin/env python3
"""Accept GPT Image 2.5 Sunburst as public Images-API model.

Flare and GPT Image 2 must stay public. Optional live smoke: VERIFY_IMAGE_SMOKE=1.
Does not require picker == ACTIVE_MODEL_IDS.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import (
    GPT_IMAGE_25_FLARE_ID,
    GPT_IMAGE_25_SUNBURST_DESCRIPTION,
    GPT_IMAGE_25_SUNBURST_ID,
    PIPE,
)

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
OPENWEBUI_PASSWORD = os.environ.get("OPENWEBUI_PASSWORD")
IMAGE2_ID = f"{PIPE}.openai.gpt-image-2"
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
    if "/api/v1/files/" in text or ("files/" in text and ".png" in text):
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


def _check_row(oks: list[str], errors: list[str], label: str, model: dict, *, check_caps: bool, description: str | None) -> None:
    if model.get("is_active") is False:
        errors.append(f"{label} inactive")
    else:
        oks.append(f"{label} active")
    if not is_public(model.get("access_grants") or []):
        errors.append(f"{label} not public")
    else:
        oks.append(f"{label} public")
    if check_caps:
        caps = (model.get("meta") or {}).get("capabilities") or {}
        for key in ("code_interpreter", "web_search", "builtin_tools", "terminal"):
            if caps.get(key):
                errors.append(f"{label} {key} still true")
        if caps.get("builtin_tools") is not False:
            errors.append(f"{label} builtin_tools={caps.get('builtin_tools')} want false")
        else:
            oks.append(f"{label} image caps stripped")
    if description is not None:
        desc = (model.get("meta") or {}).get("description") or ""
        if desc != description:
            errors.append(f"{label} description mismatch: {desc[:80]}")
        else:
            oks.append(f"{label} description")


def main() -> int:
    h = headers(signin())
    errors: list[str] = []
    oks: list[str] = []

    sun = get_model(h, GPT_IMAGE_25_SUNBURST_ID)
    flare = get_model(h, GPT_IMAGE_25_FLARE_ID)
    image2 = get_model(h, IMAGE2_ID)
    _check_row(oks, errors, "sunburst", sun, check_caps=True, description=GPT_IMAGE_25_SUNBURST_DESCRIPTION)
    _check_row(oks, errors, "flare", flare, check_caps=False, description=None)
    _check_row(oks, errors, "image-2", image2, check_caps=False, description=None)

    runtime = requests.get(f"{OPENWEBUI_URL}/api/models", headers=h, timeout=90).json().get("data") or []
    runtime_ids = {m["id"] for m in runtime}
    for label, mid in (
        ("sunburst", GPT_IMAGE_25_SUNBURST_ID),
        ("flare", GPT_IMAGE_25_FLARE_ID),
        ("image-2", IMAGE2_ID),
    ):
        if mid not in runtime_ids:
            errors.append(f"{label} missing from runtime picker")
        else:
            oks.append(f"{label} in picker")

    if SMOKE:
        payload = {
            "model": GPT_IMAGE_25_SUNBURST_ID,
            "messages": [
                {
                    "role": "user",
                    "content": "Generate a simple image: a solid blue circle on a white background. No text.",
                }
            ],
            "stream": False,
        }
        resp = requests.post(
            f"{OPENWEBUI_URL}/api/chat/completions",
            headers=h,
            json=payload,
            timeout=300,
        )
        text = (resp.text or "")[:500]
        if resp.status_code != 200:
            errors.append(f"smoke sunburst {resp.status_code} {text}")
        elif "cannot be used with the chat/completions endpoint" in text:
            errors.append(f"smoke sunburst still on chat endpoint {text}")
        elif not _has_image(resp.json()):
            errors.append(f"smoke sunburst 200 but no image payload {text}")
        else:
            oks.append(f"smoke sunburst {resp.status_code} image")
    else:
        print("INFO image smoke skipped (VERIFY_IMAGE_SMOKE=0)")

    for msg in oks:
        print(f"OK  {msg}")
    for msg in errors:
        print(f"ERR {msg}")
    print(f"verify sunburst: {len(oks)} ok, {len(errors)} err")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
