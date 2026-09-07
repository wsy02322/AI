#!/usr/bin/env python3
"""Install ST-17 X recent-search Tool and attach it to qualified public text.

Does not change Pipe valves. Merges tool valves so an existing X_BEARER_TOKEN is kept.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import (
    IMAGE_MODEL_IDS,
    PUBLIC_MODEL_IDS,
    SONAR_MODEL_IDS,
    X_RECENT_SEARCH_MARKER,
    X_RECENT_SEARCH_MODEL_IDS,
    X_RECENT_SEARCH_TOOL,
)
from text_web_search_ops import (
    OPENWEBUI_URL,
    get_model,
    headers,
    refresh_runtime_models,
    signin,
    update_model,
)

TOOL_SOURCE = Path(__file__).with_name("x_recent_search_tool.py")
TOOL_NAME = "X Recent Posts"
PUBLIC_GRANT = {"principal_type": "user", "principal_id": "*", "permission": "read"}


def tool_source() -> str:
    content = TOOL_SOURCE.read_text(encoding="utf-8")
    if X_RECENT_SEARCH_MARKER not in content:
        raise RuntimeError("x recent search tool source missing marker")
    return content


def get_tool(h: dict[str, str]) -> tuple[int, dict[str, Any] | None]:
    response = requests.get(
        f"{OPENWEBUI_URL}/api/v1/tools/id/{X_RECENT_SEARCH_TOOL}",
        headers=h,
        timeout=60,
    )
    if response.status_code in (401, 404):
        return response.status_code, None
    if response.status_code != 200:
        raise RuntimeError(f"get tool: {response.status_code} {response.text[:300]}")
    return 200, response.json()


def upsert_tool(h: dict[str, str]) -> dict[str, Any]:
    content = tool_source()
    status, existing = get_tool(h)
    payload = {
        "id": X_RECENT_SEARCH_TOOL,
        "name": TOOL_NAME,
        "meta": {"description": "Official X recent search (7 days). Compact posts, no embed UI."},
        "content": content,
        "access_grants": [PUBLIC_GRANT],
    }
    if status == 200 and existing:
        response = requests.post(
            f"{OPENWEBUI_URL}/api/v1/tools/id/{X_RECENT_SEARCH_TOOL}/update",
            headers=h,
            json=payload,
            timeout=120,
        )
    else:
        response = requests.post(
            f"{OPENWEBUI_URL}/api/v1/tools/create",
            headers=h,
            json=payload,
            timeout=120,
        )
    if response.status_code != 200:
        raise RuntimeError(f"upsert tool: {response.status_code} {response.text[:500]}")
    grants = requests.post(
        f"{OPENWEBUI_URL}/api/v1/tools/id/{X_RECENT_SEARCH_TOOL}/access/update",
        headers=h,
        json={"access_grants": [PUBLIC_GRANT]},
        timeout=30,
    )
    if grants.status_code != 200:
        print(f"WARN tool access {grants.status_code} {grants.text[:200]}")
    return response.json()


def merge_valves(h: dict[str, str]) -> dict[str, Any]:
    current: dict[str, Any] = {}
    got = requests.get(
        f"{OPENWEBUI_URL}/api/v1/tools/id/{X_RECENT_SEARCH_TOOL}/valves",
        headers=h,
        timeout=30,
    )
    if got.status_code == 200 and isinstance(got.json(), dict):
        current = got.json()
    env_key = (
        os.environ.get("X_BEARER_TOKEN")
        or os.environ.get("X_API_BEARER")
        or os.environ.get("TWITTER_BEARER_TOKEN")
        or ""
    ).strip()
    existing_key = str(current.get("X_BEARER_TOKEN") or "").strip()
    valves = {
        "X_BEARER_TOKEN": env_key or existing_key,
        "MAX_CALLS_PER_TURN": int(current.get("MAX_CALLS_PER_TURN") or 3),
        "MAX_RESULTS": int(current.get("MAX_RESULTS") or 10),
    }
    if valves["MAX_RESULTS"] < 10:
        valves["MAX_RESULTS"] = 10
    if valves["MAX_RESULTS"] > 20:
        valves["MAX_RESULTS"] = 20
    response = requests.post(
        f"{OPENWEBUI_URL}/api/v1/tools/id/{X_RECENT_SEARCH_TOOL}/valves/update",
        headers=h,
        json=valves,
        timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(f"tool valves: {response.status_code} {response.text[:300]}")
    print(f"tool valves token_set={bool(valves['X_BEARER_TOKEN'])} max_results={valves['MAX_RESULTS']}")
    return valves


def attach_tool(h: dict[str, str], model_ids: list[str], *, attach: bool) -> None:
    wanted = set(model_ids) if attach else set()
    inspect = list(dict.fromkeys([*PUBLIC_MODEL_IDS, *model_ids, *IMAGE_MODEL_IDS, *SONAR_MODEL_IDS]))
    for model_id in inspect:
        model = get_model(h, model_id)
        meta = dict(model.get("meta") or {})
        tools = [tid for tid in (meta.get("toolIds") or []) if tid]
        changed = False
        if model_id in wanted:
            if X_RECENT_SEARCH_TOOL not in tools:
                tools.append(X_RECENT_SEARCH_TOOL)
                changed = True
        elif X_RECENT_SEARCH_TOOL in tools:
            tools = [tid for tid in tools if tid != X_RECENT_SEARCH_TOOL]
            changed = True
        if not changed:
            continue
        if tools:
            meta["toolIds"] = tools
        else:
            meta.pop("toolIds", None)
        update_model(h, model, meta)
        print(f"attach {model_id}: toolIds={tools}")
    refresh_runtime_models(h)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("install", "attach", "detach"))
    args = parser.parse_args()
    h = headers(signin())
    if args.mode == "detach":
        attach_tool(h, [], attach=False)
        print("detach ok")
        return 0
    upsert_tool(h)
    merge_valves(h)
    if args.mode == "attach":
        attach_tool(h, X_RECENT_SEARCH_MODEL_IDS, attach=True)
    print(f"apply mode={args.mode} ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
