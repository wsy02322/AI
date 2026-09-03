#!/usr/bin/env python3
"""Apply prominent English in-app guidance (banners, descriptions).

Empty-chat Suggested chips are cleared: OWUI always auto-sends on click,
so they are a misfire surface, not hints. Banners + descriptions stay.
"""

from __future__ import annotations

import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import DEFAULT_MODELS

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
PIPE = "open_webui_openrouter_integration"

BANNERS = [
    {
        "id": "usage-guide-v3",
        "type": "info",
        "title": "",
        "content": (
            "<b>Web search only on Perplexity Sonar. Images only on an image model.</b> "
            "<b>Reasoning depth</b>: Input box → <b>Valves</b>. "
            "<b>Settings → General → System Prompt</b> may also affect image models and Perplexity sonar."
        ),
        "dismissible": False,
        "timestamp": 1787100005,
    },
]

DESCRIPTIONS = {
    f"{PIPE}.x-ai.grok-4.6": (
        "DEFAULT CHAT. Use Compare to add a second model. Raise Reasoning depth for hard problems."
    ),
    f"{PIPE}.perplexity.sonar-pro-search": (
        "PERPLEXITY is the only model with live web search. QUICK SEARCH with citations. For chat, writing, or reasoning use GPT-5.6 Sol Pro or Claude Opus 5."
    ),
    f"{PIPE}.perplexity.sonar-deep-research": (
        "PERPLEXITY is the only model with live web search. DEEP REPORT — long sourced briefs. Typically 2–10 minutes. Keep this tab open; do not refresh or switch models."
    ),
    f"{PIPE}.openai.gpt-5.6-sol-pro": (
        "DEFAULT CHAT and hard reasoning. For difficult tasks: Valves → Reasoning depth → high or xhigh. Not live web search."
    ),
    f"{PIPE}.anthropic.claude-opus-5": (
        "Strong reasoning and long writing. Not live web; use Sonar Pro Search for current news. Raise Reasoning depth for hard problems."
    ),
    f"{PIPE}.google.gemini-3-pro-image": (
        "PRIMARY IMAGE MODEL. Switch here before asking for pictures. Multi-turn edits may drift slightly."
    ),
    f"{PIPE}.google.gemini-3.1-flash-image": (
        "FASTER IMAGE MODEL. Switch here before asking for pictures."
    ),
    f"{PIPE}.openai.gpt-image-2": (
        "ALTERNATE IMAGE MODEL. Switch here before asking for pictures."
    ),
}

# OWUI Suggested chips always submit on click. Clear them; banners carry the hints.
SUGGESTIONS: list[dict] = []


def signin() -> str:
    password = os.environ.get("OPENWEBUI_PASSWORD")
    last = ""
    for ident in (os.environ.get("OPENWEBUI_USERNAME"), os.environ.get("OPENWEBUI_EMAIL")):
        if not ident:
            continue
        resp = requests.post(
            f"{OPENWEBUI_URL}/api/v1/auths/signin",
            json={"email": ident, "password": password},
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


def set_banners(h: dict[str, str]) -> None:
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/configs/banners",
        headers=h,
        json={"banners": BANNERS},
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"banners: {resp.status_code} {resp.text[:400]}")
    saved = resp.json()
    print(f"banners saved: {len(saved)}")
    for b in saved:
        print(f"  {b.get('id')} type={b.get('type')} dismissible={b.get('dismissible')} title={b.get('title')}")


def set_default_models(h: dict[str, str]) -> None:
    models_cfg = requests.get(f"{OPENWEBUI_URL}/api/v1/configs/models", headers=h, timeout=30)
    if models_cfg.status_code != 200:
        raise RuntimeError(f"get models config: {models_cfg.status_code} {models_cfg.text[:300]}")
    cfg = models_cfg.json()
    payload = {
        "DEFAULT_MODELS": DEFAULT_MODELS,
        "DEFAULT_PINNED_MODELS": cfg.get("DEFAULT_PINNED_MODELS"),
        "MODEL_ORDER_LIST": cfg.get("MODEL_ORDER_LIST"),
    }
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/configs/models",
        headers=h,
        json=payload,
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"models config: {resp.status_code} {resp.text[:400]}")
    saved = resp.json()
    print(f"DEFAULT_MODELS={saved.get('DEFAULT_MODELS')}")


def set_suggestions(h: dict[str, str]) -> None:
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/configs/suggestions",
        headers=h,
        json={"suggestions": SUGGESTIONS},
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"suggestions: {resp.status_code} {resp.text[:400]}")
    print(f"suggestions saved: {len(resp.json())}")


def set_descriptions(h: dict[str, str]) -> None:
    for model_id, description in DESCRIPTIONS.items():
        detail = requests.get(
            f"{OPENWEBUI_URL}/api/v1/models/model",
            headers=h,
            params={"id": model_id},
            timeout=30,
        )
        if detail.status_code != 200:
            print(f"skip {model_id}: get {detail.status_code}")
            continue
        model = detail.json()
        meta = dict(model.get("meta") or {})
        if meta.get("description") == description:
            print(f"desc {model.get('name')}: unchanged")
            continue
        meta["description"] = description
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
        print(f"desc {model.get('name')}: {resp.status_code}")
        if resp.status_code != 200:
            print(f"  {resp.text[:200]}")


def verify(h: dict[str, str]) -> int:
    errors = 0
    banners = requests.get(f"{OPENWEBUI_URL}/api/v1/configs/banners", headers=h, timeout=30).json()
    suggestions = requests.get(
        f"{OPENWEBUI_URL}/api/v1/configs/export", headers=h, timeout=30
    ).json().get("ui.prompt_suggestions") or []
    ids = [b.get("id") for b in banners]
    print("verify banners", ids)
    if len(banners) != 1 or "usage-guide-v3" not in ids:
        print("ERROR want single usage-guide-v3 banner")
        errors += 1
    if any(bid in ids for bid in ("usage-pick-model-v2", "usage-reasoning-depth-v2")):
        print("ERROR legacy dual banners still present")
        errors += 1
    old = [b for b in banners if "resoning" in str(b.get("content") or "").lower()]
    if old:
        print("ERROR old misspelled banner still present")
        errors += 1
    chinese = 0
    for b in banners:
        text = f"{b.get('title')} {b.get('content')}"
        if any("\u4e00" <= ch <= "\u9fff" for ch in text):
            chinese += 1
    if chinese:
        print(f"ERROR Chinese in user-facing copy: {chinese}")
        errors += 1
    if suggestions:
        print(f"ERROR suggestions still present: {len(suggestions)}")
        errors += 1
    else:
        print("ok suggestions empty")
    guide = next((b for b in banners if b.get("id") == "usage-guide-v3"), {})
    guide_html = str(guide.get("content") or "")
    if "Web search only on Perplexity Sonar" not in guide_html:
        print("ERROR guide banner missing Sonar/image lead")
        errors += 1
    if "Reasoning depth" not in guide_html:
        print("ERROR guide banner missing Reasoning depth")
        errors += 1
    if "Settings → General → System Prompt" not in guide_html:
        print("ERROR guide banner missing General System Prompt note")
        errors += 1
    if "may also affect image models and Perplexity sonar" not in guide_html:
        print("ERROR guide banner missing image/search System Prompt impact")
        errors += 1
    if any(
        p in guide_html
        for p in (
            "Quick search",
            "Deep report",
            "Do not use Sonar for everyday chat",
            "use <b>high</b> or <b>xhigh</b>",
        )
    ):
        print("ERROR guide banner still has long usage copy")
        errors += 1
    if "style=" in guide_html.lower() or "<div" in guide_html.lower() or "<span" in guide_html.lower():
        print("ERROR guide banner has non-minimal HTML (expect bold only)")
        errors += 1
    banned = ("Voice / screen share", "Notebook / YouTube", "GPT-5.6 Sol Pro or Claude Opus")
    hit = [p for p in banned if p in guide_html]
    if hit:
        print("ERROR guide banner still has", hit)
        errors += 1
    elif guide_html and "Web search only on Perplexity Sonar" in guide_html:
        print("ok guide banner merged English")
    listed = {
        m["id"]: m
        for m in requests.get(f"{OPENWEBUI_URL}/api/v1/models", headers=h, timeout=60).json()["data"]
    }
    for model_id, expected in DESCRIPTIONS.items():
        model = listed.get(model_id)
        if not model:
            print("ERROR missing model", model_id)
            errors += 1
            continue
        desc = ((model.get("info") or {}).get("meta") or {}).get("description")
        if desc != expected:
            print("ERROR desc mismatch", model.get("name"), desc)
            errors += 1
        else:
            print("ok desc", model.get("name"))
    grok_desc = (
        (listed.get(f"{PIPE}.x-ai.grok-4.6", {}).get("info") or {}).get("meta") or {}
    ).get("description") or ""
    if "Vision-capable" in grok_desc:
        print("ERROR Grok description still contains Vision-capable guidance")
        errors += 1
    else:
        print("ok Grok description removed Vision-capable guidance")
    for model_id in (
        f"{PIPE}.perplexity.sonar-pro-search",
        f"{PIPE}.perplexity.sonar-deep-research",
    ):
        desc = (
            (listed.get(model_id, {}).get("info") or {}).get("meta") or {}
        ).get("description") or ""
        if "only model with live web search" not in desc:
            print("ERROR Perplexity description missing unique live web search claim", model_id)
            errors += 1
        else:
            print("ok Perplexity unique live web search", model_id)
    return errors


def main() -> int:
    if not OPENWEBUI_URL:
        raise SystemExit("OPENWEBUI_URL missing")
    h = headers(signin())
    set_default_models(h)
    set_banners(h)
    set_suggestions(h)
    set_descriptions(h)
    errors = verify(h)
    if errors:
        print(f"verify errors: {errors}")
        return 1
    models_cfg = requests.get(f"{OPENWEBUI_URL}/api/v1/configs/models", headers=h, timeout=30).json()
    if models_cfg.get("DEFAULT_MODELS") != DEFAULT_MODELS:
        print("ERROR DEFAULT_MODELS", models_cfg.get("DEFAULT_MODELS"))
        errors += 1
    else:
        print("ok DEFAULT_MODELS", models_cfg.get("DEFAULT_MODELS"))
    if errors:
        print(f"verify errors: {errors}")
        return 1
    print("ui guidance apply ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
