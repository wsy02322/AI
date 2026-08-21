"""Shared helpers for ST-OPS L0 apply/verify scripts."""

from __future__ import annotations

import os
import time

import requests

PIPE_ID = "open_webui_openrouter_integration"

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
OPENWEBUI_PASSWORD = os.environ.get("OPENWEBUI_PASSWORD")

PIPE_VALVE_UPDATES = {
    "AUTO_ATTACH_WEB_TOOLS_FILTER": False,
    "AUTO_DEFAULT_WEB_TOOLS_FILTER": False,
    "AUTO_INSTALL_WEB_TOOLS_FILTER": False,
    "AUTO_ATTACH_IMAGE_GEN_FILTER": False,
    "AUTO_INSTALL_IMAGE_GEN_FILTER": False,
    "ENABLE_DATETIME": False,
    "ENABLE_WEB_SEARCH": False,
    "UPDATE_MODEL_CAPABILITIES": False,
}


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
        resp = requests.post(
            f"{OPENWEBUI_URL}/api/v1/auths/signin",
            json={"email": ident, "password": OPENWEBUI_PASSWORD},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()["token"]
        last = f"{resp.status_code} {resp.text[:160]}"
        if resp.status_code in (429, 502, 503):
            time.sleep(5)
    raise SystemExit(f"signin failed: {last}")


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def get_pipe_valves(h: dict[str, str]) -> dict:
    resp = requests.get(
        f"{OPENWEBUI_URL}/api/v1/functions/id/{PIPE_ID}/valves",
        headers=h,
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"get pipe valves: {resp.status_code} {resp.text[:300]}")
    return dict(resp.json() or {})


def merge_pipe_valves(h: dict[str, str], extra: dict | None = None) -> dict:
    merged = get_pipe_valves(h)
    merged.update(PIPE_VALVE_UPDATES)
    if extra:
        merged.update(extra)
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/functions/id/{PIPE_ID}/valves/update",
        headers=h,
        json=merged,
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"pipe valves update: {resp.status_code} {resp.text[:400]}")
    return dict(resp.json() or {})


def openrouter_key_from_export(export: dict) -> str:
    for key in export.get("openai.api_keys") or []:
        if isinstance(key, str) and key.startswith("sk-"):
            return key.strip()
    for cfg in _iter_api_configs(export):
        if cfg.get("enable"):
            continue
        for key in (cfg.get("key"), cfg.get("api_key")):
            if isinstance(key, str) and key.startswith("sk-"):
                return key.strip()
    for slot in ("tts", "stt"):
        audio = (export.get("audio") or {}).get(slot) or {}
        key = audio.get("OPENAI_API_KEY") or ""
        if isinstance(key, str) and key.startswith("sk-"):
            return key.strip()
    raise RuntimeError("no plaintext OpenRouter key in export (openai.api_keys / audio)")


def _iter_api_configs(export: dict):
    raw = export.get("openai.api_configs") or {}
    if isinstance(raw, dict):
        return raw.values()
    if isinstance(raw, list):
        return raw
    return []


def api_key_shape(key: str) -> str:
    if not key:
        return "missing"
    if key.startswith("encrypted:"):
        return "encrypted"
    if key.startswith("sk-"):
        return "plaintext"
    return "other"


def catalog_count(payload: dict) -> int:
    data = payload.get("data") or []
    return len(data) if isinstance(data, list) else 0


def st_valves_need_update(valves: dict) -> bool:
    return any(valves.get(key) is not want for key, want in PIPE_VALVE_UPDATES.items())
