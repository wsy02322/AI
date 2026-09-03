#!/usr/bin/env python3
"""Verify ST-OPS L0 policy on the live instance (no secret values printed)."""

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
    get_pipe_valves,
    headers,
    signin,
)
from stack_contract import EXTRA_ACTIVE_MODEL_IDS, PUBLIC_MODEL_IDS, RETIRED_MODEL_IDS


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.oks: list[str] = []

    def ok(self, msg: str) -> None:
        self.oks.append(msg)
        print(f"OK  {msg}")

    def err(self, msg: str) -> None:
        self.errors.append(msg)
        print(f"ERR {msg}")


def main() -> int:
    r = Report()
    h = headers(signin())

    export = requests.get(f"{OPENWEBUI_URL}/api/v1/configs/export", headers=h, timeout=60).json()
    configs = list(_iter_api_configs(export))
    enabled = [i for i, c in enumerate(configs) if c.get("enable")]
    if enabled:
        r.err(f"openai.api_configs enabled slots={enabled}")
    else:
        r.ok(f"openai.api_configs all disabled ({len(configs)} slots)")

    valves = get_pipe_valves(h)
    key = (valves.get("API_KEY") or "").strip()
    shape = api_key_shape(key)
    if shape == "missing":
        r.err("pipe API_KEY missing")
    else:
        r.ok(f"pipe API_KEY configured ({shape})")

    for vk, want in PIPE_VALVE_UPDATES.items():
        if valves.get(vk) is not want:
            r.err(f"pipe valve {vk}={valves.get(vk)} want {want}")
    if not any(e.startswith("pipe valve") for e in r.errors):
        r.ok("pipe valves ST-4/5/6")

    listed = requests.get(f"{OPENWEBUI_URL}/api/v1/models", headers=h, timeout=120).json().get("data") or []
    if len(listed) < 400:
        r.err(f"catalog too small {len(listed)}")
    else:
        r.ok(f"catalog {len(listed)} models")

    public = 0
    for mid in PUBLIC_MODEL_IDS:
        detail = requests.get(
            f"{OPENWEBUI_URL}/api/v1/models/model",
            headers=h,
            params={"id": mid},
            timeout=30,
        )
        if detail.status_code != 200:
            r.err(f"model missing {mid}")
            continue
        grants = detail.json().get("access_grants") or []
        if any(g.get("principal_id") == "*" for g in grants):
            public += 1
        else:
            r.err(f"not public {mid}")
    if public == len(PUBLIC_MODEL_IDS):
        r.ok(f"public {public}")

    leaked = []
    for mid in list(EXTRA_ACTIVE_MODEL_IDS) + list(RETIRED_MODEL_IDS):
        detail = requests.get(
            f"{OPENWEBUI_URL}/api/v1/models/model",
            headers=h,
            params={"id": mid},
            timeout=30,
        )
        if detail.status_code == 404:
            continue
        if detail.status_code != 200:
            r.err(f"extra-public get fail {mid} {detail.status_code}")
            continue
        grants = detail.json().get("access_grants") or []
        if any(g.get("principal_id") == "*" and g.get("permission") == "read" for g in grants):
            leaked.append(mid)
    if leaked:
        r.err(f"extra public {leaked}")
    else:
        r.ok("no extra public grants")

    print(f"\nverify_ops_l0: {len(r.oks)} ok, {len(r.errors)} err")
    for e in r.errors:
        print(f"  - {e}")
    return 1 if r.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
