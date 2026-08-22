#!/usr/bin/env python3
"""Disable catalog models that are not in the 19 public list; keep public active."""

from __future__ import annotations

import os
import sys
import time
from typing import Any

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import ACTIVE_MODEL_IDS, PIPE

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


def main() -> int:
    h = headers(signin())
    active_set = set(ACTIVE_MODEL_IDS)
    listed = requests.get(f"{OPENWEBUI_URL}/api/v1/models", headers=h, timeout=120).json().get("data") or []
    pipe_models = [m for m in listed if (m.get("id") or "").startswith(f"{PIPE}.")]
    print(f"catalog {len(listed)} total, {len(pipe_models)} pipe models")

    enabled = disabled = skipped = errors = 0
    for idx, summary in enumerate(pipe_models, 1):
        model_id = summary["id"]
        want_active = model_id in active_set
        detail = requests.get(
            f"{OPENWEBUI_URL}/api/v1/models/model",
            headers=h,
            params={"id": model_id},
            timeout=30,
        )
        if detail.status_code != 200:
            print(f"ERR get {model_id} {detail.status_code}")
            errors += 1
            continue
        model = detail.json()
        if update_active(h, model, want_active):
            if want_active:
                enabled += 1
                print(f"enable {model.get('name')}")
            else:
                disabled += 1
            if disabled and disabled % 50 == 0:
                print(f"  ... disabled {disabled}")
        else:
            skipped += 1

    runtime = requests.get(f"{OPENWEBUI_URL}/api/models", headers=h, timeout=120).json().get("data") or []
    runtime_ids = {m["id"] for m in runtime}
    print(f"done: enabled={enabled} disabled={disabled} skipped={skipped} errors={errors}")
    print(f"runtime picker {len(runtime)} models")
    extra = runtime_ids - active_set
    missing = active_set - runtime_ids
    if extra:
        print(f"ERR extra in picker: {sorted(extra)}")
        errors += len(extra)
    if missing:
        print(f"ERR missing from picker: {sorted(missing)}")
        errors += len(missing)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
