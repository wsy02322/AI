#!/usr/bin/env python3
"""Retry OpenAI 400 'Server tool request failed' without replayed images.

Root cause (ST-14 / search quality, not a new ST): a long Sol thread replayed a
remote markdown image as input_image, then OpenAI native server tools 400'd.

Top path (confirmed): same OpenRouterAPIError loop as ST-10/11.
  1. Strip input_image / image_url / markdown images; keep search.
  2. If that is a no-op or still 400, drop openrouter: server tools
     (same keep-rule as _fusion_server_tools_stripped) and clear
     stop_server_tools_when. Function tools stay.

Content-only Function update; never touches valves / API_KEY.
Marker already present → no-op.
"""

from __future__ import annotations

import hashlib
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from search_quality_w0 import _replace_once

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
PIPE_ID = "open_webui_openrouter_integration"
MARKER = "SERVER_TOOL_FAIL_RETRY_V1"

FLAG_ANCHOR = """        signature_retry_attempted = False
        self.logger.debug(
            "Orchestrator: __request__ type=%s, is_none=%s",
"""

FLAG_PATCH = """        signature_retry_attempted = False
        server_tool_image_retry_attempted = False
        server_tool_disable_retry_attempted = False
        self.logger.debug(
            "Orchestrator: __request__ type=%s, is_none=%s",
"""

RETRY_ANCHOR = """                if (
                    not reasoning_retry_attempted
                    and self._pipe._ensure_reasoning_config_manager()._should_retry_without_reasoning(exc, responses_body)
                ):
                    reasoning_retry_attempted = True
                    await self._pipe._dispatch_plugin_event(
                        "dispatch_on_request_retry",
                        "reasoning",
                        request_id=SessionLogger.request_id.get() or "",
                    )
                    continue

                await self._pipe._ensure_error_formatter()._report_openrouter_error(
"""

RETRY_PATCH = """                if (
                    not reasoning_retry_attempted
                    and self._pipe._ensure_reasoning_config_manager()._should_retry_without_reasoning(exc, responses_body)
                ):
                    reasoning_retry_attempted = True
                    await self._pipe._dispatch_plugin_event(
                        "dispatch_on_request_retry",
                        "reasoning",
                        request_id=SessionLogger.request_id.get() or "",
                    )
                    continue

                # SERVER_TOOL_FAIL_RETRY_V1: OpenAI native 400 after a replayed
                # remote markdown image was turned into input_image.
                if _stf_is_server_tool_fail(exc):
                    if not server_tool_image_retry_attempted:
                        server_tool_image_retry_attempted = True
                        if _stf_strip_input_images(responses_body):
                            self.logger.info(
                                "%s: retry without replayed images model=%s",
                                "SERVER_TOOL_FAIL_RETRY_V1",
                                getattr(responses_body, "model", None),
                            )
                            await self._pipe._dispatch_plugin_event(
                                "dispatch_on_request_retry",
                                "server_tool_images",
                                request_id=SessionLogger.request_id.get() or "",
                            )
                            continue
                    if not server_tool_disable_retry_attempted:
                        server_tool_disable_retry_attempted = True
                        if _stf_disable_server_tools(responses_body):
                            self.logger.info(
                                "%s: retry without server tools model=%s",
                                "SERVER_TOOL_FAIL_RETRY_V1",
                                getattr(responses_body, "model", None),
                            )
                            await self._pipe._dispatch_plugin_event(
                                "dispatch_on_request_retry",
                                "server_tool_disable",
                                request_id=SessionLogger.request_id.get() or "",
                            )
                            continue

                await self._pipe._ensure_error_formatter()._report_openrouter_error(
"""

HELPER_ANCHOR = """def _fusion_server_tools_stripped(
"""

HELPERS = r'''def _stf_error_text(exc: Any) -> str:
    """SERVER_TOOL_FAIL_RETRY_V1: flatten OpenRouter 400 text for matching."""
    parts = [
        getattr(exc, "upstream_message", None),
        getattr(exc, "openrouter_message", None),
        getattr(exc, "reason", None),
        getattr(exc, "raw_body", None),
        str(exc),
    ]
    return " ".join(part for part in parts if isinstance(part, str)).lower()


def _stf_is_server_tool_fail(exc: Any) -> bool:
    """True for HTTP 400 whose body says server tool request failed."""
    status = getattr(exc, "status", None)
    if status is None:
        status = getattr(exc, "status_code", None)
    if status != 400:
        return False
    return "server tool request failed" in _stf_error_text(exc)


_STF_IMAGE_TYPES = frozenset({"input_image", "image_url", "image"})
_STF_MD_IMG = re.compile(r"!\[[^\]]*\]\([^)]+\)")


def _stf_is_image_part(part: Any) -> bool:
    if not isinstance(part, dict):
        return False
    typ = part.get("type")
    if isinstance(typ, str) and typ in _STF_IMAGE_TYPES:
        return True
    if "image_url" in part:
        return True
    return False


def _stf_strip_markdown_images(text: str) -> str:
    return _STF_MD_IMG.sub("", text)


def _stf_strip_input_images(responses_body: Any) -> bool:
    """Drop replayed images from /responses input. True if mutated."""
    data = getattr(responses_body, "input", None)
    if isinstance(data, str):
        cleaned = _stf_strip_markdown_images(data)
        if cleaned != data:
            responses_body.input = cleaned
            return True
        return False
    if not isinstance(data, list):
        return False
    changed = False
    cleaned_items: list[Any] = []
    for item in data:
        if not isinstance(item, dict):
            cleaned_items.append(item)
            continue
        if _stf_is_image_part(item):
            changed = True
            continue
        content = item.get("content")
        if isinstance(content, str):
            new_content = _stf_strip_markdown_images(content)
            if new_content != content:
                item = dict(item)
                item["content"] = new_content
                changed = True
        elif isinstance(content, list):
            kept: list[Any] = []
            content_changed = False
            for part in content:
                if _stf_is_image_part(part):
                    content_changed = True
                    continue
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    new_text = _stf_strip_markdown_images(part["text"])
                    if new_text != part["text"]:
                        part = dict(part)
                        part["text"] = new_text
                        content_changed = True
                kept.append(part)
            if content_changed:
                item = dict(item)
                item["content"] = kept
                changed = True
        cleaned_items.append(item)
    if changed:
        responses_body.input = cleaned_items
    return changed


def _stf_disable_server_tools(responses_body: Any) -> bool:
    """Drop openrouter: server tools; keep function tools. True if mutated."""
    changed = False
    tools = getattr(responses_body, "tools", None)
    if isinstance(tools, list):
        kept = [
            tool
            for tool in tools
            if not (
                isinstance(tool, dict)
                and isinstance(tool.get("type"), str)
                and tool["type"].startswith("openrouter:")
            )
        ]
        if len(kept) != len(tools):
            responses_body.tools = kept
            changed = True
    if getattr(responses_body, "stop_server_tools_when", None) is not None:
        responses_body.stop_server_tools_when = None
        changed = True
    return changed


'''


def sha12(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def inject(src: str) -> str:
    if MARKER in src:
        return src
    src = _replace_once(src, FLAG_ANCHOR, FLAG_PATCH, what="server-tool-fail flags")
    src = _replace_once(src, RETRY_ANCHOR, RETRY_PATCH, what="server-tool-fail retry")
    return _replace_once(src, HELPER_ANCHOR, HELPERS + HELPER_ANCHOR, what="server-tool-fail helpers")


def _auth_headers() -> dict[str, str]:
    token = os.environ.get("OPENWEBUI_TOKEN")
    if token:
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    from text_web_search_ops import headers, signin

    return headers(signin())


def main() -> int:
    if not OPENWEBUI_URL:
        raise SystemExit("Missing OPENWEBUI_URL")
    h = _auth_headers()
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
