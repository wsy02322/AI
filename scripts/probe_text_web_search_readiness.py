#!/usr/bin/env python3
"""Read-only readiness probe for the proposed text-model web search plan.

This script signs in and issues GET requests only after authentication. It does
not activate functions, update models, change valves, or send model inference
requests.
"""

from __future__ import annotations

import os
import re
import sys
import time
from typing import Any

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import ACTIVE_MODEL_IDS, GUARDS, IMAGE_MODEL_IDS, PIPE, SONAR_MODEL_IDS

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
OPENWEBUI_PASSWORD = os.environ.get("OPENWEBUI_PASSWORD")
UPSTREAM_WEB_TOOLS_FILTER = "openrouter_web_tools"

# First-wave models whose providers have native search through OpenRouter's
# `engine=auto`. DeepSeek, Kimi, and Qwen remain available without the filter
# until they pass a later Exa-fallback trial.
PROPOSED_TEXT_SEARCH_MODEL_IDS = [
    f"{PIPE}.x-ai.grok-4.6",
    f"{PIPE}.openai.gpt-5.6-sol-pro",
    f"{PIPE}.openai.gpt-5.6-sol",
    f"{PIPE}.anthropic.claude-opus-5",
    f"{PIPE}.anthropic.claude-fable-5.1",
    f"{PIPE}.google.gemini-3.1-pro-preview",
    f"{PIPE}.google.gemini-3.8-flash",
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
    last_error = ""
    for ident in _login_candidates():
        response = requests.post(
            f"{OPENWEBUI_URL}/api/v1/auths/signin",
            json={"email": ident, "password": OPENWEBUI_PASSWORD},
            timeout=30,
        )
        if response.status_code == 200:
            return response.json()["token"]
        last_error = f"{response.status_code} {response.text[:160]}"
        if response.status_code == 429:
            time.sleep(8)
    raise SystemExit(f"signin failed: {last_error}")


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


class Report:
    def __init__(self) -> None:
        self.oks: list[str] = []
        self.warnings: list[str] = []
        self.errors: list[str] = []

    def ok(self, message: str) -> None:
        self.oks.append(message)
        print(f"OK   {message}")

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        print(f"WARN {message}")

    def error(self, message: str) -> None:
        self.errors.append(message)
        print(f"ERR  {message}")


def get_json(h: dict[str, str], path: str, **kwargs: Any) -> Any:
    response = requests.get(f"{OPENWEBUI_URL}{path}", headers=h, timeout=60, **kwargs)
    if response.status_code != 200:
        raise RuntimeError(f"GET {path}: {response.status_code} {response.text[:300]}")
    return response.json()


def effective_priority(content: str, valves: dict[str, Any]) -> int | None:
    value = valves.get("priority")
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    match = re.search(r"priority\s*:\s*int\s*=\s*Field\([^)]*default\s*=\s*(\d+)", content)
    return int(match.group(1)) if match else None


def function_state(h: dict[str, str], function_id: str) -> tuple[dict[str, Any], str, int | None]:
    function = get_json(h, f"/api/v1/functions/id/{function_id}")
    content = function.get("content") or ""
    valves = get_json(h, f"/api/v1/functions/id/{function_id}/valves")
    priority = effective_priority(content, valves if isinstance(valves, dict) else {})
    return function, content, priority


def verify_baseline(h: dict[str, str], report: Report) -> None:
    version = get_json(h, "/api/version").get("version")
    report.ok(f"OWUI version={version}")

    config = get_json(h, "/api/config")
    if (config.get("features") or {}).get("enable_web_search"):
        report.error("OWUI native web search is enabled; proposed plan requires it off")
    else:
        report.ok("OWUI native web search off")

    listed = get_json(h, "/api/models").get("data") or []
    listed_ids = {model.get("id") for model in listed}
    if listed_ids == set(ACTIVE_MODEL_IDS):
        report.ok(f"active picker matches contract ({len(ACTIVE_MODEL_IDS)})")
    else:
        extra = sorted(listed_ids - set(ACTIVE_MODEL_IDS))
        missing = sorted(set(ACTIVE_MODEL_IDS) - listed_ids)
        report.warn(
            f"active catalog drift: got {len(listed_ids)}, want {len(ACTIVE_MODEL_IDS)}; "
            f"extra={extra or []}; missing={missing or []}"
        )


def verify_pipe_and_filters(h: dict[str, str], report: Report) -> None:
    pipe, pipe_content, _ = function_state(h, PIPE)
    pipe_markers = (
        "server_tools",
        "openrouter:web_search",
        "openrouter:web_fetch",
        "stop_server_tools_when",
    )
    missing_pipe_markers = [marker for marker in pipe_markers if marker not in pipe_content]
    if missing_pipe_markers:
        report.error(f"Pipe lacks modern server-tool markers: {missing_pipe_markers}")
    elif not pipe.get("is_active"):
        report.error("OpenRouter Pipe is inactive")
    else:
        report.ok("Pipe supports web_search, web_fetch, citations, and cost stop")

    web_filter, web_content, web_priority = function_state(h, UPSTREAM_WEB_TOOLS_FILTER)
    if web_filter.get("is_active"):
        report.error("broad upstream Web Tools filter is already active")
    else:
        report.ok("broad upstream Web Tools filter remains inactive")
    if web_filter.get("is_global"):
        report.error("broad upstream Web Tools filter is global")
    else:
        report.ok("broad upstream Web Tools filter is not global")

    filter_markers = (
        'server_tools["web_search"]',
        'server_tools["web_fetch"]',
        'features["web_search"] = False',
        "stop_server_tools_when",
    )
    missing_filter_markers = [marker for marker in filter_markers if marker not in web_content]
    if missing_filter_markers:
        report.error(f"installed Web Tools filter lacks markers: {missing_filter_markers}")
    else:
        report.ok("installed filter confirms modern agentic search/fetch contract")
    if 'server_tools["datetime"]' in web_content:
        report.error("installed Web Tools filter still injects datetime")
    else:
        report.ok("installed Web Tools filter has no datetime injection")
    if re.search(r"WEB_FETCH\s*:\s*bool\s*=\s*Field\(\s*default\s*=\s*False", web_content):
        report.warn("upstream Web Fetch defaults off; implementation must make fetch default-on")

    image_guard, image_content, image_priority = function_state(h, "openrouter_image_tool_guard")
    if not image_guard.get("is_active") or not image_guard.get("is_global"):
        report.error("image tool guard must be active and global")
    else:
        report.ok("image tool guard active and global")
    image_markers = ("image_output", "video_generation", 'pipe_meta.pop("server_tools"', 'body.pop("tools"')
    missing_image_markers = [marker for marker in image_markers if marker not in image_content]
    if missing_image_markers:
        report.error(f"image tool guard lacks hard-strip markers: {missing_image_markers}")
    else:
        report.ok("image/video guard strips server tools and request tools")
    if web_priority is None or image_priority is None:
        report.error(f"cannot resolve filter priorities web={web_priority} image={image_priority}")
    elif image_priority <= web_priority:
        report.error(
            f"image guard priority={image_priority} must run after web filter priority={web_priority}"
        )
    else:
        report.ok(f"filter order safe: web={web_priority}, image guard={image_priority}")

    for guard_id in GUARDS:
        guard = get_json(h, f"/api/v1/functions/id/{guard_id}")
        if guard.get("is_active") and guard.get("is_global"):
            report.ok(f"guard active/global {guard_id}")
        else:
            report.error(f"guard not active/global {guard_id}")


def verify_models(h: dict[str, str], report: Report) -> None:
    for model_id in PROPOSED_TEXT_SEARCH_MODEL_IDS:
        model = get_json(h, "/api/v1/models/model", params={"id": model_id})
        filters = (model.get("meta") or {}).get("filterIds") or []
        if UPSTREAM_WEB_TOOLS_FILTER in filters:
            report.error(f"proposed text model already has broad Web Tools: {model_id}")
        else:
            report.ok(f"proposed text model ready: {model_id}")

    for model_id in SONAR_MODEL_IDS + IMAGE_MODEL_IDS:
        model = get_json(h, "/api/v1/models/model", params={"id": model_id})
        filters = (model.get("meta") or {}).get("filterIds") or []
        if UPSTREAM_WEB_TOOLS_FILTER in filters:
            report.error(f"excluded model has broad Web Tools: {model_id}")
    if not any(error.startswith("excluded model") for error in report.errors):
        report.ok("Sonar and image models have no broad Web Tools attachment")


def main() -> int:
    token = signin()
    h = headers(token)
    report = Report()
    verify_baseline(h, report)
    verify_pipe_and_filters(h, report)
    verify_models(h, report)
    print(
        f"\nreadiness: {len(report.oks)} ok, "
        f"{len(report.warnings)} warning, {len(report.errors)} error"
    )
    for warning in report.warnings:
        print(f"  WARN: {warning}")
    for error in report.errors:
        print(f"  ERR: {error}")
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
