#!/usr/bin/env python3
"""Temporary stream status for Astra vs Sol server_tools (P2). Content-only.

Inserts one status event after _apply_server_tools_metadata. Does not change
tool gates, valves, or API_KEY. Always --revert when the probe is done.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time

import requests

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
PIPE_ID = "open_webui_openrouter_integration"
MARKER = "ASTRA_SEARCH_PIPE_DEBUG_V1"

ANCHOR = "        _apply_server_tools_metadata(responses_body, __metadata__, logger=self.logger)\n"
SNIPPET = ANCHOR + f'''        # {MARKER}
        if __event_emitter__:
            try:
                _pm = (__metadata__ or {{}}).get(_PIPE_METADATA_KEY) or {{}}
                _st = _pm.get("server_tools") if isinstance(_pm, dict) else None
                _tools = getattr(responses_body, "tools", None)
                _types = []
                if isinstance(_tools, list):
                    for _t in _tools:
                        if isinstance(_t, dict):
                            _types.append(str(_t.get("type") or _t.get("name") or "?"))
                _mid = str(getattr(responses_body, "model", "") or "")
                _cap = str(capability_model_id or "")
                _desc = (
                    "{MARKER} "
                    f"model={{_mid}} cap={{_cap}} "
                    f"fn={{ModelFamily.supports('function_calling', _cap or _mid)}} "
                    f"img={{ModelFamily.supports('image_output', _cap or _mid)}} "
                    f"vid={{ModelFamily.supports('video_generation', _cap or _mid)}} "
                    f"st={{list(_st) if isinstance(_st, dict) else _st}} "
                    f"n={{len(_tools) if isinstance(_tools, list) else _tools}} "
                    f"types={{_types[:8]}}"
                )
                await __event_emitter__({{"type": "status", "data": {{"description": _desc, "done": False}}}})
            except Exception:
                pass
'''


def _login_candidates() -> list[str]:
    out: list[str] = []
    for value in (os.environ.get("OPENWEBUI_USERNAME"), os.environ.get("OPENWEBUI_EMAIL")):
        if value and value not in out:
            out.append(value)
    return out


def signin() -> str:
    password = os.environ.get("OPENWEBUI_PASSWORD")
    if not OPENWEBUI_URL or not password:
        raise SystemExit("Missing OPENWEBUI_URL / OPENWEBUI_PASSWORD")
    last = ""
    for ident in _login_candidates():
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


def sha12(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def apply_snippet(content: str) -> str:
    if MARKER in content:
        return content
    count = content.count(ANCHOR)
    if count != 1:
        raise SystemExit(f"anchor count={count} want 1")
    return content.replace(ANCHOR, SNIPPET, 1)


def revert_snippet(content: str) -> str:
    if MARKER not in content:
        return content
    start = content.find(f"        # {MARKER}\n")
    if start < 0:
        raise SystemExit("marker comment missing")
    end = content.find("        stripped_tools = _fusion_server_tools_stripped(", start)
    if end < 0:
        raise SystemExit("revert end anchor missing")
    return content[:start] + content[end:]


def update_pipe(content: str, name: str, meta: dict) -> None:
    headers = {"Authorization": f"Bearer {signin()}", "Content-Type": "application/json"}
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/functions/id/{PIPE_ID}/update",
        headers=headers,
        json={"id": PIPE_ID, "name": name, "meta": meta, "content": content},
        timeout=180,
    )
    if resp.status_code != 200:
        raise SystemExit(f"update pipe: {resp.status_code} {resp.text[:500]}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--revert", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.apply == args.revert:
        raise SystemExit("pass exactly one of --apply / --revert")
    headers = {"Authorization": f"Bearer {signin()}", "Content-Type": "application/json"}
    fn = requests.get(f"{OPENWEBUI_URL}/api/v1/functions/id/{PIPE_ID}", headers=headers, timeout=60)
    if fn.status_code != 200:
        raise SystemExit(f"get pipe: {fn.status_code} {fn.text[:300]}")
    pipe = fn.json()
    original = pipe["content"]
    new = apply_snippet(original) if args.apply else revert_snippet(original)
    print(f"sha256[:12] before={sha12(original)} after={sha12(new)} marker={MARKER in new}")
    if new == original:
        print("no content change")
        return 0
    if args.dry_run:
        print("dry-run: not POSTing")
        return 0
    update_pipe(new, pipe.get("name") or PIPE_ID, pipe.get("meta") or {})
    print("pipe content-only update ok; API_KEY not touched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
