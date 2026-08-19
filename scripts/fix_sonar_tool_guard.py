#!/usr/bin/env python3
"""Patch Open WebUI filters to prevent tool injection on Perplexity Sonar models."""

from __future__ import annotations

import os
import re
import sys
import textwrap
import requests

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
OPENWEBUI_PASSWORD = os.environ.get("OPENWEBUI_PASSWORD")


def _login_candidates() -> list[str]:
    candidates: list[str] = []
    for value in (os.environ.get("OPENWEBUI_USERNAME"), os.environ.get("OPENWEBUI_EMAIL")):
        if value and value not in candidates:
            candidates.append(value)
    return candidates

def _indent_class_block(block: str) -> str:
    return "\n".join(f"    {line}" if line else line for line in block.strip("\n").splitlines())


SEARCH_NATIVE_HELPER_RAW = textwrap.dedent(
    '''
    @staticmethod
    def _is_search_native_model(
        body: dict[str, Any] | None = None,
        __model__: dict[str, Any] | None = None,
    ) -> bool:
        parts: list[str] = []
        if isinstance(body, dict):
            parts.append(str(body.get("model") or ""))
        if isinstance(__model__, dict):
            parts.append(str(__model__.get("id") or ""))
            parts.append(str(__model__.get("name") or ""))
            parts.append(str(__model__.get("base_model_id") or ""))
            info = __model__.get("info") if isinstance(__model__.get("info"), dict) else {}
            parts.append(str(info.get("id") or ""))
            base = info.get("base_model_id")
            if base:
                parts.append(str(base))
        lowered = " ".join(parts).lower()
        markers = (
            "perplexity/",
            "perplexity.",
            "sonar",
            "research-quick",
            "deep-research",
        )
        return any(marker in lowered for marker in markers)
'''
).strip("\n")

SEARCH_NATIVE_HELPER = _indent_class_block(SEARCH_NATIVE_HELPER_RAW)

WEB_TOOLS_EARLY_RETURN = "        if self._is_search_native_model(body, __model__):\n            return body"

IMAGE_GEN_EARLY_RETURN = WEB_TOOLS_EARLY_RETURN


def signin() -> str:
    if not OPENWEBUI_URL or not OPENWEBUI_PASSWORD:
        raise SystemExit("Missing OPENWEBUI_URL / OPENWEBUI_PASSWORD")
    candidates = _login_candidates()
    if not candidates:
        raise SystemExit("Missing OPENWEBUI_EMAIL or OPENWEBUI_USERNAME")
    last_error = ""
    for email in candidates:
        resp = requests.post(
            f"{OPENWEBUI_URL}/api/v1/auths/signin",
            json={"email": email, "password": OPENWEBUI_PASSWORD},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()["token"]
        last_error = f"{email}: {resp.status_code} {resp.text[:200]}"
    raise SystemExit(f"signin failed: {last_error}")


def get_function(headers: dict, fid: str) -> dict:
    resp = requests.get(f"{OPENWEBUI_URL}/api/v1/functions/id/{fid}", headers=headers, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"get {fid}: {resp.status_code} {resp.text[:300]}")
    return resp.json()


def update_function(headers: dict, fid: str, fn: dict, content: str) -> None:
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/functions/id/{fid}/update",
        headers=headers,
        json={
            "id": fid,
            "name": fn["name"],
            "meta": fn.get("meta") or {},
            "content": content,
        },
        timeout=120,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"update {fid}: {resp.status_code} {resp.text[:500]}")


def update_valves(headers: dict, fid: str, valves: dict) -> None:
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/functions/id/{fid}/valves/update",
        headers=headers,
        json=valves,
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"valves {fid}: {resp.status_code} {resp.text[:300]}")


def patch_web_tools(content: str) -> str:
    if "_is_search_native_model" in content and "search_native_model(body, __model__)" in content:
        return content
    if "@staticmethod" not in content:
        raise RuntimeError("web_tools: unexpected structure")
    content = content.replace(
        "    @staticmethod\n    def _csv_list(value: str) -> list[str]:",
        SEARCH_NATIVE_HELPER + "\n\n    @staticmethod\n    def _csv_list(value: str) -> list[str]:",
        1,
    )
    content = content.replace(
        "        if __metadata__ is not None and not isinstance(__metadata__, dict):\n            return body\n",
        "        if __metadata__ is not None and not isinstance(__metadata__, dict):\n            return body\n\n"
        + WEB_TOOLS_EARLY_RETURN
        + "\n",
        1,
    )
    return content


def patch_image_gen(content: str) -> str:
    if "_is_search_native_model" in content and "search_native_model(body, __model__)" in content:
        return content
    # Insert helper before first @staticmethod or before inlet
    if "    @staticmethod" in content:
        content = re.sub(
            r"    @staticmethod",
            SEARCH_NATIVE_HELPER + "\n\n    @staticmethod",
            content,
            count=1,
        )
    else:
        content = content.replace(
            "    def inlet(",
            SEARCH_NATIVE_HELPER + "\n\n    def inlet(",
            1,
        )
    content = content.replace(
        "        if not isinstance(body, dict):\n            return body\n",
        "        if not isinstance(body, dict):\n            return body\n\n" + IMAGE_GEN_EARLY_RETURN + "\n",
        1,
    )
    return content


def patch_search_guard(content: str) -> str:
    content = content.replace(
        "priority: int = Field(default=1, description=\"Run early to strip tools before the pipe.\")",
        "priority: int = Field(default=100, description=\"Run last to strip tools after other filters.\")",
    )
    return content


def main() -> int:
    token = signin()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    patches = {
        "openrouter_web_tools": patch_web_tools,
        "openrouter_image_gen": patch_image_gen,
        "openrouter_search_native_tool_guard": patch_search_guard,
    }

    for fid, patch_fn in patches.items():
        fn = get_function(headers, fid)
        new_content = patch_fn(fn["content"])
        if new_content != fn["content"]:
            update_function(headers, fid, fn, new_content)
            print(f"updated content: {fid}")
        else:
            print(f"content unchanged: {fid}")

    update_valves(headers, "openrouter_search_native_tool_guard", {"priority": 100})
    print("guard priority -> 100")

  # Update sonar model filterIds - try model update
    sonar_id = "open_webui_openrouter_integration.perplexity.sonar-pro-search"
    sonar_deep = "open_webui_openrouter_integration.perplexity.sonar-deep-research"
    for model_id in [sonar_id, sonar_deep]:
        body = {
            "id": model_id,
            "meta": {
                "filterIds": ["openrouter_direct_uploads"],
            },
        }
        for ep in ["/api/v1/models/model/update", "/api/v1/models/update"]:
            resp = requests.post(f"{OPENWEBUI_URL}{ep}", headers=headers, json=body, timeout=30)
            print(f"{ep} {model_id}: {resp.status_code} {resp.text[:200]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
