#!/usr/bin/env python3
"""N1 apply: point RAG embeddings at OpenRouter, YouTube loader langs, notebook collection.

Merge-only. Does not enable native web search, does not touch Pipe valves/API_KEY.
"""

from __future__ import annotations

import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import (
    NOTEBOOK_KNOWLEDGE_NAME,
    RAG_EMBEDDING_ENGINE,
    RAG_EMBEDDING_MODEL,
    RAG_OPENAI_BASE_URL,
    YOUTUBE_LOADER_LANGUAGES,
)

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
OPENWEBUI_PASSWORD = os.environ.get("OPENWEBUI_PASSWORD")

GROUNDED_NEEDLE = "If the answer isn't present in the notebook sources"
OLD_OWN_KNOWLEDGE = (
    "If the answer isn't present in the context but you possess the knowledge, "
    "explain this to the user and provide the answer using your own understanding."
)
GROUNDED_REPLACEMENT = (
    "If the answer isn't present in the notebook sources, say so clearly. "
    "Do not invent facts or citations from outside the sources."
)


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


def openrouter_key(h: dict[str, str]) -> str:
    audio = requests.get(f"{OPENWEBUI_URL}/api/v1/audio/config", headers=h, timeout=30).json()
    key = ((audio.get("tts") or {}).get("OPENAI_API_KEY") or "").strip()
    if not key:
        raise SystemExit("TTS OPENAI_API_KEY missing; cannot merge into RAG")
    return key


def update_embedding(h: dict[str, str], api_key: str) -> None:
    current = requests.get(f"{OPENWEBUI_URL}/api/v1/retrieval/embedding", headers=h, timeout=30)
    if current.status_code != 200:
        raise RuntimeError(f"get embedding: {current.status_code} {current.text[:300]}")
    payload = dict(current.json())
    payload.pop("status", None)
    payload["RAG_EMBEDDING_ENGINE"] = RAG_EMBEDDING_ENGINE
    payload["RAG_EMBEDDING_MODEL"] = RAG_EMBEDDING_MODEL
    openai_cfg = dict(payload.get("openai_config") or {})
    openai_cfg["url"] = RAG_OPENAI_BASE_URL
    openai_cfg["key"] = api_key
    payload["openai_config"] = openai_cfg
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/retrieval/embedding/update",
        headers=h,
        json=payload,
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"embedding update: {resp.status_code} {resp.text[:400]}")
    saved = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    url = ((saved.get("openai_config") or {}).get("url")) or "ok"
    print(f"RAG embedding engine={payload['RAG_EMBEDDING_ENGINE']} model={payload['RAG_EMBEDDING_MODEL']} url={url}")


def update_retrieval(h: dict[str, str]) -> None:
    cfg = requests.get(f"{OPENWEBUI_URL}/api/v1/retrieval/config", headers=h, timeout=30)
    if cfg.status_code != 200:
        raise RuntimeError(f"get retrieval: {cfg.status_code}")
    payload = dict(cfg.json())
    payload.pop("status", None)
    template = payload.get("RAG_TEMPLATE") or ""
    if GROUNDED_NEEDLE not in template:
        if OLD_OWN_KNOWLEDGE in template:
            payload["RAG_TEMPLATE"] = template.replace(OLD_OWN_KNOWLEDGE, GROUNDED_REPLACEMENT)
        else:
            payload["RAG_TEMPLATE"] = template.rstrip() + "\n\n" + GROUNDED_REPLACEMENT + "\n"
    web = dict(payload.get("web") or {})
    web["ENABLE_WEB_SEARCH"] = False
    web["YOUTUBE_LOADER_LANGUAGE"] = list(YOUTUBE_LOADER_LANGUAGES)
    payload["web"] = web
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/retrieval/config/update",
        headers=h,
        json=payload,
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"retrieval update: {resp.status_code} {resp.text[:400]}")
    saved = resp.json() or {}
    langs = (saved.get("web") or {}).get("YOUTUBE_LOADER_LANGUAGE")
    search = (saved.get("web") or {}).get("ENABLE_WEB_SEARCH")
    print(f"youtube langs={langs} ENABLE_WEB_SEARCH={search}")


def upsert_knowledge(h: dict[str, str]) -> str:
    listed = requests.get(f"{OPENWEBUI_URL}/api/v1/knowledge/", headers=h, timeout=30)
    if listed.status_code != 200:
        raise RuntimeError(f"list knowledge: {listed.status_code} {listed.text[:200]}")
    body = listed.json()
    items = body.get("items") if isinstance(body, dict) else body
    kid = None
    for item in items or []:
        if item.get("name") == NOTEBOOK_KNOWLEDGE_NAME:
            kid = item.get("id")
            break
    desc = (
        "Grounded YouTube notebook: spoken timestamps + on-screen visuals. "
        "Not web search — use Sonar for the public web."
    )
    if not kid:
        created = requests.post(
            f"{OPENWEBUI_URL}/api/v1/knowledge/create",
            headers=h,
            json={"name": NOTEBOOK_KNOWLEDGE_NAME, "description": desc},
            timeout=30,
        )
        if created.status_code != 200:
            raise RuntimeError(f"knowledge create: {created.status_code} {created.text[:300]}")
        kid = created.json()["id"]
        print(f"created knowledge {kid}")
    else:
        requests.post(
            f"{OPENWEBUI_URL}/api/v1/knowledge/{kid}/update",
            headers=h,
            json={"name": NOTEBOOK_KNOWLEDGE_NAME, "description": desc},
            timeout=30,
        )
        print(f"updated knowledge {kid}")
    grants = requests.post(
        f"{OPENWEBUI_URL}/api/v1/knowledge/{kid}/access/update",
        headers=h,
        json={"access_grants": [{"principal_id": "*", "permission": "read"}]},
        timeout=30,
    )
    if grants.status_code != 200:
        print(f"WARN knowledge access {grants.status_code} {grants.text[:200]}")
    else:
        print("knowledge public read grant set")
    return kid


def main() -> int:
    h = headers(signin())
    key = openrouter_key(h)
    update_embedding(h, key)
    update_retrieval(h)
    kid = upsert_knowledge(h)
    export = requests.get(f"{OPENWEBUI_URL}/api/v1/configs/export", headers=h, timeout=60).json()
    base = export.get("rag.openai.api_base_url")
    model = export.get("rag.embedding_model")
    print(f"export rag.openai.api_base_url={base}")
    print(f"export rag.embedding_model={model}")
    if RAG_OPENAI_BASE_URL not in str(base or ""):
        raise SystemExit(f"RAG base still {base}")
    print(f"N1 apply ok knowledge={kid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
