#!/usr/bin/env python3
"""T0: two-turn Search follow-up on the OWUI chat path. Read-only for Pipe.

Creates a short Flash chat, forces one search, then a continue-from-sources
turn. Writes sizes and item types so T1 knows what to compact. Does not patch
Pipe or Filter.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from collections import Counter
from pathlib import Path

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import PIPE, TEXT_WEB_SEARCH_CANARY_MODEL_ID, TEXT_WEB_SEARCH_FILTER
from text_web_search_ops import headers, signin, web_search_requests

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
MODEL = TEXT_WEB_SEARCH_CANARY_MODEL_ID
OUT = Path(os.environ.get("SEARCH_COST_T0_OUT", "/opt/cursor/artifacts/search-cost-t0.json"))


def complete_via_chat(h: dict[str, str], chat_id: str, messages: list, msg_id: str, timeout: int = 240) -> dict:
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/chat/completions",
        headers=h,
        json={
            "model": MODEL,
            "messages": messages,
            "stream": True,
            "chat_id": chat_id,
            "id": msg_id,
            "session_id": str(uuid.uuid4()),
            "filter_ids": [TEXT_WEB_SEARCH_FILTER],
            "features": {"web_search": False},
        },
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"enqueue {resp.status_code} {resp.text[:400]}")
    deadline = time.time() + timeout
    last: dict = {}
    while time.time() < deadline:
        detail = requests.get(f"{OPENWEBUI_URL}/api/v1/chats/{chat_id}", headers=h, timeout=30).json()
        hist = ((detail.get("chat") or {}).get("history") or {}).get("messages") or {}
        last = hist.get(msg_id) or {}
        content = last.get("content") or ""
        blob = content if isinstance(content, str) else json.dumps(content)
        if last.get("done") and (str(blob).strip() or last.get("error")):
            return last
        time.sleep(1.5)
    raise RuntimeError(f"timeout waiting for {msg_id}: {json.dumps(last)[:500]}")


def summarize_message(msg: dict) -> dict:
    content = msg.get("content") or ""
    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
    output = msg.get("output") if isinstance(msg.get("output"), list) else []
    types = Counter()
    type_chars: dict[str, int] = {}
    sample_keys: dict[str, list[str]] = {}
    for item in output:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("type") or item.get("name") or "unknown")
        types[kind] += 1
        raw = json.dumps(item, ensure_ascii=False)
        type_chars[kind] = type_chars.get(kind, 0) + len(raw)
        if kind not in sample_keys:
            sample_keys[kind] = sorted(item.keys())[:20]
    sources = msg.get("sources") or []
    src_chars = 0
    for src in sources:
        if not isinstance(src, dict):
            continue
        docs = src.get("document") or src.get("documents") or []
        if isinstance(docs, str):
            src_chars += len(docs)
        else:
            for doc in docs:
                src_chars += len(doc) if isinstance(doc, str) else len(json.dumps(doc, ensure_ascii=False))
    usage = msg.get("usage") or {}
    return {
        "content_chars": len(text),
        "content_preview": text[:180].replace("\n", " "),
        "output_n": len(output),
        "output_types": dict(types),
        "output_type_chars": type_chars,
        "output_sample_keys": sample_keys,
        "sources_n": len(sources),
        "source_chars": src_chars,
        "status_n": len(msg.get("statusHistory") or []),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "input_tokens": usage.get("input_tokens"),
        "turn_count": usage.get("turn_count"),
        "web_search_requests": web_search_requests(usage),
        "upstream_usd": (usage.get("cost_details") or {}).get("upstream_inference_cost"),
        "usage_keys": sorted(usage.keys()),
        "message_keys": sorted(msg.keys()),
    }


def main() -> int:
    if not OPENWEBUI_URL:
        raise SystemExit("Missing OPENWEBUI_URL")
    h = headers(signin())
    chat = requests.post(
        f"{OPENWEBUI_URL}/api/v1/chats/new",
        headers=h,
        json={
            "chat": {
                "title": "search-cost-t0",
                "models": [MODEL],
                "history": {"messages": {}, "currentId": None},
                "messages": [],
            }
        },
        timeout=30,
    )
    chat.raise_for_status()
    chat_id = chat.json()["id"]
    user1 = (
        "You must call web_search. Do not answer from memory. "
        "What official product news did OpenAI announce this week? "
        "Cite one live source URL. Keep the answer under 80 words."
    )
    user1_id = str(uuid.uuid4())
    asst1_id = str(uuid.uuid4())
    turn1 = complete_via_chat(h, chat_id, [{"role": "user", "content": user1, "id": user1_id}], asst1_id)
    user2 = "Using only the source you just cited, add one Chinese sentence. Do not start a new research loop."
    history = [
        {"role": "user", "content": user1, "id": user1_id},
        {"role": "assistant", "content": turn1.get("content") or "", "id": asst1_id, "model": MODEL},
        {"role": "user", "content": user2},
    ]
    asst2_id = str(uuid.uuid4())
    turn2 = complete_via_chat(h, chat_id, history, asst2_id)
    report = {
        "chat_id": chat_id,
        "model": MODEL,
        "pipe": PIPE,
        "turn1": summarize_message(turn1),
        "turn2": summarize_message(turn2),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"wrote {OUT}")
    t1 = report["turn1"]
    if t1["web_search_requests"] < 1 and t1["sources_n"] < 1:
        print("ERR turn1 produced no search evidence")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
