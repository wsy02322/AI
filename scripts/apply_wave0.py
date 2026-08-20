#!/usr/bin/env python3
"""Wave 0 apply: Sonar/image capabilities + Pipe task models. Merge-only. No global feature kills."""

from __future__ import annotations

import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import (
    CHAT_KEEP_CODE_INTERPRETER,
    DEFAULT_MODEL,
    IMAGE_MODEL_IDS,
    SONAR_MODEL_IDS,
    TASK_MODEL,
)

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


def update_model(h: dict[str, str], model: dict, meta: dict) -> None:
    payload = {
        "id": model["id"],
        "name": model["name"],
        "meta": meta,
        "params": model.get("params") or {},
        "is_active": model.get("is_active", True),
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


def strip_tool_caps(caps: dict, *, image: bool) -> dict:
    out = dict(caps or {})
    out["code_interpreter"] = False
    out["web_search"] = False
    if image:
        out["builtin_tools"] = False
        out["terminal"] = False
    return out


def apply_capabilities(h: dict[str, str]) -> None:
    for model_id in SONAR_MODEL_IDS:
        model = get_model(h, model_id)
        meta = dict(model.get("meta") or {})
        before = dict(meta.get("capabilities") or {})
        after = strip_tool_caps(before, image=False)
        if before == after:
            print(f"caps unchanged {model_id}")
            continue
        meta["capabilities"] = after
        update_model(h, model, meta)
        print(f"caps sonar {model.get('name')}: code_interpreter {before.get('code_interpreter')} -> False")

    for model_id in IMAGE_MODEL_IDS:
        model = get_model(h, model_id)
        meta = dict(model.get("meta") or {})
        before = dict(meta.get("capabilities") or {})
        after = strip_tool_caps(before, image=True)
        if before == after:
            print(f"caps unchanged {model_id}")
            continue
        meta["capabilities"] = after
        update_model(h, model, meta)
        print(
            f"caps image {model.get('name')}: "
            f"code={before.get('code_interpreter')} builtin={before.get('builtin_tools')} "
            f"terminal={before.get('terminal')} -> false"
        )

    for model_id in CHAT_KEEP_CODE_INTERPRETER:
        model = get_model(h, model_id)
        caps = (model.get("meta") or {}).get("capabilities") or {}
        print(f"keep chat {model.get('name')} code_interpreter={caps.get('code_interpreter')}")


def apply_task_models(h: dict[str, str]) -> None:
    cfg = requests.get(f"{OPENWEBUI_URL}/api/v1/tasks/config", headers=h, timeout=30)
    if cfg.status_code != 200:
        raise RuntimeError(f"get tasks: {cfg.status_code} {cfg.text[:200]}")
    payload = dict(cfg.json())
    payload["TASK_MODEL"] = TASK_MODEL
    payload["TASK_MODEL_EXTERNAL"] = TASK_MODEL
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/tasks/config/update",
        headers=h,
        json=payload,
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"tasks update: {resp.status_code} {resp.text[:400]}")
    saved = resp.json()
    print(f"TASK_MODEL={saved.get('TASK_MODEL')}")
    print(f"TASK_MODEL_EXTERNAL={saved.get('TASK_MODEL_EXTERNAL')}")
    print(f"DEFAULT_MODEL (unchanged here)={DEFAULT_MODEL}")


def main() -> int:
    h = headers(signin())
    apply_capabilities(h)
    apply_task_models(h)
    print("wave0 apply ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
