#!/usr/bin/env python3
"""Apply prominent English in-app guidance (banners, descriptions).

Empty-chat Suggested chips are cleared: OWUI always auto-sends on click,
so they are a misfire surface, not hints. Banners + descriptions stay.

Rules: English only; one global banner (per-model facts in descriptions);
never tell users to open hidden Integrations; compact HTML (newlines
become <br>); changing banner id re-shows the bar. Do not replay v2.
POST /api/v1/configs/banners body is {"banners":[...]}, not a bare list.
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
        "id": "usage-guide-v5",
        "type": "info",
        "title": "",
        "content": (
            "🌐 Grok, Sol, Claude, and Gemini can search the web and read pages. "
            "🔗 GitHub: use a github.com URL, not api.github.com. "
            "🖼️ Images only on an image model. "
            "🧠 Reasoning depth: Input box → Valves. "
            "📝 Settings → General → System Prompt may also affect image models and Perplexity sonar."
        ),
        "dismissible": False,
        "timestamp": 1788610001,
    },
]

DESCRIPTIONS = {
    f"{PIPE}.x-ai.grok-4.6": (
        "DEFAULT CHAT. Can search the web. Use Compare to add a second model. Raise Reasoning depth for hard problems."
    ),
    f"{PIPE}.perplexity.sonar-pro-search": (
        "PERPLEXITY QUICK SEARCH with citations. Dedicated search model. Selected chat models can also search; use this for Perplexity-native results."
    ),
    f"{PIPE}.perplexity.sonar-deep-research": (
        "PERPLEXITY DEEP REPORT — long sourced briefs. Typically 2–10 minutes. Keep this tab open; do not refresh or switch models. Chat-model search is not this report mode."
    ),
    f"{PIPE}.openai.gpt-5.6-sol-pro": (
        "DEFAULT CHAT and hard reasoning. Can search the web. For difficult tasks: Valves → Reasoning depth → high or xhigh."
    ),
    f"{PIPE}.anthropic.claude-opus-5": (
        "Strong reasoning and long writing. Can search the web. Raise Reasoning depth for hard problems."
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
    if len(banners) != 1 or "usage-guide-v5" not in ids:
        print("ERROR want single usage-guide-v5 banner")
        errors += 1
    if any(bid in ids for bid in ("usage-guide-v4", "usage-guide-v3", "usage-pick-model-v2", "usage-reasoning-depth-v2")):
        print("ERROR legacy banners still present")
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
    guide = next((b for b in banners if b.get("id") == "usage-guide-v5"), {})
    guide_html = str(guide.get("content") or "")
    for needle, label in (
        ("🌐", "globe icon"),
        ("Grok, Sol, Claude, and Gemini can search the web and read pages", "search lead"),
        ("🔗", "github icon"),
        ("GitHub: use a github.com URL, not api.github.com", "github hint"),
        ("🖼️", "image icon"),
        ("Images only on an image model", "image-model lead"),
        ("🧠", "reasoning icon"),
        ("Reasoning depth", "Reasoning depth"),
        ("📝", "prompt icon"),
        ("Settings → General → System Prompt", "General System Prompt note"),
        ("may also affect image models and Perplexity sonar", "image/search System Prompt impact"),
    ):
        if needle not in guide_html:
            print(f"ERROR guide banner missing {label}")
            errors += 1
    if "<br" in guide_html.lower():
        print("ERROR guide banner is split across lines")
        errors += 1
    if "<b>" in guide_html.lower() or "</b>" in guide_html.lower():
        print("ERROR guide banner still has bold tags")
        errors += 1
    if any(
        p in guide_html
        for p in (
            "Web search only on Perplexity Sonar",
            "Do not use Sonar for everyday chat",
            "Sonar remains Quick Search / Deep Research",
            "Selected chat models can search the web automatically",
            "use <b>high</b> or <b>xhigh</b>",
            "🔍",
        )
    ):
        print("ERROR guide banner still has old or long usage copy")
        errors += 1
    if "style=" in guide_html.lower() or "<div" in guide_html.lower() or "<span" in guide_html.lower():
        print("ERROR guide banner has non-minimal HTML")
        errors += 1
    banned = ("Voice / screen share", "Notebook / YouTube", "GPT-5.6 Sol Pro or Claude Opus")
    hit = [p for p in banned if p in guide_html]
    if hit:
        print("ERROR guide banner still has", hit)
        errors += 1
    elif guide_html and "Grok, Sol, Claude, and Gemini can search the web and read pages" in guide_html:
        print("ok guide banner search English")
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
        if "only model with live web search" in desc:
            print("ERROR Perplexity description still claims exclusive live web search", model_id)
            errors += 1
        elif model_id.endswith("sonar-pro-search") and "QUICK SEARCH" not in desc:
            print("ERROR Perplexity Quick Search description missing", model_id)
            errors += 1
        elif model_id.endswith("sonar-deep-research") and "DEEP REPORT" not in desc:
            print("ERROR Perplexity Deep Research description missing", model_id)
            errors += 1
        else:
            print("ok Perplexity dedicated search description", model_id)
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
