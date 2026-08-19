#!/usr/bin/env python3
"""Hide OR Web Tools, OR Image Gen, and OWUI Web Search from chat Integrations (Plan A).

Keeps filter functions installed. Keeps OR Direct Uploads and native image filters.
Must merge Pipe valves (never replace) so API_KEY is preserved.
"""

from __future__ import annotations

import os
import sys
import time

import requests

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
OPENWEBUI_PASSWORD = os.environ.get("OPENWEBUI_PASSWORD")
PIPE_ID = "open_webui_openrouter_integration"
DETACH_FILTERS = {"openrouter_web_tools", "openrouter_image_gen"}
PIPE_VALVE_UPDATES = {
    "AUTO_ATTACH_WEB_TOOLS_FILTER": False,
    "AUTO_DEFAULT_WEB_TOOLS_FILTER": False,
    "AUTO_INSTALL_WEB_TOOLS_FILTER": False,
    "AUTO_ATTACH_IMAGE_GEN_FILTER": False,
    "AUTO_INSTALL_IMAGE_GEN_FILTER": False,
    "ENABLE_DATETIME": False,
    "ENABLE_WEB_SEARCH": False,
}


def _login_candidates() -> list[str]:
    candidates: list[str] = []
    # Username succeeds more reliably than email on this instance.
    for value in (os.environ.get("OPENWEBUI_USERNAME"), os.environ.get("OPENWEBUI_EMAIL")):
        if value and value not in candidates:
            candidates.append(value)
    return candidates


def signin() -> str:
    if not OPENWEBUI_URL or not OPENWEBUI_PASSWORD:
        raise SystemExit("Missing OPENWEBUI_URL / OPENWEBUI_PASSWORD")
    last_error = ""
    for ident in _login_candidates():
        resp = requests.post(
            f"{OPENWEBUI_URL}/api/v1/auths/signin",
            json={"email": ident, "password": OPENWEBUI_PASSWORD},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()["token"]
        last_error = f"{resp.status_code} {resp.text[:160]}"
        if resp.status_code == 429:
            time.sleep(8)
    raise SystemExit(f"signin failed: {last_error}")


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def merge_pipe_valves(h: dict[str, str]) -> dict:
    current = requests.get(
        f"{OPENWEBUI_URL}/api/v1/functions/id/{PIPE_ID}/valves",
        headers=h,
        timeout=30,
    )
    if current.status_code != 200:
        raise RuntimeError(f"get pipe valves: {current.status_code} {current.text[:300]}")
    merged = dict(current.json() or {})
    merged.update(PIPE_VALVE_UPDATES)
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/functions/id/{PIPE_ID}/valves/update",
        headers=h,
        json=merged,
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"pipe valves update: {resp.status_code} {resp.text[:400]}")
    saved = resp.json()
    print("pipe valves:")
    for key in PIPE_VALVE_UPDATES:
        print(f"  {key}={saved.get(key)}")
    print(f"  API_KEY set={bool(saved.get('API_KEY'))}")
    return saved


def set_filter_active(h: dict[str, str], fid: str, active: bool) -> None:
    fn = requests.get(f"{OPENWEBUI_URL}/api/v1/functions/id/{fid}", headers=h, timeout=30).json()
    if bool(fn.get("is_active")) == active:
        print(f"{fid} already is_active={active}")
        return
    resp = requests.post(f"{OPENWEBUI_URL}/api/v1/functions/id/{fid}/toggle", headers=h, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"toggle {fid}: {resp.status_code} {resp.text[:300]}")
    after = requests.get(f"{OPENWEBUI_URL}/api/v1/functions/id/{fid}", headers=h, timeout=30).json()
    print(f"{fid} is_active {fn.get('is_active')} -> {after.get('is_active')}")
    if bool(after.get("is_active")) != active:
        raise RuntimeError(f"failed to set {fid} is_active={active}")


def disable_native_web_search(h: dict[str, str]) -> None:
    cfg = requests.get(f"{OPENWEBUI_URL}/api/v1/retrieval/config", headers=h, timeout=30)
    if cfg.status_code != 200:
        raise RuntimeError(f"get retrieval config: {cfg.status_code}")
    payload = dict(cfg.json())
    payload.pop("status", None)
    web = dict(payload.get("web") or {})
    web["ENABLE_WEB_SEARCH"] = False
    payload["web"] = web
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/retrieval/config/update",
        headers=h,
        json=payload,
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"retrieval update: {resp.status_code} {resp.text[:300]}")
    saved_web = (resp.json() or {}).get("web") or {}
    print(f"native ENABLE_WEB_SEARCH={saved_web.get('ENABLE_WEB_SEARCH')}")


def list_pipe_models(h: dict[str, str]) -> list[dict]:
    resp = requests.get(f"{OPENWEBUI_URL}/api/v1/models", headers=h, timeout=60)
    data = resp.json()
    models = data.get("data", data) if isinstance(data, dict) else data
    return [m for m in models if str(m.get("id") or "").startswith(f"{PIPE_ID}.")]


def model_needs_update(meta: dict) -> bool:
    filters = meta.get("filterIds") or []
    caps = meta.get("capabilities") or {}
    if any(fid in DETACH_FILTERS for fid in filters):
        return True
    if caps.get("web_search") is True:
        return True
    return False


def prune_model(h: dict[str, str], model_id: str) -> str:
    detail = requests.get(
        f"{OPENWEBUI_URL}/api/v1/models/model",
        headers=h,
        params={"id": model_id},
        timeout=30,
    )
    if detail.status_code != 200:
        return f"skip get {detail.status_code}"
    model = detail.json()
    meta = dict(model.get("meta") or {})
    if not model_needs_update(meta):
        return "unchanged"
    filters = [fid for fid in (meta.get("filterIds") or []) if fid not in DETACH_FILTERS]
    meta["filterIds"] = filters
    caps = dict(meta.get("capabilities") or {})
    caps["web_search"] = False
    meta["capabilities"] = caps
    pipe_meta = dict(meta.get("openrouter_pipe") or {})
    pipe_meta.pop("web_tools_filter_id", None)
    pipe_meta.pop("image_gen_filter_id", None)
    if pipe_meta:
        meta["openrouter_pipe"] = pipe_meta
    payload = {
        "id": model["id"],
        "name": model["name"],
        "meta": meta,
        "params": model.get("params") or {},
        "is_active": model.get("is_active", True),
        "access_grants": model.get("access_grants") or [],
    }
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/models/model/update",
        headers=h,
        json=payload,
        timeout=30,
    )
    if resp.status_code != 200:
        return f"fail {resp.status_code}"
    return "updated"


def prune_all_models(h: dict[str, str]) -> None:
    models = list_pipe_models(h)
    print(f"pipe models: {len(models)}")
    counts = {"updated": 0, "unchanged": 0, "fail": 0, "skip": 0}
    failures: list[str] = []
    for index, model in enumerate(models, start=1):
        result = prune_model(h, model["id"])
        if result.startswith("fail") or result.startswith("skip"):
            counts["fail" if result.startswith("fail") else "skip"] += 1
            failures.append(f"{model['id']}: {result}")
        else:
            counts[result] += 1
        if index % 50 == 0:
            print(f"  processed {index}/{len(models)} {counts}")
    print("prune counts", counts)
    if failures:
        print("failures", len(failures))
        for line in failures[:20]:
            print(" ", line)


def verify(h: dict[str, str]) -> int:
    errors = 0
    cfg = requests.get(f"{OPENWEBUI_URL}/api/config", headers=h, timeout=30).json()
    enable_web = (cfg.get("features") or {}).get("enable_web_search")
    print(f"api/config enable_web_search={enable_web}")
    if enable_web:
        print("ERROR: native web search still enabled")
        errors += 1
    for fid in sorted(DETACH_FILTERS):
        fn = requests.get(f"{OPENWEBUI_URL}/api/v1/functions/id/{fid}", headers=h, timeout=30).json()
        print(f"{fid} is_active={fn.get('is_active')}")
        if fn.get("is_active"):
            print(f"ERROR: {fid} still active")
            errors += 1
    samples = [
        "open_webui_openrouter_integration.perplexity.sonar-pro-search",
        "open_webui_openrouter_integration.perplexity.sonar-deep-research",
        "open_webui_openrouter_integration.anthropic.claude-opus-5",
        "open_webui_openrouter_integration.google.gemini-3.1-flash-image",
        "open_webui_openrouter_integration.openai.gpt-image-2",
    ]
    listed = {m["id"]: m for m in list_pipe_models(h)}
    for mid in samples:
        model = listed.get(mid)
        if not model:
            print(f"WARN missing {mid}")
            continue
        meta = (model.get("info") or {}).get("meta") or {}
        filters = meta.get("filterIds") or []
        caps = meta.get("capabilities") or {}
        ui_filters = [f.get("id") for f in (model.get("filters") or [])]
        bad = [fid for fid in filters if fid in DETACH_FILTERS]
        print(f"{mid}")
        print(f"  filterIds={filters}")
        print(f"  ui_filters={ui_filters}")
        print(f"  web_search={caps.get('web_search')}")
        if bad:
            print("  ERROR still attached", bad)
            errors += 1
        if caps.get("web_search"):
            print("  ERROR web_search still true")
            errors += 1
        if "openrouter_direct_uploads" not in filters and "image" not in mid and "gpt-image" not in mid:
            # Direct uploads stay on text/sonar; image models may not need it
            print("  note: no direct_uploads")
    return errors


def main() -> int:
    token = signin()
    h = headers(token)
    merge_pipe_valves(h)
    for fid in sorted(DETACH_FILTERS):
        set_filter_active(h, fid, False)
    disable_native_web_search(h)
    prune_all_models(h)
    errors = verify(h)
    if errors:
        print(f"verify errors: {errors}")
        return 1
    print("plan A apply ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
