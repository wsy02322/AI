#!/usr/bin/env python3
"""Forward pipe_meta max_tool_calls onto OpenRouter /responses.

W6: OpenAI native only caps when this field actually reaches the API.
Content-only Function update; never touches valves / API_KEY.
Marker already present → no-op.
"""

from __future__ import annotations

import hashlib
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from search_quality_w0 import PIPE_STOP_ANCHOR, _replace_once

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
PIPE_ID = "open_webui_openrouter_integration"
MARKER = "MAX_TOOL_CALLS_FORWARD_V1"

PIPE_STOP_PATCH = PIPE_STOP_ANCHOR + f"""    # {MARKER}
    _mtc = pipe_meta.get("max_tool_calls")
    if isinstance(_mtc, int) and not isinstance(_mtc, bool) and _mtc > 0:
        responses_body.max_tool_calls = _mtc
"""


def sha12(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def inject(src: str) -> str:
    if MARKER in src:
        return src
    return _replace_once(src, PIPE_STOP_ANCHOR, PIPE_STOP_PATCH, what="pipe max_tool_calls")


def main() -> int:
    token = os.environ.get("OPENWEBUI_TOKEN")
    if not token:
        from text_web_search_ops import headers, signin

        h = headers(signin())
    else:
        h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.get(f"{OPENWEBUI_URL}/api/v1/functions/id/{PIPE_ID}", headers=h, timeout=60)
    if response.status_code != 200:
        raise SystemExit(f"get pipe: {response.status_code} {response.text[:300]}")
    pipe = response.json()
    original = pipe.get("content") or ""
    patched = inject(original)
    if patched == original:
        print(f"pipe {MARKER} already present sha={sha12(original)}")
        return 0
    payload = {
        "id": PIPE_ID,
        "name": pipe.get("name") or PIPE_ID,
        "meta": pipe.get("meta") or {},
        "content": patched,
    }
    update = requests.post(
        f"{OPENWEBUI_URL}/api/v1/functions/id/{PIPE_ID}/update",
        headers=h,
        json=payload,
        timeout=180,
    )
    if update.status_code != 200:
        raise SystemExit(f"update pipe: {update.status_code} {update.text[:400]}")
    print(f"pipe {MARKER} applied {sha12(original)} -> {sha12(patched)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
