#!/usr/bin/env python3
"""Recreate the 19 public model rows + access_grants after a catalog wipe.

Does NOT call POST /api/v1/models/sync (empty sync deletes every DB model).
Requires the Pipe catalog to already be visible on GET /api/models.
"""

from __future__ import annotations

import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import PUBLIC_MODEL_IDS

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
OPENWEBUI_PASSWORD = os.environ.get("OPENWEBUI_PASSWORD")
PUBLIC_GRANT = {"principal_type": "user", "principal_id": "*", "permission": "read"}


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
    return any(
        g.get("principal_id") == "*" and g.get("permission") == "read" for g in (grants or [])
    )


def main() -> int:
    h = headers(signin())
    listed = requests.get(f"{OPENWEBUI_URL}/api/models", headers=h, timeout=120).json().get("data") or []
    by_id = {m["id"]: m for m in listed}
    print(f"runtime catalog {len(listed)}")
    errors = 0
    for model_id in PUBLIC_MODEL_IDS:
        model = by_id.get(model_id)
        if not model:
            print(f"ERR missing in catalog {model_id}")
            errors += 1
            continue
        resp = requests.post(
            f"{OPENWEBUI_URL}/api/v1/models/model/access/update",
            headers=h,
            json={
                "id": model_id,
                "name": model.get("name") or model_id,
                "access_grants": [PUBLIC_GRANT],
            },
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"ERR grant {model_id} {resp.status_code} {resp.text[:200]}")
            errors += 1
            continue
        if not is_public(resp.json().get("access_grants") or []):
            print(f"ERR not public after grant {model_id}")
            errors += 1
            continue
        print(f"OK public {model.get('name')}")
    if errors:
        print(f"restore errors: {errors}")
        return 1
    print("public grants restore ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
