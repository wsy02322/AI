#!/usr/bin/env python3
"""Disable Pipe catalog rows outside ACTIVE_MODEL_IDS (picker == 25 public).

Keeps the principle series (Astra 23 + GPT Image 2.5 Flare/Sunburst + Image 2).
Does not call models/sync. Does not rewrite banners. Does not strip grants on
kept rows. Unconfirmed families / latest aliases / video / batch become inactive.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import ACTIVE_MODEL_IDS, PIPE, RETIRED_MODEL_IDS

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
OPENWEBUI_PASSWORD = os.environ.get("OPENWEBUI_PASSWORD")


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


def get_model(h: dict[str, str], model_id: str) -> dict[str, Any] | None:
    resp = requests.get(
        f"{OPENWEBUI_URL}/api/v1/models/model",
        headers=h,
        params={"id": model_id},
        timeout=30,
    )
    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        raise RuntimeError(f"get {model_id}: {resp.status_code} {resp.text[:200]}")
    return resp.json()


def update_active(h: dict[str, str], model: dict[str, Any], active: bool) -> bool:
    if model.get("is_active") == active:
        return False
    payload = {
        "id": model["id"],
        "name": model["name"],
        "meta": model.get("meta") or {},
        "params": model.get("params") or {},
        "is_active": active,
        "access_grants": model.get("access_grants") or [],
    }
    for attempt in range(4):
        resp = requests.post(
            f"{OPENWEBUI_URL}/api/v1/models/model/update",
            headers=h,
            json=payload,
            timeout=30,
        )
        if resp.status_code == 200:
            return True
        if resp.status_code == 429:
            time.sleep(4 * (attempt + 1))
            continue
        raise RuntimeError(f"update {model['id']}: {resp.status_code} {resp.text[:300]}")
    raise RuntimeError(f"update {model['id']}: rate limited")


def strip_public_grant(h: dict[str, str], model: dict[str, Any]) -> bool:
    grants = model.get("access_grants") or []
    kept = [
        g
        for g in grants
        if not (g.get("principal_id") == "*" and g.get("permission") == "read")
    ]
    if len(kept) == len(grants):
        return False
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/models/model/access/update",
        headers=h,
        json={"id": model["id"], "name": model.get("name") or model["id"], "access_grants": kept},
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"grant {model['id']}: {resp.status_code} {resp.text[:200]}")
    return True


def main() -> int:
    h = headers(signin())
    active_set = set(ACTIVE_MODEL_IDS)
    listed = requests.get(f"{OPENWEBUI_URL}/api/v1/models", headers=h, timeout=120).json().get("data") or []
    pipe_ids = [m["id"] for m in listed if (m.get("id") or "").startswith(f"{PIPE}.")]
    extras = [mid for mid in pipe_ids if mid not in active_set]
    print(f"admin {len(listed)} pipe={len(pipe_ids)} extras={len(extras)} keep={len(active_set)}")

    disabled = stripped = skipped = errors = 0
    for model_id in extras:
        model = get_model(h, model_id)
        if not model:
            print(f"ERR missing {model_id}")
            errors += 1
            continue
        if strip_public_grant(h, model):
            stripped += 1
            print(f"strip * {model.get('name')}")
            model = get_model(h, model_id) or model
        if update_active(h, model, False):
            disabled += 1
            print(f"disable {model.get('name')}")
        else:
            skipped += 1

    for model_id in RETIRED_MODEL_IDS:
        model = get_model(h, model_id)
        if not model:
            continue
        if strip_public_grant(h, model):
            stripped += 1
            print(f"strip retired * {model.get('name')}")
            model = get_model(h, model_id) or model
        if update_active(h, model, False):
            disabled += 1
            print(f"disable retired {model.get('name')}")

    runtime = requests.get(f"{OPENWEBUI_URL}/api/models", headers=h, timeout=120).json().get("data") or []
    runtime_ids = {m["id"] for m in runtime}
    print(f"done: disabled={disabled} stripped={stripped} skipped={skipped} errors={errors}")
    print(f"runtime picker {len(runtime)} want {len(active_set)}")
    extra = sorted(runtime_ids - active_set)
    missing = sorted(active_set - runtime_ids)
    if extra:
        print(f"ERR extra in picker: {extra}")
        errors += len(extra)
    if missing:
        print(f"ERR missing from picker: {missing}")
        errors += len(missing)
    if not extra and not missing:
        print("picker == principle series")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
