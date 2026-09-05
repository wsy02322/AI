#!/usr/bin/env python3
"""Shared Open WebUI helpers for the thin text Web Search Filter."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import requests

from stack_contract import (
    ACTIVE_MODEL_IDS,
    BANNER_IDS,
    DISABLED_FILTERS,
    PIPE,
    PIPE_PATCH_MARKERS,
    PUBLIC_MODEL_IDS,
    TEXT_WEB_SEARCH_FILTER,
    TEXT_WEB_SEARCH_FILTER_MARKER,
    TEXT_WEB_SEARCH_MODEL_IDS,
)

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
OPENWEBUI_PASSWORD = os.environ.get("OPENWEBUI_PASSWORD")
FILTER_SOURCE = Path(__file__).with_name("text_web_search_filter.py")
FILTER_NAME = "Web Search"
FILTER_DESCRIPTION = "OpenRouter web search and fetch for selected text models only."


def login_candidates() -> list[str]:
    candidates: list[str] = []
    for value in (os.environ.get("OPENWEBUI_USERNAME"), os.environ.get("OPENWEBUI_EMAIL")):
        if value and value not in candidates:
            candidates.append(value)
    return candidates


def signin() -> str:
    if not OPENWEBUI_URL or not OPENWEBUI_PASSWORD:
        raise SystemExit("Missing OPENWEBUI_URL / OPENWEBUI_PASSWORD")
    last = ""
    for ident in login_candidates():
        response = requests.post(
            f"{OPENWEBUI_URL}/api/v1/auths/signin",
            json={"email": ident, "password": OPENWEBUI_PASSWORD},
            timeout=30,
        )
        if response.status_code == 200:
            return response.json()["token"]
        last = f"{response.status_code} {response.text[:160]}"
        if response.status_code == 429:
            time.sleep(8)
    raise SystemExit(f"signin failed: {last}")


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def filter_source() -> str:
    content = FILTER_SOURCE.read_text(encoding="utf-8")
    if TEXT_WEB_SEARCH_FILTER_MARKER not in content:
        raise RuntimeError("thin filter source missing marker")
    return content


def get_function(h: dict[str, str], function_id: str) -> tuple[int, dict[str, Any] | None]:
    response = requests.get(
        f"{OPENWEBUI_URL}/api/v1/functions/id/{function_id}",
        headers=h,
        timeout=60,
    )
    if response.status_code in (401, 404):
        return response.status_code, None
    if response.status_code != 200:
        raise RuntimeError(f"get function {function_id}: {response.status_code} {response.text[:300]}")
    return 200, response.json()


def upsert_filter(h: dict[str, str]) -> dict[str, Any]:
    content = filter_source()
    status, existing = get_function(h, TEXT_WEB_SEARCH_FILTER)
    payload = {
        "id": TEXT_WEB_SEARCH_FILTER,
        "name": FILTER_NAME,
        "meta": {
            "description": FILTER_DESCRIPTION,
            "manifest": {},
        },
        "content": content,
    }
    if status == 200 and existing:
        response = requests.post(
            f"{OPENWEBUI_URL}/api/v1/functions/id/{TEXT_WEB_SEARCH_FILTER}/update",
            headers=h,
            json=payload,
            timeout=120,
        )
    else:
        response = requests.post(
            f"{OPENWEBUI_URL}/api/v1/functions/create",
            headers=h,
            json=payload,
            timeout=120,
        )
    if response.status_code != 200:
        raise RuntimeError(f"upsert filter: {response.status_code} {response.text[:400]}")
    return response.json()


def set_active(h: dict[str, str], function_id: str, active: bool) -> None:
    _, current = get_function(h, function_id)
    if not current:
        raise RuntimeError(f"missing function {function_id}")
    if bool(current.get("is_active")) == active:
        return
    response = requests.post(
        f"{OPENWEBUI_URL}/api/v1/functions/id/{function_id}/toggle",
        headers=h,
        timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(f"toggle {function_id}: {response.status_code} {response.text[:300]}")
    _, after = get_function(h, function_id)
    if not after or bool(after.get("is_active")) != active:
        raise RuntimeError(f"failed to set {function_id} is_active={active}")


def set_global(h: dict[str, str], function_id: str, is_global: bool) -> None:
    _, current = get_function(h, function_id)
    if not current:
        raise RuntimeError(f"missing function {function_id}")
    if bool(current.get("is_global")) == is_global:
        return
    response = requests.post(
        f"{OPENWEBUI_URL}/api/v1/functions/id/{function_id}/toggle/global",
        headers=h,
        timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(f"toggle global {function_id}: {response.status_code} {response.text[:300]}")
    _, after = get_function(h, function_id)
    if not after or bool(after.get("is_global")) != is_global:
        raise RuntimeError(f"failed to set {function_id} is_global={is_global}")


def set_valves(h: dict[str, str]) -> None:
    response = requests.post(
        f"{OPENWEBUI_URL}/api/v1/functions/id/{TEXT_WEB_SEARCH_FILTER}/valves/update",
        headers=h,
        json={"priority": 0},
        timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(f"valves update: {response.status_code} {response.text[:300]}")


def get_model(h: dict[str, str], model_id: str) -> dict[str, Any]:
    response = requests.get(
        f"{OPENWEBUI_URL}/api/v1/models/model",
        headers=h,
        params={"id": model_id},
        timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(f"get model {model_id}: {response.status_code} {response.text[:300]}")
    return response.json()


def update_model(h: dict[str, str], model: dict[str, Any], meta: dict[str, Any]) -> None:
    payload = {
        "id": model["id"],
        "name": model["name"],
        "meta": meta,
        "params": model.get("params") or {},
        "is_active": model.get("is_active", True),
        "access_grants": model.get("access_grants") or [],
    }
    response = requests.post(
        f"{OPENWEBUI_URL}/api/v1/models/model/update",
        headers=h,
        json=payload,
        timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(f"update model {model['id']}: {response.status_code} {response.text[:300]}")


def attach_models(h: dict[str, str], model_ids: list[str], *, default_on: bool) -> None:
    wanted = set(model_ids)
    inspect = list(dict.fromkeys([*TEXT_WEB_SEARCH_MODEL_IDS, *model_ids]))
    for model_id in inspect:
        model = get_model(h, model_id)
        meta = dict(model.get("meta") or {})
        filters = [fid for fid in (meta.get("filterIds") or []) if fid]
        defaults = [fid for fid in (meta.get("defaultFilterIds") or []) if fid]
        changed = False
        if model_id in wanted:
            if TEXT_WEB_SEARCH_FILTER not in filters:
                filters.append(TEXT_WEB_SEARCH_FILTER)
                changed = True
            if default_on and TEXT_WEB_SEARCH_FILTER not in defaults:
                defaults.append(TEXT_WEB_SEARCH_FILTER)
                changed = True
            if not default_on and TEXT_WEB_SEARCH_FILTER in defaults:
                defaults = [fid for fid in defaults if fid != TEXT_WEB_SEARCH_FILTER]
                changed = True
        else:
            if TEXT_WEB_SEARCH_FILTER in filters:
                filters = [fid for fid in filters if fid != TEXT_WEB_SEARCH_FILTER]
                changed = True
            if TEXT_WEB_SEARCH_FILTER in defaults:
                defaults = [fid for fid in defaults if fid != TEXT_WEB_SEARCH_FILTER]
                changed = True
        if not changed:
            continue
        meta["filterIds"] = filters
        if defaults:
            meta["defaultFilterIds"] = defaults
        else:
            meta.pop("defaultFilterIds", None)
        update_model(h, model, meta)
        print(f"attach {model_id}: filters={filters} default={defaults}")


def detach_all(h: dict[str, str]) -> None:
    attach_models(h, [], default_on=False)


def collect_stream(h: dict[str, str], payload: dict[str, Any], *, timeout: int = 240) -> dict[str, Any]:
    response = requests.post(
        f"{OPENWEBUI_URL}/api/chat/completions",
        headers=h,
        json=payload,
        timeout=timeout,
        stream=True,
    )
    raw = response.text if response.status_code != 200 else ""
    events: list[dict[str, Any]] = []
    text_parts: list[str] = []
    if response.status_code == 200:
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            events.append(chunk)
            choices = chunk.get("choices") or []
            if choices:
                delta = (choices[0].get("delta") or {}).get("content")
                message = (choices[0].get("message") or {}).get("content")
                if isinstance(delta, str):
                    text_parts.append(delta)
                elif isinstance(message, str):
                    text_parts.append(message)
    blob = json.dumps(events, ensure_ascii=False)
    usage: dict[str, Any] = {}
    for event in events:
        chunk_usage = event.get("usage") if isinstance(event, dict) else None
        if isinstance(chunk_usage, dict) and chunk_usage:
            usage.update(chunk_usage)
    return {
        "status": response.status_code,
        "error": raw[:600],
        "events": events,
        "text": "".join(text_parts),
        "blob": blob,
        "usage": usage or {},
    }


def chat_with_optional_search(
    h: dict[str, str],
    model_id: str,
    messages: list[dict[str, str]],
    *,
    enable_search: bool,
    timeout: int = 240,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model_id,
        "messages": messages,
        "stream": True,
        "features": {"web_search": False},
    }
    if enable_search:
        payload["filter_ids"] = [TEXT_WEB_SEARCH_FILTER]
    return collect_stream(h, payload, timeout=timeout)


def server_tool_details(usage: dict[str, Any] | None) -> dict[str, Any]:
    usage = usage or {}
    details = usage.get("server_tool_use_details") or usage.get("server_tool_use") or {}
    return details if isinstance(details, dict) else {}


def web_search_requests(usage: dict[str, Any] | None) -> int:
    details = server_tool_details(usage)
    try:
        return int(details.get("web_search_requests") or 0)
    except (TypeError, ValueError):
        return 0


def tool_calls_executed(usage: dict[str, Any] | None) -> int:
    details = server_tool_details(usage)
    try:
        return int(details.get("tool_calls_executed") or 0)
    except (TypeError, ValueError):
        return 0


def tool_calls_requested(usage: dict[str, Any] | None) -> int:
    details = server_tool_details(usage)
    try:
        return int(details.get("tool_calls_requested") or 0)
    except (TypeError, ValueError):
        return 0


def event_actions(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for event in events:
        payload = event.get("event") if isinstance(event, dict) else None
        data = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(data, dict) and (data.get("action") or data.get("description")):
            out.append(
                {
                    "action": data.get("action"),
                    "description": data.get("description"),
                    "done": data.get("done"),
                    "urls": data.get("urls"),
                }
            )
    return out


def has_status_action(events: list[dict[str, Any]], action: str) -> bool:
    return any(item.get("action") == action for item in event_actions(events))


def has_status_description(events: list[dict[str, Any]], needle: str) -> bool:
    lowered = needle.lower()
    return any(lowered in str(item.get("description") or "").lower() for item in event_actions(events))


def collect_source_urls(events: list[dict[str, Any]]) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()

    def _add(value: object) -> None:
        if isinstance(value, str) and value.startswith("http") and value not in seen:
            seen.add(value)
            urls.append(value)

    for event in events:
        payload = event.get("event") if isinstance(event, dict) else None
        if not isinstance(payload, dict):
            continue
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        source = data.get("source") if isinstance(data.get("source"), dict) else {}
        _add(source.get("url"))
        metadata = data.get("metadata")
        if isinstance(metadata, list):
            for item in metadata:
                if isinstance(item, dict):
                    _add(item.get("source"))
                    _add(item.get("url"))
        action_urls = data.get("urls")
        if isinstance(action_urls, list):
            for item in action_urls:
                _add(item)
        elif isinstance(action_urls, str):
            _add(action_urls)
    return urls


def has_source_urls(events: list[dict[str, Any]]) -> bool:
    return bool(collect_source_urls(events))


def web_fetch_requests(usage: dict[str, Any] | None) -> int:
    details = server_tool_details(usage)
    for key in ("web_fetch_requests", "web_fetch_request_count"):
        try:
            value = int(details.get(key) or 0)
        except (TypeError, ValueError):
            continue
        if value:
            return value
    return 0


def usage_cost_usd(usage: dict[str, Any] | None) -> float | None:
    usage = usage or {}
    for key in ("cost", "total_cost", "cost_usd"):
        value = usage.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                continue
    details = usage.get("cost_details")
    if isinstance(details, dict):
        for key in ("upstream_inference_cost", "total_cost", "cost"):
            value = details.get(key)
            if isinstance(value, (int, float)):
                return float(value)
    return None


def search_called(result: dict[str, Any]) -> bool:
    usage = result.get("usage") or {}
    events = result.get("events") or []
    return web_search_requests(usage) >= 1 or has_status_action(events, "web_search")


def fetch_called_hard(result: dict[str, Any]) -> bool:
    usage = result.get("usage") or {}
    events = result.get("events") or []
    if web_fetch_requests(usage) >= 1 or has_status_action(events, "web_fetch"):
        return True
    for item in event_actions(events):
        description = str(item.get("description") or "").lower()
        if "fetching web page" in description and item.get("done") is True:
            return True
    return False


def fetch_called_soft(result: dict[str, Any]) -> bool:
    events = result.get("events") or []
    return (not fetch_called_hard(result)) and has_status_description(events, "Fetching web page")


def has_search_evidence(result: dict[str, Any]) -> bool:
    return search_called(result)


def has_fetch_evidence(result: dict[str, Any]) -> bool:
    return fetch_called_hard(result) or fetch_called_soft(result)


def snapshot_search_state(h: dict[str, str]) -> dict[str, Any]:
    status, function = get_function(h, TEXT_WEB_SEARCH_FILTER)
    if status != 200 or not function:
        raise RuntimeError("thin filter missing")
    content = function.get("content") or ""
    valves = requests.get(
        f"{OPENWEBUI_URL}/api/v1/functions/id/{TEXT_WEB_SEARCH_FILTER}/valves",
        headers=h,
        timeout=30,
    )
    if valves.status_code != 200:
        raise RuntimeError(f"filter valves: {valves.status_code}")
    attachments: dict[str, dict[str, bool]] = {}
    for model_id in TEXT_WEB_SEARCH_MODEL_IDS:
        model = get_model(h, model_id)
        meta = model.get("meta") or {}
        filters = meta.get("filterIds") or []
        defaults = meta.get("defaultFilterIds") or []
        attachments[model_id] = {
            "attached": TEXT_WEB_SEARCH_FILTER in filters,
            "default_on": TEXT_WEB_SEARCH_FILTER in defaults,
        }
    disabled: dict[str, dict[str, Any]] = {}
    for function_id in DISABLED_FILTERS:
        status, current = get_function(h, function_id)
        disabled[function_id] = {
            "present": status == 200,
            "is_active": bool(current and current.get("is_active")),
            "is_global": bool(current and current.get("is_global")),
        }
    return {
        "filter_id": TEXT_WEB_SEARCH_FILTER,
        "content_sha12": hashlib.sha256(content.encode("utf-8")).hexdigest()[:12],
        "marker_present": TEXT_WEB_SEARCH_FILTER_MARKER in content,
        "is_active": bool(function.get("is_active")),
        "is_global": bool(function.get("is_global")),
        "priority": (valves.json() or {}).get("priority"),
        "attachments": attachments,
        "disabled_filters": disabled,
    }


def _sha12(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def snapshot_eval_instance(h: dict[str, str]) -> dict[str, Any]:
    """Read-only eval fingerprint. Pipe content + markers only; never valves or API_KEY."""
    base = snapshot_search_state(h)
    version = requests.get(f"{OPENWEBUI_URL}/api/version", headers=h, timeout=15).json()
    pipe_status, pipe = get_function(h, PIPE)
    if pipe_status != 200 or not pipe:
        raise RuntimeError("pipe missing")
    pipe_content = pipe.get("content") or ""
    export = requests.get(f"{OPENWEBUI_URL}/api/v1/configs/export", headers=h, timeout=60).json()
    banners = export.get("ui.banners") or []
    banner_items = []
    for banner in banners:
        body = json.dumps(
            {
                "id": banner.get("id"),
                "content": banner.get("content") or banner.get("text") or "",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        banner_items.append({"id": banner.get("id"), "content_sha12": _sha12(body)})
    listed = requests.get(f"{OPENWEBUI_URL}/api/models", headers=h, timeout=90).json().get("data") or []
    picker_ids = sorted(str(item.get("id") or "") for item in listed if item.get("id"))
    return {
        **base,
        "owui_version": version.get("version"),
        "pipe": {
            "id": PIPE,
            "content_sha12": _sha12(pipe_content),
            "markers": {marker: marker in pipe_content for marker in PIPE_PATCH_MARKERS},
        },
        "banners": {
            "ids": [item.get("id") for item in banners],
            "count": len(banners),
            "expected_ids": list(BANNER_IDS),
            "items": banner_items,
        },
        "public_picker": {
            "picker_count": len(picker_ids),
            "picker_ids_sha12": _sha12("\n".join(picker_ids)),
            "public_count_expected": len(PUBLIC_MODEL_IDS),
            "picker_matches_active": picker_ids == sorted(ACTIVE_MODEL_IDS),
        },
    }
