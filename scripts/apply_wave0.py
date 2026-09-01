#!/usr/bin/env python3
"""Wave 0 apply: Sonar/image capabilities + Pipe task models. Merge-only.

Pins ENABLE_FOLLOW_UP_GENERATION=false (reply chips; empty-chat suggestions stay empty).
Does not kill Autocomplete / Title / other global features.
"""

from __future__ import annotations

import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import (
    CHAT_KEEP_CODE_INTERPRETER,
    DEFAULT_MODELS,
    IMAGE_MODEL_IDS,
    SONAR_MODEL_IDS,
    TASK_FOLLOW_UP_ENABLE,
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
    # OWUI 0.11 defaults missing builtin_tools -> True and injects get_current_timestamp.
    out["builtin_tools"] = False
    if image:
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
        print(
            f"caps sonar {model.get('name')}: "
            f"code={before.get('code_interpreter')} builtin={before.get('builtin_tools')} -> False"
        )

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


def apply_default_chat_model(h: dict[str, str]) -> None:
    models_cfg = requests.get(f"{OPENWEBUI_URL}/api/v1/configs/models", headers=h, timeout=30)
    if models_cfg.status_code != 200:
        raise RuntimeError(f"get models config: {models_cfg.status_code}")
    cfg = models_cfg.json()
    payload = {
        "DEFAULT_MODELS": DEFAULT_MODELS,
        "DEFAULT_PINNED_MODELS": cfg.get("DEFAULT_PINNED_MODELS"),
        "MODEL_ORDER_LIST": cfg.get("MODEL_ORDER_LIST"),
    }
    resp = requests.post(f"{OPENWEBUI_URL}/api/v1/configs/models", headers=h, json=payload, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"models config: {resp.status_code} {resp.text[:400]}")
    saved = resp.json()
    print(f"DEFAULT_MODELS={saved.get('DEFAULT_MODELS')}")


def disable_global_image_gen(h: dict[str, str]) -> None:
    img = requests.get(f"{OPENWEBUI_URL}/api/v1/images/config", headers=h, timeout=30)
    if img.status_code != 200:
        raise RuntimeError(f"get images config: {img.status_code}")
    payload = dict(img.json())
    payload["ENABLE_IMAGE_GENERATION"] = False
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/images/config/update",
        headers=h,
        json=payload,
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"images config: {resp.status_code} {resp.text[:400]}")
    saved = resp.json()
    print(f"ENABLE_IMAGE_GENERATION={saved.get('ENABLE_IMAGE_GENERATION')}")
    cfg = requests.get(f"{OPENWEBUI_URL}/api/config", headers=h, timeout=30).json()
    feat = (cfg.get("features") or {}).get("enable_image_generation")
    print(f"features.enable_image_generation={feat}")


def apply_task_models(h: dict[str, str]) -> None:
    cfg = requests.get(f"{OPENWEBUI_URL}/api/v1/tasks/config", headers=h, timeout=30)
    if cfg.status_code != 200:
        raise RuntimeError(f"get tasks: {cfg.status_code} {cfg.text[:200]}")
    payload = dict(cfg.json())
    payload["TASK_MODEL"] = TASK_MODEL
    payload["TASK_MODEL_EXTERNAL"] = TASK_MODEL
    payload["ENABLE_FOLLOW_UP_GENERATION"] = TASK_FOLLOW_UP_ENABLE
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
    print(f"ENABLE_FOLLOW_UP_GENERATION={saved.get('ENABLE_FOLLOW_UP_GENERATION')}")
    print(f"DEFAULT_MODEL (task)={TASK_MODEL}")


def main() -> int:
    h = headers(signin())
    apply_capabilities(h)
    apply_default_chat_model(h)
    disable_global_image_gen(h)
    apply_task_models(h)
    print("wave0 apply ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
