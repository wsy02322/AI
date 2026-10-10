#!/usr/bin/env python3
"""Keep only the confirmed model series active and public.

Nano Banana public id is 2.1; Nano Banana 2 is off; Pro stays.
Sol Pro public id is GPT-6.1; GPT-5.6 Sol Pro is off.
Pins stay Opus Latest, Sunburst, Sol Latest, Astra Latest.
Other active catalog rows are toggled off and lose public grants.
Does not delete rows, sync models, or touch valves.
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

SEARCH_FILTER = "openrouter_text_web_search"
TEXT_TOOL_IDS = [
    "amap_drive_route",
    "google_drive_route",
    "x_recent_search",
]
SONAR_SHORT = {
    "perplexity.sonar-pro-search",
    "perplexity.sonar-deep-research",
}
IMAGE_SHORT = {
    "bytedance-seed.seedream-5-0-lite",
    "bytedance-seed.seedream-5-0-pro",
    "google.gemini-nano-banana-2.1",
    "google.gemini-3-pro-image",
    "microsoft.mai-image-2.5-pro",
    "openai.gpt-image-2.5-flare",
    "openai.gpt-image-2.5-sunburst",
    "openai.gpt-5.4-image-2",
    "qwen.qwen-image-3-pro",
    "x-ai.grok-imagine-image-2.0",
}

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
    "google.gemini-nano-banana-2.1",
    "google.gemini-3-pro-image",
    "microsoft.mai-image-2.5-pro",
    "~moonshotai.kimi-latest",
    "~openai.gpt-astra-latest",
    "openai.gpt-6-astra-pro",
    "~openai.gpt-sol-latest",
    "openai.gpt-image-2.5-flare",
    "openai.gpt-image-2.5-sunburst",
    "openai.gpt-5.4-image-2",
    "openai.gpt-6.1-sol-pro",
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


def post_json(h: dict[str, str], path: str, payload: dict[str, Any], label: str) -> dict[str, Any]:
    last = ""
    for attempt in range(4):
        resp = requests.post(f"{OPENWEBUI_URL}{path}", headers=h, json=payload, timeout=30)
        if resp.status_code == 200:
            body = resp.json()
            return body if isinstance(body, dict) else {}
        last = f"{resp.status_code} {resp.text[:300]}"
        if resp.status_code == 429:
            time.sleep(4 * (attempt + 1))
            continue
        raise RuntimeError(f"{label}: {last}")
    raise RuntimeError(f"{label}: {last}")


def set_active(h: dict[str, str], model: dict[str, Any], active: bool) -> None:
    if model.get("is_active") == active:
        return
    post_json(
        h,
        "/api/v1/models/model/update",
        {
            "id": model["id"],
            "name": model["name"],
            "meta": model.get("meta") or {},
            "params": model.get("params") or {},
            "is_active": active,
            "access_grants": model.get("access_grants") or [],
        },
        f"update {model['id']}",
    )


def set_public(h: dict[str, str], model_id: str, name: str, public: bool) -> None:
    grants = [PUBLIC_GRANT] if public else []
    post_json(
        h,
        "/api/v1/models/model/access/update",
        {"id": model_id, "name": name, "access_grants": grants},
        f"access {model_id}",
    )


IMAGE_CAPS = {
    "code_interpreter": False,
    "web_search": False,
    "builtin_tools": False,
    "terminal": False,
}
BANANA_DESCRIPTION = "FASTER IMAGE MODEL. Switch here before asking for pictures."
SOL_PRO_DESCRIPTION = (
    "Hard reasoning. Can search the web. For difficult tasks: "
    "Valves → Reasoning depth → high or xhigh."
)


def update_meta(h: dict[str, str], model: dict[str, Any], meta: dict[str, Any]) -> None:
    post_json(
        h,
        "/api/v1/models/model/update",
        {
            "id": model["id"],
            "name": model["name"],
            "meta": meta,
            "params": model.get("params") or {},
            "is_active": model.get("is_active", True),
            "access_grants": model.get("access_grants") or [],
        },
        f"meta {model['id']}",
    )


def tune_swapped_skus(h: dict[str, str]) -> None:
    """Image tool caps on Banana 2.1; keep Sol Pro web search on the new id."""
    banana = get_model(h, full_id("google.gemini-nano-banana-2.1"))
    if not is_public(banana.get("access_grants") or []):
        banana["access_grants"] = [PUBLIC_GRANT]
    meta = dict(banana.get("meta") or {})
    meta["capabilities"] = dict(IMAGE_CAPS)
    meta["description"] = BANANA_DESCRIPTION
    update_meta(h, banana, meta)
    print(f"tune {banana.get('name')}")

    sol = get_model(h, full_id("openai.gpt-6.1-sol-pro"))
    if not is_public(sol.get("access_grants") or []):
        sol["access_grants"] = [PUBLIC_GRANT]
    meta = dict(sol.get("meta") or {})
    filters = list(meta.get("filterIds") or [])
    for fid in ("openrouter_direct_uploads", "openrouter_text_web_search"):
        if fid not in filters:
            filters.append(fid)
    meta["filterIds"] = filters
    meta["description"] = SOL_PRO_DESCRIPTION
    update_meta(h, sol, meta)
    print(f"tune {sol.get('name')} filters={filters}")


def text_shorts() -> list[str]:
    return [short for short in KEEP_SHORT if short not in SONAR_SHORT and short not in IMAGE_SHORT]


def align_model_attachments(h: dict[str, str], short: str, *, search: bool) -> None:
    """Public text gets search default-on plus route/X tools. Sonar and images lose those."""
    model = get_model(h, full_id(short))
    if search and not is_public(model.get("access_grants") or []):
        model["access_grants"] = [PUBLIC_GRANT]
    meta = dict(model.get("meta") or {})
    filters = [fid for fid in (meta.get("filterIds") or []) if fid]
    defaults = [fid for fid in (meta.get("defaultFilterIds") or []) if fid]
    tools = [tid for tid in (meta.get("toolIds") or []) if tid]
    if search:
        if SEARCH_FILTER not in filters:
            filters.append(SEARCH_FILTER)
        if SEARCH_FILTER not in defaults:
            defaults.append(SEARCH_FILTER)
        for tid in TEXT_TOOL_IDS:
            if tid not in tools:
                tools.append(tid)
    else:
        filters = [fid for fid in filters if fid != SEARCH_FILTER]
        defaults = [fid for fid in defaults if fid != SEARCH_FILTER]
        tools = [tid for tid in tools if tid not in TEXT_TOOL_IDS]
    meta["filterIds"] = filters
    if defaults:
        meta["defaultFilterIds"] = defaults
    else:
        meta.pop("defaultFilterIds", None)
    if tools:
        meta["toolIds"] = tools
    else:
        meta.pop("toolIds", None)
    update_meta(h, model, meta)
    print(f"align {short} search={search} filters={filters} default={defaults} tools={tools}")


def reload_runtime_models(h: dict[str, str]) -> list[dict[str, Any]]:
    """Overlay DB meta into the chat model cache.

    POST /model/update writes the row only. Chat reads app.state.MODELS, so a
    toggleable filter stays invisible until get_all_models runs. GET /api/models
    without refresh does that overlay. refresh=true is intentionally not used:
    it re-fetches the pipe catalog and can turn new SKUs back on.
    """
    keep = {full_id(short) for short in KEEP_SHORT}
    data: list[dict[str, Any]] = []
    for _ in range(3):
        resp = requests.get(f"{OPENWEBUI_URL}/api/models", headers=h, timeout=180)
        if resp.status_code != 200:
            raise RuntimeError(f"runtime models: {resp.status_code} {resp.text[:240]}")
        data = resp.json().get("data") or []
    extras = [
        summary
        for summary in data
        if str(summary.get("id") or "").startswith(f"{PIPE}.") and summary.get("id") not in keep
    ]
    for summary in extras:
        model_id = summary["id"]
        model = get_model(h, model_id)
        if is_public(model.get("access_grants") or []):
            set_public(h, model_id, model.get("name") or model_id, False)
            model = get_model(h, model_id)
        set_active(h, model, False)
        print(f"off extra {model.get('name')}")
    if extras:
        resp = requests.get(f"{OPENWEBUI_URL}/api/models", headers=h, timeout=180)
        if resp.status_code != 200:
            raise RuntimeError(f"runtime models: {resp.status_code} {resp.text[:240]}")
        data = resp.json().get("data") or []
    print(f"runtime models {len(data)}")
    return data


def align_public_text(
    h: dict[str, str],
    shorts: list[str] | None = None,
    *,
    strip_others: bool = True,
) -> None:
    wanted = set(shorts or text_shorts())
    for short in KEEP_SHORT:
        if short in wanted:
            align_model_attachments(h, short, search=True)
        elif strip_others and short in SONAR_SHORT | IMAGE_SHORT:
            align_model_attachments(h, short, search=False)
    reload_runtime_models(h)


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
    tune_swapped_skus(h)
    align_public_text(h)


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
    retired = {
        "google.gemini-3.1-flash-image": "Nano Banana 2",
        "openai.gpt-5.6-sol-pro": "GPT-5.6 Sol Pro",
    }
    for short, label in retired.items():
        model = get_model(h, full_id(short))
        if model.get("is_active") or is_public(model.get("access_grants") or []):
            print(f"ERR retired still on {label}")
            errors += 1
        else:
            print(f"OK off {label}")
    pro = get_model(h, full_id("google.gemini-3-pro-image"))
    if not pro.get("is_active") or not is_public(pro.get("access_grants") or []):
        print("ERR Nano Banana Pro not public")
        errors += 1
    else:
        print("OK public Nano Banana Pro")
    banana = get_model(h, full_id("google.gemini-nano-banana-2.1"))
    caps = (banana.get("meta") or {}).get("capabilities") or {}
    if any(caps.get(key) for key in IMAGE_CAPS):
        print(f"ERR banana caps {caps}")
        errors += 1
    sol = get_model(h, full_id("openai.gpt-6.1-sol-pro"))
    filters = (sol.get("meta") or {}).get("filterIds") or []
    if "openrouter_text_web_search" not in filters:
        print(f"ERR sol pro filters {filters}")
        errors += 1
    for short in text_shorts():
        model = get_model(h, full_id(short))
        meta = model.get("meta") or {}
        filters = meta.get("filterIds") or []
        defaults = meta.get("defaultFilterIds") or []
        tools = meta.get("toolIds") or []
        if SEARCH_FILTER not in filters or SEARCH_FILTER not in defaults:
            print(f"ERR text search attach {short} filters={filters} default={defaults}")
            errors += 1
        if any(tid not in tools for tid in TEXT_TOOL_IDS):
            print(f"ERR text tools {short} tools={tools}")
            errors += 1
    for short in (*SONAR_SHORT, *IMAGE_SHORT):
        model = get_model(h, full_id(short))
        meta = model.get("meta") or {}
        filters = meta.get("filterIds") or []
        tools = meta.get("toolIds") or []
        if SEARCH_FILTER in filters or any(tid in tools for tid in TEXT_TOOL_IDS):
            print(f"ERR non-text has search/tools {short}")
            errors += 1
    return errors


def main() -> int:
    only = None
    align_text = False
    if len(sys.argv) > 1:
        if sys.argv[1] == "--align-text" and len(sys.argv) == 2:
            align_text = True
        elif sys.argv[1] == "--align-only" and len(sys.argv) >= 3:
            only = sys.argv[2:]
            unknown = [short for short in only if short not in text_shorts()]
            if unknown:
                raise SystemExit(f"not public text: {unknown}")
        else:
            raise SystemExit(
                "usage: apply_confirmed_series_picker.py [--align-text | --align-only <short> ...]"
            )
    h = headers(signin())
    if align_text:
        align_public_text(h)
        return 0
    if only is not None:
        align_public_text(h, only, strip_others=False)
        return 0
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
