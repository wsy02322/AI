#!/usr/bin/env python3
"""N1 verify: RAG embeddings on OpenRouter, notebook collection, YouTube ingest contract."""

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
)

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
OPENWEBUI_PASSWORD = os.environ.get("OPENWEBUI_PASSWORD")


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


def main() -> int:
    h = headers(signin())
    r = Report()
    export = requests.get(f"{OPENWEBUI_URL}/api/v1/configs/export", headers=h, timeout=60).json()
    base = export.get("rag.openai.api_base_url") or ""
    if RAG_OPENAI_BASE_URL.rstrip("/") not in str(base):
        r.err(f"rag.openai.api_base_url={base} want {RAG_OPENAI_BASE_URL}")
    else:
        r.ok("RAG embeddings via OpenRouter")
    if export.get("rag.embedding_engine") != RAG_EMBEDDING_ENGINE:
        r.err(f"embedding_engine={export.get('rag.embedding_engine')}")
    else:
        r.ok(f"embedding_engine={RAG_EMBEDDING_ENGINE}")
    if export.get("rag.embedding_model") != RAG_EMBEDDING_MODEL:
        r.err(f"embedding_model={export.get('rag.embedding_model')} want {RAG_EMBEDDING_MODEL}")
    else:
        r.ok(f"embedding_model={RAG_EMBEDDING_MODEL}")
    if (export.get("web.search.enable") is True) or export.get("rag.web.search.enable") is True:
        r.err("native web search enabled")
    else:
        r.ok("native web search still off")

    cfg = requests.get(f"{OPENWEBUI_URL}/api/v1/retrieval/config", headers=h, timeout=30).json()
    template = cfg.get("RAG_TEMPLATE") or ""
    if "notebook sources" in template.lower() or "do not invent" in template.lower():
        r.ok("RAG template grounded")
    else:
        r.err("RAG template still allows out-of-source answers")
    langs = (cfg.get("web") or {}).get("YOUTUBE_LOADER_LANGUAGE") or []
    if "en" in langs:
        r.ok(f"youtube loader langs={langs}")
    else:
        r.err(f"youtube loader langs={langs}")

    listed = requests.get(f"{OPENWEBUI_URL}/api/v1/knowledge/", headers=h, timeout=30).json()
    items = listed.get("items") if isinstance(listed, dict) else listed
    nb = next((i for i in (items or []) if i.get("name") == NOTEBOOK_KNOWLEDGE_NAME), None)
    if not nb:
        r.err(f"missing knowledge {NOTEBOOK_KNOWLEDGE_NAME}")
    else:
        r.ok(f"knowledge {NOTEBOOK_KNOWLEDGE_NAME} id={nb.get('id')}")
        kid = nb["id"]
        detail = requests.get(f"{OPENWEBUI_URL}/api/v1/knowledge/{kid}", headers=h, timeout=30)
        if detail.status_code == 200:
            files = detail.json().get("files") or []
            blob = json_blob(files)
            if "youtu.be/" in blob or "youtube.com" in blob or "Spoken" in blob or "spoken:" in blob:
                r.ok("knowledge has YouTube source text")
            else:
                r.err("knowledge has no YouTube ingest yet")
            if "shown:" in blob.lower() or "## Shown" in blob:
                r.ok("knowledge has visual timeline")
            else:
                r.err("knowledge missing visual timeline (shown)")
        else:
            r.err(f"knowledge detail {detail.status_code}")

    banners = requests.get(f"{OPENWEBUI_URL}/api/v1/configs/banners", headers=h, timeout=30).json()
    text = " ".join(f"{b.get('title')} {b.get('content')}" for b in banners).lower()
    if "notebook" in text and "youtube" in text:
        r.ok("banner mentions Notebook / YouTube")
    else:
        r.err("banner missing Notebook / YouTube")
    if "screen share" in text:
        r.ok("banner still mentions screen share")
    else:
        r.err("banner lost screen share guidance")

    print(f"{len(r.oks)} ok / {len(r.errors)} err")
    return 1 if r.errors else 0


def json_blob(obj) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False)


if __name__ == "__main__":
    raise SystemExit(main())
