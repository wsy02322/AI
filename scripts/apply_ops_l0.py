#!/usr/bin/env python3
"""Apply ST-OPS L0 on the live instance (merge-only).

- Pipe API_KEY: ensure configured (merge plaintext from export when missing / catalog low)
- Pipe valves ST-4/5/6 false (only POST when a bool actually drifted)
- openai.api_configs: all enable=false
- Catalog refresh + public grants if needed

Note: OWUI re-encrypts API_KEY on valves/update when runtime WEBUI_SECRET_KEY exists.
L0 recovery = merge plaintext input; DB may show encrypted: while catalog works.
Does NOT set WEBUI_SECRET_KEY (VPS env stays empty by policy).
"""

from __future__ import annotations

import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ops_l0_common import (
    OPENWEBUI_URL,
    PIPE_ID,
    PIPE_VALVE_UPDATES,
    _iter_api_configs,
    api_key_shape,
    catalog_count,
    get_pipe_valves,
    headers,
    merge_pipe_valves,
    openrouter_key_from_export,
    signin,
    st_valves_need_update,
)
from stack_contract import PUBLIC_MODEL_IDS

PUBLIC_GRANT = {"principal_type": "user", "principal_id": "*", "permission": "read"}


def ensure_api_configs_disabled(h: dict[str, str], export: dict) -> bool:
    raw = export.get("openai.api_configs") or {}
    if not raw:
        print("WARN openai.api_configs empty in export")
        return False
    configs = dict(raw) if isinstance(raw, dict) else {str(i): c for i, c in enumerate(raw)}
    changed = False
    for cfg in configs.values():
        if cfg.get("enable"):
            cfg["enable"] = False
            changed = True
    if not changed:
        print("openai.api_configs already all enable=false")
        return False
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/configs/import",
        headers=h,
        json={"config": {"openai.api_configs": configs}},
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"configs/import openai.api_configs: {resp.status_code} {resp.text[:400]}")
    print("openai.api_configs set all enable=false")
    return True


def ensure_pipe_key(h: dict[str, str], export: dict, count: int) -> None:
    valves = get_pipe_valves(h)
    current = (valves.get("API_KEY") or "").strip()
    shape = api_key_shape(current)
    print(f"pipe API_KEY shape={shape}")
    if shape != "missing" and count >= 400:
        print("pipe API_KEY ok for L0 (catalog healthy)")
        return
    source = openrouter_key_from_export(export)
    saved = merge_pipe_valves(h, {"API_KEY": source})
    new_shape = api_key_shape((saved.get("API_KEY") or "").strip())
    print(f"pipe API_KEY merged -> shape={new_shape}")
    if not (saved.get("API_KEY") or "").strip():
        raise RuntimeError("failed to set Pipe API_KEY")


def ensure_st_valves(h: dict[str, str]) -> None:
    valves = get_pipe_valves(h)
    if not st_valves_need_update(valves):
        print("pipe ST-4/5/6 valves already correct")
        return
    merge_pipe_valves(h)
    print("pipe ST-4/5/6 valves merged")


def refresh_catalog(h: dict[str, str]) -> int:
    resp = requests.get(
        f"{OPENWEBUI_URL}/api/models",
        headers=h,
        params={"refresh": "true"},
        timeout=180,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"models refresh: {resp.status_code} {resp.text[:300]}")
    count = catalog_count(resp.json())
    print(f"catalog after refresh: {count}")
    return count


def ensure_public_grants(h: dict[str, str]) -> int:
    listed = requests.get(f"{OPENWEBUI_URL}/api/v1/models", headers=h, timeout=120).json().get("data") or []
    by_id = {m["id"]: m for m in listed}
    fixed = 0
    for model_id in PUBLIC_MODEL_IDS:
        model = by_id.get(model_id)
        if not model:
            print(f"WARN missing in catalog {model_id}")
            continue
        grants = model.get("access_grants") or []
        if any(g.get("principal_id") == "*" for g in grants):
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
            print(f"WARN access/update {model_id}: {resp.status_code}")
            continue
        fixed += 1
    print(f"public grants restored for {fixed} models")
    return fixed


def main() -> int:
    h = headers(signin())
    export = requests.get(f"{OPENWEBUI_URL}/api/v1/configs/export", headers=h, timeout=60).json()

    ensure_api_configs_disabled(h, export)
    count = catalog_count(
        requests.get(f"{OPENWEBUI_URL}/api/v1/models", headers=h, timeout=120).json()
    )
    ensure_pipe_key(h, export, count)
    ensure_st_valves(h)

    count = refresh_catalog(h)
    if count < 400:
        export = requests.get(f"{OPENWEBUI_URL}/api/v1/configs/export", headers=h, timeout=60).json()
        ensure_pipe_key(h, export, count)
        count = refresh_catalog(h)
    if count < 400:
        print(f"ERR catalog still low ({count})")
        return 1

    ensure_public_grants(h)
    print("apply_ops_l0: done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
