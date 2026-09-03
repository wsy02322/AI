#!/usr/bin/env python3
"""Recreate the public model rows + access_grants after a catalog wipe.

Also strips leftover `*` read from extra / retired / non-public picker rows
so verify_stack does not miss a 21st public model.

Does NOT call POST /api/v1/models/sync (empty sync deletes every DB model).
Requires the Pipe catalog to already be visible on GET /api/models.
"""

from __future__ import annotations

import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import EXTRA_ACTIVE_MODEL_IDS, PUBLIC_MODEL_IDS, RETIRED_MODEL_IDS

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


def _get_model(h: dict[str, str], model_id: str) -> tuple[int, dict | None]:
    for attempt in range(4):
        resp = requests.get(
            f"{OPENWEBUI_URL}/api/v1/models/model",
            headers=h,
            params={"id": model_id},
            timeout=30,
        )
        if resp.status_code == 200:
            return 200, resp.json()
        if resp.status_code == 404:
            return 404, None
        if resp.status_code == 429:
            time.sleep(4 * (attempt + 1))
            continue
        return resp.status_code, None
    return 429, None


def _access_update(h: dict[str, str], model_id: str, name: str, grants: list) -> tuple[int, dict | None]:
    payload = {"id": model_id, "name": name or model_id, "access_grants": grants}
    for attempt in range(4):
        resp = requests.post(
            f"{OPENWEBUI_URL}/api/v1/models/model/access/update",
            headers=h,
            json=payload,
            timeout=30,
        )
        if resp.status_code == 200:
            return 200, resp.json()
        if resp.status_code == 429:
            time.sleep(4 * (attempt + 1))
            continue
        return resp.status_code, None
    return 429, None


def grant_public(h: dict[str, str]) -> int:
    listed = requests.get(f"{OPENWEBUI_URL}/api/models", headers=h, timeout=120).json().get("data") or []
    by_id = {m["id"]: m for m in listed}
    print(f"runtime catalog {len(listed)}")
    errors = 0
    for model_id in PUBLIC_MODEL_IDS:
        model = by_id.get(model_id)
        if not model:
            status, detail = _get_model(h, model_id)
            if status != 200 or not detail:
                print(f"ERR missing in catalog {model_id}")
                errors += 1
                continue
            model = detail
        status, body = _access_update(
            h, model_id, model.get("name") or model_id, [PUBLIC_GRANT]
        )
        if status != 200 or not body:
            print(f"ERR grant {model_id} {status}")
            errors += 1
            continue
        if not is_public(body.get("access_grants") or []):
            print(f"ERR not public after grant {model_id}")
            errors += 1
            continue
        print(f"OK public {model.get('name')}")
    return errors


def strip_non_public_star(h: dict[str, str]) -> int:
    listed = requests.get(f"{OPENWEBUI_URL}/api/models", headers=h, timeout=120).json().get("data") or []
    inspect = {m["id"] for m in listed}
    inspect.update(EXTRA_ACTIVE_MODEL_IDS)
    inspect.update(RETIRED_MODEL_IDS)
    public_set = set(PUBLIC_MODEL_IDS)
    errors = 0
    stripped = 0
    for model_id in sorted(inspect):
        if model_id in public_set:
            continue
        status, model = _get_model(h, model_id)
        if status == 404:
            continue
        if status != 200 or not model:
            print(f"ERR get {model_id} {status}")
            errors += 1
            continue
        if not is_public(model.get("access_grants") or []):
            continue
        status, body = _access_update(h, model_id, model.get("name") or model_id, [])
        if status != 200 or not body:
            print(f"ERR strip {model_id} {status}")
            errors += 1
            continue
        if is_public(body.get("access_grants") or []):
            print(f"ERR still public after strip {model_id}")
            errors += 1
            continue
        stripped += 1
        print(f"OK stripped * {model.get('name')}")
    print(f"stripped extra public grants: {stripped}")
    return errors


def main() -> int:
    h = headers(signin())
    errors = grant_public(h) + strip_non_public_star(h)
    if errors:
        print(f"restore errors: {errors}")
        return 1
    print("public grants restore ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
