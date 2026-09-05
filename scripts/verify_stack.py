#!/usr/bin/env python3
"""Verify the live Open WebUI stack against docs/SPEC.md (Wave 0)."""

from __future__ import annotations

import hashlib
import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import (
    ACTIVE_MODEL_IDS,
    BANNER_IDS,
    CHAT_KEEP_CODE_INTERPRETER,
    DEFAULT_MODEL_PRIMARY,
    DEFAULT_MODEL_SECONDARY,
    DEFAULT_MODELS,
    DETACH_FILTERS,
    DISABLED_FILTERS,
    EXTRA_ACTIVE_MODEL_IDS,
    GUARDS,
    IMAGE_MODEL_IDS,
    PINNED_MODELS,
    PIPE,
    PIPE_PATCH_MARKERS,
    PIPE_VALVES_FALSE,
    PUBLIC_MODEL_IDS,
    RETIRED_MODEL_IDS,
    SONAR_MODEL_IDS,
    SUGGESTIONS_COUNT,
    TASK_FOLLOW_UP_ENABLE,
    TASK_MODEL,
    TEXT_WEB_SEARCH_FILTER,
    TEXT_WEB_SEARCH_FILTER_MARKER,
    TEXT_WEB_SEARCH_MODEL_IDS,
)

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
OPENWEBUI_PASSWORD = os.environ.get("OPENWEBUI_PASSWORD")
SMOKE = os.environ.get("VERIFY_SMOKE", "1") != "0"


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


def is_public(grants: list) -> bool:
    return any(
        g.get("principal_id") == "*" and g.get("permission") == "read" for g in (grants or [])
    )


def verify(h: dict[str, str]) -> int:
    r = Report()

    version = requests.get(f"{OPENWEBUI_URL}/api/version", headers=h, timeout=15).json()
    r.ok(f"OWUI version={version.get('version')}")

    cfg = requests.get(f"{OPENWEBUI_URL}/api/config", headers=h, timeout=30).json()
    if cfg.get("default_models") != DEFAULT_MODELS:
        r.err(f"default_models={cfg.get('default_models')} want {DEFAULT_MODELS}")
    else:
        r.ok(f"default_models {DEFAULT_MODELS}")
    if (cfg.get("features") or {}).get("enable_web_search"):
        r.err("native web search enabled")
    else:
        r.ok("native web search off")
    if (cfg.get("features") or {}).get("enable_image_generation"):
        r.err("global image generation enabled")
    else:
        r.ok("global image generation off")
    if (cfg.get("features") or {}).get("enable_direct_connections"):
        r.err("direct connections enabled")
    else:
        r.ok("direct connections off")

    img_cfg = requests.get(f"{OPENWEBUI_URL}/api/v1/images/config", headers=h, timeout=30)
    if img_cfg.status_code == 200:
        if img_cfg.json().get("ENABLE_IMAGE_GENERATION"):
            r.err("ENABLE_IMAGE_GENERATION still true")
        else:
            r.ok("ENABLE_IMAGE_GENERATION false")

    models_cfg = requests.get(f"{OPENWEBUI_URL}/api/v1/configs/models", headers=h, timeout=30).json()
    pinned = models_cfg.get("DEFAULT_PINNED_MODELS") or ""
    missing_pinned = [mid for mid in PINNED_MODELS if mid not in pinned]
    if missing_pinned:
        for mid in missing_pinned:
            r.err(f"pinned missing {mid}")
    else:
        r.ok("pinned four-grid present")

    tasks = requests.get(f"{OPENWEBUI_URL}/api/v1/tasks/config", headers=h, timeout=30).json()
    if tasks.get("TASK_MODEL") != TASK_MODEL or tasks.get("TASK_MODEL_EXTERNAL") != TASK_MODEL:
        r.err(f"TASK_MODEL={tasks.get('TASK_MODEL')} / {tasks.get('TASK_MODEL_EXTERNAL')} want {TASK_MODEL}")
    else:
        r.ok(f"task models {TASK_MODEL}")
    if tasks.get("ENABLE_FOLLOW_UP_GENERATION") is not TASK_FOLLOW_UP_ENABLE:
        r.err(
            f"ENABLE_FOLLOW_UP_GENERATION={tasks.get('ENABLE_FOLLOW_UP_GENERATION')!r} "
            f"want {TASK_FOLLOW_UP_ENABLE}"
        )
    else:
        r.ok("follow-up generation off")

    export = requests.get(f"{OPENWEBUI_URL}/api/v1/configs/export", headers=h, timeout=60).json()
    banners = export.get("ui.banners") or []
    banner_ids = [b.get("id") for b in banners]
    for bid in BANNER_IDS:
        if bid not in banner_ids:
            r.err(f"banner missing {bid}")
    if all(bid in banner_ids for bid in BANNER_IDS):
        r.ok(f"banners {banner_ids}")
    suggestions = export.get("ui.prompt_suggestions") or []
    if len(suggestions) != SUGGESTIONS_COUNT:
        r.err(f"suggestions={len(suggestions)} want {SUGGESTIONS_COUNT}")
    else:
        r.ok(f"suggestions {len(suggestions)}")
    if export.get("task.follow_up.enable") is not TASK_FOLLOW_UP_ENABLE:
        r.err(
            f"export task.follow_up.enable={export.get('task.follow_up.enable')!r} "
            f"want {TASK_FOLLOW_UP_ENABLE}"
        )
    else:
        r.ok("export follow-up off")

    valves = requests.get(
        f"{OPENWEBUI_URL}/api/v1/functions/id/{PIPE}/valves", headers=h, timeout=30
    ).json()
    for key in PIPE_VALVES_FALSE:
        if valves.get(key) is not False:
            r.err(f"pipe valve {key}={valves.get(key)}")
    if not any(e.startswith("pipe valve") for e in r.errors):
        r.ok("pipe valves ST-4/5/6")
    if not valves.get("API_KEY"):
        r.err("pipe API_KEY missing")
    else:
        r.ok("pipe API_KEY configured")

    pipe = requests.get(f"{OPENWEBUI_URL}/api/v1/functions/id/{PIPE}", headers=h, timeout=60).json()
    content = pipe.get("content") or ""
    digest = hashlib.sha256(content.encode()).hexdigest()[:12]
    print(f"INFO pipe sha256[:12]={digest}")
    for marker in PIPE_PATCH_MARKERS:
        if marker not in content:
            r.err(f"pipe missing patch marker {marker}")
    if all(m in content for m in PIPE_PATCH_MARKERS):
        r.ok("pipe images/context patch markers")

    funcs = requests.get(f"{OPENWEBUI_URL}/api/v1/functions/", headers=h, timeout=60).json()
    by_id = {f["id"]: f for f in funcs}
    for gid in GUARDS:
        fn = by_id.get(gid)
        if not fn or not fn.get("is_active"):
            r.err(f"guard inactive {gid}")
        else:
            r.ok(f"guard active {gid}")
    for fid in DISABLED_FILTERS:
        fn = by_id.get(fid)
        if fn and fn.get("is_active"):
            r.err(f"{fid} still active")
        else:
            r.ok(f"{fid} inactive")
    thin = by_id.get(TEXT_WEB_SEARCH_FILTER)
    if not thin or not thin.get("is_active"):
        r.err("thin web search filter inactive")
    elif thin.get("is_global"):
        r.err("thin web search filter is global")
    elif TEXT_WEB_SEARCH_FILTER_MARKER not in (thin.get("content") or ""):
        r.err("thin web search filter missing marker")
    else:
        r.ok("thin web search filter active, not global")

    public_found: set[str] = set()
    listed = requests.get(f"{OPENWEBUI_URL}/api/models", headers=h, timeout=90).json().get("data") or []
    listed_ids = {m["id"] for m in listed}
    if len(listed) != len(ACTIVE_MODEL_IDS):
        r.err(f"active picker len={len(listed)} want {len(ACTIVE_MODEL_IDS)}")
    elif listed_ids != set(ACTIVE_MODEL_IDS):
        extra = sorted(listed_ids - set(ACTIVE_MODEL_IDS))
        missing = sorted(set(ACTIVE_MODEL_IDS) - listed_ids)
        if extra:
            r.err(f"picker extra {extra[:5]}{'...' if len(extra) > 5 else ''}")
        if missing:
            r.err(f"picker missing {missing}")
    else:
        r.ok(f"active picker {len(listed)} models")

    for mid in PUBLIC_MODEL_IDS:
        detail = requests.get(
            f"{OPENWEBUI_URL}/api/v1/models/model",
            headers=h,
            params={"id": mid},
            timeout=30,
        )
        if detail.status_code != 200:
            r.err(f"public get fail {mid} {detail.status_code}")
            continue
        model = detail.json()
        if not is_public(model.get("access_grants") or []):
            r.err(f"not public {mid}")
        else:
            public_found.add(mid)
        if model.get("is_active") is False:
            r.err(f"inactive public {mid}")
        meta = model.get("meta") or {}
        filters = meta.get("filterIds") or []
        defaults = meta.get("defaultFilterIds") or []
        bad = [fid for fid in filters if fid in DETACH_FILTERS]
        if bad:
            r.err(f"{mid} still has {bad}")
        has_thin = TEXT_WEB_SEARCH_FILTER in filters
        has_thin_default = TEXT_WEB_SEARCH_FILTER in defaults
        if mid in TEXT_WEB_SEARCH_MODEL_IDS:
            if not has_thin:
                r.err(f"{mid} missing thin web search attachment")
            if not has_thin_default:
                r.err(f"{mid} missing thin web search default-on")
        elif has_thin or has_thin_default:
            r.err(f"{mid} unexpectedly has thin web search")
        caps = meta.get("capabilities") or {}
        if mid in SONAR_MODEL_IDS or mid in IMAGE_MODEL_IDS:
            if caps.get("code_interpreter"):
                r.err(f"{mid} code_interpreter still true")
            if caps.get("web_search"):
                r.err(f"{mid} web_search still true")
            if caps.get("builtin_tools") is not False:
                r.err(f"{mid} builtin_tools={caps.get('builtin_tools')} want false")
        if mid in IMAGE_MODEL_IDS:
            if caps.get("terminal"):
                r.err(f"{mid} terminal still true")
        if mid in CHAT_KEEP_CODE_INTERPRETER:
            if caps.get("code_interpreter") is False:
                r.err(f"{mid} code_interpreter unexpectedly false")

    if public_found == set(PUBLIC_MODEL_IDS):
        r.ok(f"public {len(public_found)}")
    else:
        missing = set(PUBLIC_MODEL_IDS) - public_found
        if missing:
            r.err(f"public missing {sorted(missing)}")

    extra_public: list[str] = []
    inspect = set(listed_ids) | set(EXTRA_ACTIVE_MODEL_IDS) | set(RETIRED_MODEL_IDS)
    inspect -= set(PUBLIC_MODEL_IDS)
    for mid in sorted(inspect):
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
        extra_model = detail.json()
        extra_meta = extra_model.get("meta") or {}
        extra_filters = extra_meta.get("filterIds") or []
        extra_defaults = extra_meta.get("defaultFilterIds") or []
        if TEXT_WEB_SEARCH_FILTER in extra_filters or TEXT_WEB_SEARCH_FILTER in extra_defaults:
            r.err(f"{mid} unexpectedly has thin web search")
        if is_public(extra_model.get("access_grants") or []):
            extra_public.append(mid)
    if extra_public:
        r.err(f"extra public {extra_public}")
    else:
        r.ok("no extra public grants")

    if SMOKE:
        for mid, label in (
            (DEFAULT_MODEL_PRIMARY, "default-grok"),
            (DEFAULT_MODEL_SECONDARY, "default-opus"),
            (f"{PIPE}.openai.gpt-5.6-sol-pro", "sol-pro"),
            (f"{PIPE}.perplexity.sonar-pro-search", "sonar-search"),
        ):
            payload = {
                "model": mid,
                "messages": [{"role": "user", "content": "Reply with the single word OK."}],
                "stream": False,
            }
            if label == "sonar-search":
                payload["params"] = {"function_calling": "native"}
            resp = requests.post(
                f"{OPENWEBUI_URL}/api/chat/completions",
                headers=h,
                json=payload,
                timeout=180,
            )
            text = (resp.text or "")[:400]
            if resp.status_code != 200:
                r.err(f"smoke {label} {resp.status_code} {text}")
            elif "No endpoints found that support tool use" in text:
                r.err(f"smoke {label} tool-use 404 {text}")
            else:
                r.ok(f"smoke {label} {resp.status_code}")
    else:
        print("INFO smoke skipped (VERIFY_SMOKE=0)")

    print(f"\nverify: {len(r.oks)} ok, {len(r.errors)} err")
    for e in r.errors:
        print(f"  - {e}")
    return 1 if r.errors else 0


def main() -> int:
    if not OPENWEBUI_URL:
        raise SystemExit("OPENWEBUI_URL missing")
    return verify(headers(signin()))


if __name__ == "__main__":
    sys.exit(main())
