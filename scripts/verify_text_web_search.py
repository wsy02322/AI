#!/usr/bin/env python3
"""Verify thin text Web Search Filter install/canary/attach/final state."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import (
    DISABLED_FILTERS,
    IMAGE_MODEL_IDS,
    PUBLIC_MODEL_IDS,
    RETIRED_MODEL_IDS,
    SONAR_MODEL_IDS,
    TEXT_WEB_SEARCH_CANARY_MODEL_ID,
    TEXT_WEB_SEARCH_FILTER,
    TEXT_WEB_SEARCH_FILTER_MARKER,
    TEXT_WEB_SEARCH_MODEL_IDS,
)
from text_web_search_ops import OPENWEBUI_URL, get_function, get_model, headers, signin


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


def _filters(model: dict[str, Any]) -> list[str]:
    return list((model.get("meta") or {}).get("filterIds") or [])


def _defaults(model: dict[str, Any]) -> list[str]:
    return list((model.get("meta") or {}).get("defaultFilterIds") or [])


def verify_mode(h: dict[str, str], mode: str) -> int:
    report = Report()
    status, function = get_function(h, TEXT_WEB_SEARCH_FILTER)
    if status != 200 or not function:
        report.err("thin filter missing")
        print(f"verify {mode}: {len(report.oks)} ok, {len(report.errors)} err")
        return 1
    content = function.get("content") or ""
    if TEXT_WEB_SEARCH_FILTER_MARKER not in content:
        report.err("thin filter missing marker")
    else:
        report.ok("thin filter marker present")
    if function.get("is_global"):
        report.err("thin filter is global")
    else:
        report.ok("thin filter is not global")
    want_active = mode != "install"
    if bool(function.get("is_active")) != want_active:
        report.err(f"thin filter is_active={function.get('is_active')} want {want_active}")
    else:
        report.ok(f"thin filter is_active={want_active}")

    valves = requests.get(
        f"{OPENWEBUI_URL}/api/v1/functions/id/{TEXT_WEB_SEARCH_FILTER}/valves",
        headers=h,
        timeout=30,
    ).json()
    if valves.get("priority") not in (0, None):
        report.err(f"thin filter priority={valves.get('priority')} want 0")
    else:
        report.ok("thin filter priority 0")

    for guard_id, want_priority in (
        ("openrouter_image_tool_guard", 1),
        ("openrouter_search_native_tool_guard", 100),
    ):
        guard = requests.get(
            f"{OPENWEBUI_URL}/api/v1/functions/id/{guard_id}",
            headers=h,
            timeout=30,
        ).json()
        guard_valves = requests.get(
            f"{OPENWEBUI_URL}/api/v1/functions/id/{guard_id}/valves",
            headers=h,
            timeout=30,
        ).json()
        priority = guard_valves.get("priority")
        if not guard.get("is_active") or not guard.get("is_global"):
            report.err(f"guard not active/global {guard_id}")
        elif isinstance(priority, int) and priority <= 0:
            report.err(f"{guard_id} priority={priority} must run after thin filter")
        else:
            report.ok(f"{guard_id} after thin filter (priority={priority or want_priority})")

    for fid in DISABLED_FILTERS:
        status, broad = get_function(h, fid)
        if status == 200 and broad and broad.get("is_active"):
            report.err(f"{fid} is active")
        else:
            report.ok(f"{fid} inactive")

    attached_want = {
        "install": set(),
        "canary": {TEXT_WEB_SEARCH_CANARY_MODEL_ID},
        "attach": set(TEXT_WEB_SEARCH_MODEL_IDS),
        "final": set(TEXT_WEB_SEARCH_MODEL_IDS),
    }[mode]
    default_want = set(TEXT_WEB_SEARCH_MODEL_IDS) if mode == "final" else set()

    inspect = list(dict.fromkeys([*PUBLIC_MODEL_IDS, *RETIRED_MODEL_IDS, *TEXT_WEB_SEARCH_MODEL_IDS, *IMAGE_MODEL_IDS, *SONAR_MODEL_IDS]))
    for model_id in inspect:
        try:
            model = get_model(h, model_id)
        except RuntimeError as exc:
            if model_id in RETIRED_MODEL_IDS:
                continue
            report.err(str(exc))
            continue
        filters = _filters(model)
        defaults = _defaults(model)
        has_filter = TEXT_WEB_SEARCH_FILTER in filters
        has_default = TEXT_WEB_SEARCH_FILTER in defaults
        if model_id in attached_want:
            if not has_filter:
                report.err(f"missing attachment {model_id}")
            if (model_id in default_want) != has_default:
                report.err(f"defaultFilter mismatch {model_id} default={has_default}")
        else:
            if has_filter or has_default:
                report.err(f"excluded model has thin filter {model_id}")
        if model_id in IMAGE_MODEL_IDS + SONAR_MODEL_IDS and (has_filter or has_default):
            report.err(f"hard-exclude still attached {model_id}")

    if not any(item.startswith("missing attachment") for item in report.errors):
        report.ok(f"attachments match mode={mode}")
    if not any(item.startswith("excluded model") or item.startswith("hard-exclude") for item in report.errors):
        report.ok("Sonar/image/retired/other models have no thin filter")
    if not any(item.startswith("defaultFilter") for item in report.errors):
        report.ok(f"default-on matches mode={mode}")

    print(f"verify {mode}: {len(report.oks)} ok, {len(report.errors)} err")
    for error in report.errors:
        print(f"  - {error}")
    return 1 if report.errors else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("install", "canary", "attach", "final"))
    args = parser.parse_args()
    return verify_mode(headers(signin()), args.mode)


if __name__ == "__main__":
    sys.exit(main())
