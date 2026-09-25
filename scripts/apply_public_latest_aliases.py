#!/usr/bin/env python3
"""Point public models at OpenRouter auto-updating Latest aliases.

For each public snapshot that has a `~…-latest` row, turn that alias on and
public, and turn the snapshot off. Also point the new-chat default, task
models, and the Opus pin at the alias. Does not touch valves, banners, or
models/sync.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import (
    DEFAULT_MODELS,
    PIPE,
    PINNED_MODELS,
    TASK_MODEL,
)

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
OPENWEBUI_PASSWORD = os.environ.get("OPENWEBUI_PASSWORD")
PUBLIC_GRANT = {"principal_type": "user", "principal_id": "*", "permission": "read"}

# snapshot short id -> latest short id. Snapshot loses public and is_active.
SWAPS = [
    ("anthropic.claude-fable-5.1", "~anthropic.claude-fable-latest"),
    ("anthropic.claude-opus-5.5", "~anthropic.claude-opus-latest"),
    ("deepseek.deepseek-v4-pro-0813", "~deepseek.deepseek-pro-latest"),
    ("google.gemini-3.1-pro-preview", "~google.gemini-pro-latest"),
    ("google.gemini-3.8-flash", "~google.gemini-flash-latest"),
    ("moonshotai.kimi-k3", "~moonshotai.kimi-latest"),
    ("openai.gpt-6-astra", "~openai.gpt-astra-latest"),
    ("openai.gpt-5.6-sol", "~openai.gpt-sol-latest"),
    ("x-ai.grok-4.7", "~x-ai.grok-latest"),
]


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


def full_id(short: str) -> str:
    return f"{PIPE}.{short}"


def is_public(grants: list) -> bool:
    return any(
        g.get("principal_id") == "*" and g.get("permission") == "read" for g in (grants or [])
    )


def get_model(h: dict[str, str], model_id: str) -> dict[str, Any]:
    resp = requests.get(
        f"{OPENWEBUI_URL}/api/v1/models/model",
        headers=h,
        params={"id": model_id},
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"get {model_id}: {resp.status_code} {resp.text[:240]}")
    return resp.json()


def set_active(h: dict[str, str], model: dict[str, Any], active: bool) -> None:
    if model.get("is_active") == active:
        return
    payload = {
        "id": model["id"],
        "name": model["name"],
        "meta": model.get("meta") or {},
        "params": model.get("params") or {},
        "is_active": active,
        "access_grants": model.get("access_grants") or [],
    }
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/models/model/update",
        headers=h,
        json=payload,
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"update {model['id']}: {resp.status_code} {resp.text[:300]}")


def set_public(h: dict[str, str], model_id: str, name: str, public: bool) -> None:
    grants = [PUBLIC_GRANT] if public else []
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/models/model/access/update",
        headers=h,
        json={"id": model_id, "name": name, "access_grants": grants},
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"access {model_id}: {resp.status_code} {resp.text[:300]}")


def apply_swaps(h: dict[str, str]) -> None:
    for snapshot, alias in SWAPS:
        snap_id = full_id(snapshot)
        alias_id = full_id(alias)
        snap = get_model(h, snap_id)
        latest = get_model(h, alias_id)
        set_active(h, latest, True)
        set_public(h, alias_id, latest.get("name") or alias, True)
        set_public(h, snap_id, snap.get("name") or snapshot, False)
        snap = get_model(h, snap_id)
        set_active(h, snap, False)
        print(f"public {latest.get('name')}  <=  {snap.get('name')}")


def apply_defaults(h: dict[str, str]) -> None:
    models_cfg = requests.get(f"{OPENWEBUI_URL}/api/v1/configs/models", headers=h, timeout=30)
    if models_cfg.status_code != 200:
        raise RuntimeError(f"get models config: {models_cfg.status_code} {models_cfg.text[:240]}")
    cfg = models_cfg.json()
    pinned = cfg.get("DEFAULT_PINNED_MODELS") or ""
    pinned = pinned.replace(
        f"{PIPE}.anthropic.claude-opus-5",
        f"{PIPE}.~anthropic.claude-opus-latest",
    )
    # Keep Sol Pro. Do not rewrite claude-opus-5.5 if it was never the pin.
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/configs/models",
        headers=h,
        json={
            "DEFAULT_MODELS": DEFAULT_MODELS,
            "DEFAULT_PINNED_MODELS": pinned,
            "MODEL_ORDER_LIST": cfg.get("MODEL_ORDER_LIST"),
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"models config: {resp.status_code} {resp.text[:300]}")
    print(f"DEFAULT_MODELS={resp.json().get('DEFAULT_MODELS')}")
    print(f"DEFAULT_PINNED_MODELS={resp.json().get('DEFAULT_PINNED_MODELS')}")

    tasks = requests.get(f"{OPENWEBUI_URL}/api/v1/tasks/config", headers=h, timeout=30)
    if tasks.status_code != 200:
        raise RuntimeError(f"get tasks: {tasks.status_code} {tasks.text[:200]}")
    payload = dict(tasks.json())
    payload["TASK_MODEL"] = TASK_MODEL
    payload["TASK_MODEL_EXTERNAL"] = TASK_MODEL
    saved = requests.post(
        f"{OPENWEBUI_URL}/api/v1/tasks/config/update",
        headers=h,
        json=payload,
        timeout=30,
    )
    if saved.status_code != 200:
        raise RuntimeError(f"tasks update: {saved.status_code} {saved.text[:300]}")
    print(f"TASK_MODEL={saved.json().get('TASK_MODEL')}")
    print(f"FOLLOW_UP={saved.json().get('ENABLE_FOLLOW_UP_GENERATION')}")
    missing = [mid for mid in PINNED_MODELS if mid not in (resp.json().get("DEFAULT_PINNED_MODELS") or "")]
    if missing:
        raise RuntimeError(f"pinned missing after update: {missing}")


def verify(h: dict[str, str]) -> int:
    errors = 0
    for snapshot, alias in SWAPS:
        latest = get_model(h, full_id(alias))
        snap = get_model(h, full_id(snapshot))
        if not latest.get("is_active") or not is_public(latest.get("access_grants") or []):
            print(f"ERR alias not public+active {alias}")
            errors += 1
        else:
            print(f"OK {latest.get('name')}")
        if snap.get("is_active") or is_public(snap.get("access_grants") or []):
            print(f"ERR snapshot still on {snapshot} active={snap.get('is_active')} public={is_public(snap.get('access_grants') or [])}")
            errors += 1
    runtime = requests.get(f"{OPENWEBUI_URL}/api/models", headers=h, timeout=120).json().get("data") or []
    ids = {m.get("id") for m in runtime}
    for _, alias in SWAPS:
        if full_id(alias) not in ids:
            print(f"ERR picker missing {alias}")
            errors += 1
    for snapshot, _ in SWAPS:
        if full_id(snapshot) in ids:
            print(f"ERR picker still has {snapshot}")
            errors += 1
    print(f"picker {len(runtime)}")
    return errors


def main() -> int:
    h = headers(signin())
    apply_swaps(h)
    apply_defaults(h)
    errors = verify(h)
    if errors:
        print(f"verify errors: {errors}")
        return 1
    print("public latest aliases ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
