#!/usr/bin/env python3
"""Keep only the confirmed model series active and public.

Astra stays public. Pinned four are Opus Latest, Nano Banana Pro,
Sol Latest, Astra Latest. Other active catalog rows are toggled off
and lose public grants. Does not delete rows, sync models, or touch valves.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import DEFAULT_MODELS, PINNED_MODELS, PIPE

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
OPENWEBUI_PASSWORD = os.environ.get("OPENWEBUI_PASSWORD")
PUBLIC_GRANT = {"principal_type": "user", "principal_id": "*", "permission": "read"}

KEEP_SHORT = [
    "perplexity.sonar-pro-search",
    "perplexity.sonar-deep-research",
    "~anthropic.claude-fable-latest",
    "~anthropic.claude-opus-latest",
    "bytedance-seed.seedream-5-0-lite",
    "bytedance-seed.seedream-5-0-pro",
    "~deepseek.deepseek-pro-latest",
    "~google.gemini-flash-latest",
    "~google.gemini-pro-latest",
    "google.gemini-3.1-flash-image",
    "google.gemini-3-pro-image",
    "microsoft.mai-image-2.5-pro",
    "~moonshotai.kimi-latest",
    "~openai.gpt-astra-latest",
    "openai.gpt-6-astra-pro",
    "~openai.gpt-sol-latest",
    "openai.gpt-image-2.5-flare",
    "openai.gpt-image-2.5-sunburst",
    "openai.gpt-5.4-image-2",
    "openai.gpt-5.6-sol-pro",
    "qwen.qwen-image-3-pro",
    "qwen.qwen3.8-max-0902",
    "x-ai.grok-imagine-image-2.0",
    "~x-ai.grok-latest",
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
    return any(g.get("principal_id") == "*" and g.get("permission") == "read" for g in (grants or []))


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


def apply_picker(h: dict[str, str]) -> None:
    keep = {full_id(short) for short in KEEP_SHORT}
    listed = requests.get(f"{OPENWEBUI_URL}/api/v1/models", headers=h, timeout=180).json().get("data") or []
    for summary in listed:
        model_id = summary["id"]
        if not model_id.startswith(f"{PIPE}."):
            continue
        info = summary.get("info") or {}
        if not info.get("is_active"):
            continue
        if model_id in keep:
            continue
        model = get_model(h, model_id)
        if is_public(model.get("access_grants") or []):
            set_public(h, model_id, model.get("name") or model_id, False)
            model = get_model(h, model_id)
        set_active(h, model, False)
        print(f"off {model.get('name')}")

    for short in KEEP_SHORT:
        model_id = full_id(short)
        model = get_model(h, model_id)
        set_active(h, model, True)
        model = get_model(h, model_id)
        if not is_public(model.get("access_grants") or []):
            set_public(h, model_id, model.get("name") or short, True)
        print(f"keep {model.get('name')}")


def apply_pins(h: dict[str, str]) -> None:
    models_cfg = requests.get(f"{OPENWEBUI_URL}/api/v1/configs/models", headers=h, timeout=30)
    if models_cfg.status_code != 200:
        raise RuntimeError(f"get models config: {models_cfg.status_code} {models_cfg.text[:240]}")
    cfg = models_cfg.json()
    pinned = ",".join(PINNED_MODELS)
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
    print(f"DEFAULT_PINNED_MODELS={resp.json().get('DEFAULT_PINNED_MODELS')}")
    print(f"DEFAULT_MODELS={resp.json().get('DEFAULT_MODELS')}")


def verify(h: dict[str, str]) -> int:
    errors = 0
    keep = {full_id(short) for short in KEEP_SHORT}
    listed = requests.get(f"{OPENWEBUI_URL}/api/models", headers=h, timeout=120).json().get("data") or []
    ids = {m.get("id") for m in listed}
    extra = sorted(ids - keep)
    missing = sorted(keep - ids)
    if extra:
        print(f"ERR extra in picker: {extra}")
        errors += len(extra)
    if missing:
        print(f"ERR missing from picker: {missing}")
        errors += len(missing)
    print(f"picker {len(listed)}")
    for short in ("~openai.gpt-astra-latest", "openai.gpt-6-astra-pro"):
        model = get_model(h, full_id(short))
        if not model.get("is_active") or not is_public(model.get("access_grants") or []):
            print(f"ERR astra not public {short}")
            errors += 1
        else:
            print(f"OK public {model.get('name')}")
    cfg = requests.get(f"{OPENWEBUI_URL}/api/v1/configs/models", headers=h, timeout=30).json()
    pinned = cfg.get("DEFAULT_PINNED_MODELS") or ""
    if pinned != ",".join(PINNED_MODELS):
        print(f"ERR pins {pinned}")
        errors += 1
    else:
        print("OK pins")
    if cfg.get("DEFAULT_MODELS") != DEFAULT_MODELS:
        print(f"ERR default {cfg.get('DEFAULT_MODELS')}")
        errors += 1
    return errors


def main() -> int:
    h = headers(signin())
    apply_picker(h)
    apply_pins(h)
    errors = verify(h)
    if errors:
        print(f"verify errors: {errors}")
        return 1
    print("confirmed series picker ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
