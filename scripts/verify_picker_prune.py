#!/usr/bin/env python3
"""Accept picker == ACTIVE_MODEL_IDS (25 public). No extras, no missing keepers."""

from __future__ import annotations

import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import ACTIVE_MODEL_IDS, PUBLIC_MODEL_IDS

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


def is_public(grants: list) -> bool:
    return any(g.get("principal_id") == "*" and g.get("permission") == "read" for g in (grants or []))


def main() -> int:
    token = signin()
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    oks: list[str] = []
    errors: list[str] = []
    runtime = requests.get(f"{OPENWEBUI_URL}/api/models", headers=h, timeout=90).json().get("data") or []
    runtime_ids = {m["id"] for m in runtime}
    want = set(ACTIVE_MODEL_IDS)
    if runtime_ids != want:
        extra = sorted(runtime_ids - want)
        missing = sorted(want - runtime_ids)
        if extra:
            errors.append(f"picker extra {extra}")
        if missing:
            errors.append(f"picker missing {missing}")
    else:
        oks.append(f"picker {len(runtime)} == public {len(PUBLIC_MODEL_IDS)}")

    for mid in PUBLIC_MODEL_IDS:
        detail = requests.get(
            f"{OPENWEBUI_URL}/api/v1/models/model",
            headers=h,
            params={"id": mid},
            timeout=30,
        )
        if detail.status_code != 200:
            errors.append(f"get fail {mid} {detail.status_code}")
            continue
        model = detail.json()
        if model.get("is_active") is False:
            errors.append(f"inactive public {mid}")
        if not is_public(model.get("access_grants") or []):
            errors.append(f"not public {mid}")
        else:
            oks.append(f"public {model.get('name')}")

    for msg in oks:
        print(f"OK  {msg}")
    for msg in errors:
        print(f"ERR {msg}")
    print(f"verify picker: {len(oks)} ok, {len(errors)} err")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
