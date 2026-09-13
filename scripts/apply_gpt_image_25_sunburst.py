#!/usr/bin/env python3
"""ST-IMG: public GPT Image 2.5 Sunburst after Flare passed. Keep GPT Image 2.

Merge-only on the Sunburst row (plus Flare/Image 2 descriptions). Does not run
catalog visibility. Does not rewrite banners (live is usage-guide-v7).
"""

from __future__ import annotations

import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apply_wave0 import strip_tool_caps
from stack_contract import (
    GPT_IMAGE_25_FLARE_DESCRIPTION,
    GPT_IMAGE_25_FLARE_ID,
    GPT_IMAGE_25_SUNBURST_DESCRIPTION,
    GPT_IMAGE_25_SUNBURST_ID,
    PIPE,
)

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
OPENWEBUI_PASSWORD = os.environ.get("OPENWEBUI_PASSWORD")
PUBLIC_GRANT = {"principal_type": "user", "principal_id": "*", "permission": "read"}
IMAGE2_ID = f"{PIPE}.openai.gpt-image-2"
IMAGE2_DESCRIPTION = (
    "ALTERNATE IMAGE MODEL. Switch here before asking for pictures. "
    "Prefer GPT Image 2.5 Flare for everyday OpenAI images."
)


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


def update_model(h: dict[str, str], model: dict, meta: dict, grants: list) -> dict:
    payload = {
        "id": model["id"],
        "name": model["name"],
        "meta": meta,
        "params": model.get("params") or {},
        "is_active": True,
        "access_grants": grants,
    }
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/models/model/update",
        headers=h,
        json=payload,
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"update {model['id']}: {resp.status_code} {resp.text[:300]}")
    return resp.json()


def grant_public(h: dict[str, str], model: dict) -> dict:
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/models/model/access/update",
        headers=h,
        json={
            "id": model["id"],
            "name": model.get("name") or model["id"],
            "access_grants": [PUBLIC_GRANT],
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"grant {model['id']}: {resp.status_code} {resp.text[:200]}")
    return resp.json()


def refresh_catalog(h: dict[str, str]) -> None:
    resp = requests.get(f"{OPENWEBUI_URL}/api/models", headers=h, params={"refresh": "true"}, timeout=180)
    if resp.status_code != 200:
        raise RuntimeError(f"refresh catalog: {resp.status_code} {resp.text[:200]}")
    print(f"catalog refresh {len(resp.json().get('data') or [])}")


def apply_image_row(h: dict[str, str], model_id: str, description: str) -> None:
    model = get_model(h, model_id)
    meta = dict(model.get("meta") or {})
    before_caps = dict(meta.get("capabilities") or {})
    meta["capabilities"] = strip_tool_caps(before_caps, image=True)
    meta["description"] = description
    grants = model.get("access_grants") or []
    update_model(h, model, meta, grants)
    saved = grant_public(h, model)
    grants = saved.get("access_grants") or []
    public = any(g.get("principal_id") == "*" and g.get("permission") == "read" for g in grants)
    if not public:
        raise RuntimeError(f"{model_id} not public after grant")
    print(f"ok {model.get('name')} public active caps stripped")


def main() -> int:
    h = headers(signin())
    refresh_catalog(h)
    apply_image_row(h, GPT_IMAGE_25_SUNBURST_ID, GPT_IMAGE_25_SUNBURST_DESCRIPTION)
    apply_image_row(h, GPT_IMAGE_25_FLARE_ID, GPT_IMAGE_25_FLARE_DESCRIPTION)
    apply_image_row(h, IMAGE2_ID, IMAGE2_DESCRIPTION)
    print("gpt-image-2.5-sunburst apply ok (flare + image-2 kept public)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
