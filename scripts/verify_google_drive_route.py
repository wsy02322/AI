#!/usr/bin/env python3
"""Verify ST-16 Google Routes overseas tool install/attachment."""

from __future__ import annotations

import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import (
    AMAP_DRIVE_ROUTE_TOOL,
    GOOGLE_DRIVE_ROUTE_M1A_MARKER,
    GOOGLE_DRIVE_ROUTE_MAP_LITE_MARKER,
    GOOGLE_DRIVE_ROUTE_MARKER,
    GOOGLE_DRIVE_ROUTE_MODEL_IDS,
    GOOGLE_DRIVE_ROUTE_TOOL,
    IMAGE_MODEL_IDS,
    PUBLIC_MODEL_IDS,
    SONAR_MODEL_IDS,
)
from text_web_search_ops import OPENWEBUI_URL, get_model, headers, signin


class Report:
    def __init__(self) -> None:
        self.oks: list[str] = []
        self.errors: list[str] = []

    def ok(self, message: str) -> None:
        self.oks.append(message)
        print(f"OK  {message}")

    def err(self, message: str) -> None:
        self.errors.append(message)
        print(f"ERR {message}")


def main() -> int:
    require_key = "--require-key" in sys.argv
    h = headers(signin())
    report = Report()
    response = requests.get(
        f"{OPENWEBUI_URL}/api/v1/tools/id/{GOOGLE_DRIVE_ROUTE_TOOL}",
        headers=h,
        timeout=60,
    )
    if response.status_code != 200:
        report.err(f"tool missing {response.status_code}")
        print(f"verify google routes: {len(report.oks)} ok, {len(report.errors)} err")
        return 1
    tool = response.json()
    content = tool.get("content") or ""
    if GOOGLE_DRIVE_ROUTE_MARKER not in content:
        report.err("tool missing marker")
    else:
        report.ok("tool marker present")
    if GOOGLE_DRIVE_ROUTE_M1A_MARKER not in content:
        report.err("tool missing M1a marker")
    else:
        report.ok("tool M1a marker")
    if GOOGLE_DRIVE_ROUTE_MAP_LITE_MARKER not in content:
        report.err("tool missing map-lite marker")
    else:
        report.ok("tool map-lite marker")
    if tool.get("name") != "Overseas Drive Route":
        report.err(f"tool name={tool.get('name')}")
    else:
        report.ok("tool name")
    if "mainland China" not in content:
        report.err("tool docstring missing China exclusion")
    else:
        report.ok("tool is overseas-only")
    grants = tool.get("access_grants") or []
    if any(g.get("principal_id") == "*" and g.get("permission") == "read" for g in grants):
        report.ok("tool public read")
    else:
        report.err("tool not public")
    valves_resp = requests.get(
        f"{OPENWEBUI_URL}/api/v1/tools/id/{GOOGLE_DRIVE_ROUTE_TOOL}/valves",
        headers=h,
        timeout=30,
    )
    valves = valves_resp.json() if valves_resp.status_code == 200 else {}
    key_set = bool(str((valves or {}).get("GOOGLE_MAPS_KEY") or "").strip())
    if require_key and not key_set:
        report.err("GOOGLE_MAPS_KEY not set")
    elif key_set:
        report.ok("GOOGLE_MAPS_KEY set")
    else:
        report.ok("GOOGLE_MAPS_KEY unset")

    inspect = list(dict.fromkeys([*PUBLIC_MODEL_IDS, *IMAGE_MODEL_IDS, *SONAR_MODEL_IDS]))
    for model_id in inspect:
        model = get_model(h, model_id)
        tools = (model.get("meta") or {}).get("toolIds") or []
        has = GOOGLE_DRIVE_ROUTE_TOOL in tools
        has_amap = AMAP_DRIVE_ROUTE_TOOL in tools
        if model_id in GOOGLE_DRIVE_ROUTE_MODEL_IDS:
            if has:
                report.ok(f"attached {model_id.rsplit('.', 1)[-1]}")
            else:
                report.err(f"missing attach {model_id}")
            if not has_amap:
                report.err(f"china tool missing on {model_id}")
        elif has:
            report.err(f"unexpected attach {model_id}")
    print(f"verify google routes: {len(report.oks)} ok, {len(report.errors)} err")
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
