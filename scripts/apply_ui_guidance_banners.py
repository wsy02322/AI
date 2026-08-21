#!/usr/bin/env python3
"""Apply prominent English in-app guidance (banners, descriptions, prompt chips)."""

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
        "id": "usage-pick-model-v2",
        "type": "info",
        "title": "Pick the right model — this is the main quality switch",
        "content": (
            '<div style="background:#eff6ff;color:#1e3a8a;border:1px solid #93c5fd;'
            "border-left:6px solid #2563eb;border-radius:12px;padding:10px 14px;"
            'line-height:1.35;display:block;width:100%;box-sizing:border-box;">'
            '<span style="display:inline-flex;background:#2563eb;color:#fff;padding:1px 8px;'
            'border-radius:999px;font-size:10px;font-weight:700;letter-spacing:.04em;">'
            "PICK A MODEL</span> "
            "<b>Chat</b> GPT-5.6 Sol Pro or Claude Opus 5 · "
            "<b>Quick search</b> Sonar Pro Search · "
            "<b>Deep report</b> Sonar Deep Research (2–10 min, keep this tab open) · "
            "<b>Images</b> switch to Nano Banana Pro or GPT Image 2 first<br>"
            "Do not use Sonar for everyday chat. Do not ask a chat model to draw."
            "</div>"
        ),
        "dismissible": False,
        "timestamp": 1787100000,
    },
    {
        "id": "usage-reasoning-depth-v2",
        "type": "warning",
        "title": "Turn up Reasoning depth for hard work",
        "content": (
            '<div style="background:#fff7ed;color:#9a3412;border:1px solid #fdba74;'
            "border-left:6px solid #ea580c;border-radius:12px;padding:10px 14px;"
            'line-height:1.35;display:block;width:100%;box-sizing:border-box;">'
            '<span style="display:inline-flex;background:#ea580c;color:#fff;padding:1px 8px;'
            'border-radius:999px;font-size:10px;font-weight:700;letter-spacing:.04em;">'
            "REASONING DEPTH</span> "
            "Input box → <b>Valves</b> → <b>Reasoning depth</b>: "
            "use <b>high</b> or <b>xhigh</b> for code, long analysis, and multi-step problems. "
            "Use <b>low</b> / <b>medium</b> for short or simple tasks (faster). "
            "This often changes quality more than switching between Sol Pro and Opus."
            "</div>"
        ),
        "dismissible": False,
        "timestamp": 1787100001,
    },
]

DESCRIPTIONS = {
    f"{PIPE}.perplexity.sonar-pro-search": (
        "QUICK SEARCH with citations. For chat, writing, or reasoning use GPT-5.6 Sol Pro or Claude Opus 5."
    ),
    f"{PIPE}.perplexity.sonar-deep-research": (
        "DEEP REPORT — long sourced briefs. Typically 2–10 minutes. Keep this tab open; do not refresh or switch models."
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

SUGGESTIONS = [
    {
        "title": ["Message me on WeChat @dalapi", "Let's improve this together"],
        "content": (
            "Message me on WeChat @dalapi — let's improve this together. "
            "Tell me one thing that confused you or one feature you'd like to see."
        ),
    },
    {
        "title": ["Deep report", "Select Sonar Deep Research first"],
        "content": (
            "After you select Perplexity: Sonar Deep Research, write a sourced industry brief on "
            "the latest foundation-model landscape. Keep this tab open; it can take 2–10 minutes."
        ),
    },
    {
        "title": ["Images", "Select Nano Banana Pro first"],
        "content": (
            "After you select Google: Nano Banana Pro (Gemini 3 Pro Image), generate a clean product "
            "render of a ceramic coffee mug on a white background."
        ),
    },
    {
        "title": ["Hard reasoning", "Set Reasoning depth to xhigh"],
        "content": (
            "On GPT-5.6 Sol Pro or Claude Opus 5, set input-box Valves → Reasoning depth to xhigh, "
            "then explain a multi-step strategy for evaluating two competing research papers."
        ),
    },
]


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
    if "usage-pick-model-v2" not in ids or "usage-reasoning-depth-v2" not in ids:
        print("ERROR missing banners")
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
    for s in suggestions:
        text = " ".join(s.get("title") or []) + " " + str(s.get("content") or "")
        if any("\u4e00" <= ch <= "\u9fff" for ch in text):
            chinese += 1
    if chinese:
        print(f"ERROR Chinese in user-facing copy: {chinese}")
        errors += 1
    print(f"suggestions count {len(suggestions)}")
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
