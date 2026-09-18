#!/usr/bin/env python3
"""ST-14: strip assistant inline data-URI markdown; keep http(s) links.

Root cause: a text model (Opus) wrote an unclosed
  ![路线概览图](data:image/png;base64,...)
into the reply. The UI rendered the truncated markdown instead of an image.

User 2026-09-18: do not emit a replacement image; keep the existing Gaode / web links.

Fix: content-only patch of global Filter `openrouter_image_context_guard`.
- inlet unchanged (still image-model-only history trim)
- stream + outlet run on every model
- strip `data:image` markdown (closed or not); never persist to /api/v1/files
- leave http(s) links and image-model `/api/v1/files/` markdown alone

Does not touch valves / API_KEY / models/sync / Banner.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
import re
import sys
from typing import Any, Callable

import requests

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
GUARD_ID = "openrouter_image_context_guard"
MARKER = "DATA_URI_OUTLET_V2"
MARKER_V1 = "DATA_URI_OUTLET_V1"

PersistFn = Callable[[bytes, str], str | None]

_MD_DATA_URI = re.compile(
    r"!?\[([^\]]*)\]\((data:image/[A-Za-z0-9.+-]+;base64,[A-Za-z0-9+/=\s]+)\)?",
    re.I,
)
_BARE_DATA_URI = re.compile(
    r"data:image/[A-Za-z0-9.+-]+;base64,[A-Za-z0-9+/=\s]+",
    re.I,
)
_DANGLING_MD = re.compile(
    r"!?\[([^\]]*)\]\((?:data:image/[^\)]*)?\)?\s*$",
    re.I,
)
_LOOKS_B64 = re.compile(r"^[A-Za-z0-9+/=\s]{16,}$")
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff"
_GIF_MAGIC = b"GIF8"
_MAX_BYTES = 8 * 1024 * 1024


def parse_data_uri(uri: str) -> tuple[bytes, str] | tuple[None, None]:
    text = (uri or "").strip()
    if not text.lower().startswith("data:image/"):
        return None, None
    header, _, payload = text.partition(",")
    if not payload:
        return None, None
    mime = "image/png"
    matched = re.match(r"data:(image/[A-Za-z0-9.+-]+)", header, re.I)
    if matched:
        mime = matched.group(1).lower()
    compact = re.sub(r"\s+", "", payload)
    pad = (-len(compact)) % 4
    if pad:
        compact += "=" * pad
    try:
        raw = base64.b64decode(compact, validate=False)
    except Exception:
        return None, None
    if not raw or len(raw) > _MAX_BYTES:
        return None, None
    if raw.startswith(_PNG_MAGIC):
        if len(raw) >= 64 and b"IEND" in raw[-32:]:
            return raw, mime
        return None, None
    if raw.startswith(_JPEG_MAGIC):
        if len(raw) >= 64 and b"\xff\xd9" in raw[-16:]:
            return raw, mime
        return None, None
    if raw.startswith(_GIF_MAGIC):
        if len(raw) >= 64 and raw.endswith(b";"):
            return raw, mime
        return None, None
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP" and len(raw) >= 64:
        return raw, mime
    return None, None


def iter_inline_images(text: str) -> list[tuple[bytes, str, str]]:
    if not isinstance(text, str) or "data:image" not in text.lower():
        return []
    found: list[tuple[bytes, str, str]] = []
    seen: set[str] = set()
    md_spans = [m.span() for m in _MD_DATA_URI.finditer(text)]

    def add(uri: str) -> None:
        raw, mime = parse_data_uri(uri)
        if not raw or not mime:
            return
        digest = hashlib.sha256(raw).hexdigest()
        if digest in seen:
            return
        seen.add(digest)
        found.append((raw, mime, digest))

    for match in _MD_DATA_URI.finditer(text):
        add(match.group(2))
    for match in _BARE_DATA_URI.finditer(text):
        start = match.start()
        if any(a <= start < b for a, b in md_spans):
            continue
        add(match.group(0))
    return found


def rewrite_assistant_text(text: str, persist_fn: PersistFn | None = None) -> str:
    """Strip inline data-URI markdown. persist_fn is ignored (ST-14 V2: no replacement image)."""
    del persist_fn
    if not isinstance(text, str):
        return text
    if "data:image" not in text.lower():
        return _DANGLING_MD.sub("", text).rstrip()
    rewritten = _MD_DATA_URI.sub("", text)
    rewritten = _BARE_DATA_URI.sub("", rewritten)
    rewritten = _DANGLING_MD.sub("", rewritten)
    rewritten = re.sub(r"\n{3,}", "\n\n", rewritten).rstrip()
    return rewritten


def rewrite_content(content: Any, persist_fn: PersistFn | None = None) -> Any:
    if isinstance(content, str):
        return rewrite_assistant_text(content, persist_fn=persist_fn)
    if isinstance(content, list):
        out = []
        for block in content:
            if isinstance(block, dict):
                block = dict(block)
                for key in ("text", "content"):
                    if isinstance(block.get(key), str) and "data:image" in str(block.get(key)).lower():
                        block[key] = rewrite_assistant_text(block[key], persist_fn=persist_fn)
                if isinstance(block.get("content"), list):
                    block["content"] = rewrite_content(block["content"], persist_fn=persist_fn)
                out.append(block)
            elif isinstance(block, str):
                out.append(rewrite_assistant_text(block, persist_fn=persist_fn))
            else:
                out.append(block)
        return out
    if isinstance(content, dict):
        content = dict(content)
        for key, val in list(content.items()):
            if isinstance(val, str) and "data:image" in val.lower():
                content[key] = rewrite_assistant_text(val, persist_fn=persist_fn)
            elif isinstance(val, (list, dict)):
                content[key] = rewrite_content(val, persist_fn=persist_fn)
        return content
    return content


def looks_like_b64_chunk(text: str) -> bool:
    return bool(isinstance(text, str) and _LOOKS_B64.match(text or ""))


HELPERS = r'''
# DATA_URI_OUTLET_V2 — strip assistant inline data:image markdown; keep http(s) links.
_OUTLET_MD_DATA_URI = re.compile(
    r"!?\[([^\]]*)\]\((data:image/[A-Za-z0-9.+-]+;base64,[A-Za-z0-9+/=\s]+)\)?",
    re.I,
)
_OUTLET_BARE_DATA_URI = re.compile(
    r"data:image/[A-Za-z0-9.+-]+;base64,[A-Za-z0-9+/=\s]+",
    re.I,
)
_OUTLET_DANGLING_MD = re.compile(
    r"!?\[([^\]]*)\]\((?:data:image/[^\)]*)?\)?\s*$",
    re.I,
)
_OUTLET_LOOKS_B64 = re.compile(r"^[A-Za-z0-9+/=\s]{16,}$")
_OUTLET_DROP = set()


def _outlet_rewrite_text(text: str, persist_map=None) -> str:
    del persist_map
    if not isinstance(text, str):
        return text
    if "data:image" not in text.lower():
        return _OUTLET_DANGLING_MD.sub("", text).rstrip()
    rewritten = _OUTLET_MD_DATA_URI.sub("", text)
    rewritten = _OUTLET_BARE_DATA_URI.sub("", rewritten)
    rewritten = _OUTLET_DANGLING_MD.sub("", rewritten)
    rewritten = re.sub(r"\n{3,}", "\n\n", rewritten).rstrip()
    return rewritten


def _outlet_rewrite_content(content, persist_map=None):
    persist_map = persist_map or {}
    if isinstance(content, str):
        return _outlet_rewrite_text(content, persist_map)
    if isinstance(content, list):
        out = []
        for block in content:
            if isinstance(block, dict):
                block = dict(block)
                for key in ("text", "content"):
                    val = block.get(key)
                    if isinstance(val, str):
                        block[key] = _outlet_rewrite_text(val, persist_map)
                    elif isinstance(val, list):
                        block[key] = _outlet_rewrite_content(val, persist_map)
                out.append(block)
            elif isinstance(block, str):
                out.append(_outlet_rewrite_text(block, persist_map))
            else:
                out.append(block)
        return out
    if isinstance(content, dict):
        content = dict(content)
        for key, val in list(content.items()):
            if isinstance(val, str):
                content[key] = _outlet_rewrite_text(val, persist_map)
            elif isinstance(val, (list, dict)):
                content[key] = _outlet_rewrite_content(val, persist_map)
        return content
    return content
'''

METHODS = r'''
    def _outlet_meta_key(self, __metadata__, event: dict | None = None) -> str:
        if isinstance(__metadata__, dict):
            cid = str(__metadata__.get("chat_id") or "")
            mid = str(__metadata__.get("message_id") or "")
            if cid or mid:
                return f"{cid}|{mid}"
        if isinstance(event, dict) and event.get("id"):
            return str(event.get("id"))
        return ""

    async def _outlet_rewrite_value(self, value, user_id: str | None = None, persist: bool = False):
        del user_id, persist
        if isinstance(value, str):
            return _outlet_rewrite_text(value)
        if isinstance(value, (list, dict)):
            return _outlet_rewrite_content(value)
        return value

    async def stream(
        self,
        event: dict,
        __user__: Optional[dict] = None,
        __metadata__: Optional[dict] = None,
    ) -> dict:
        if not isinstance(event, dict):
            return event
        user_id = __user__.get("id") if isinstance(__user__, dict) else None
        key = self._outlet_meta_key(__metadata__, event)

        async def clean_delta(text: str) -> str:
            if not isinstance(text, str) or not text:
                return text
            dropping = key in _OUTLET_DROP if key else False
            if dropping and _OUTLET_LOOKS_B64.match(text):
                return ""
            if dropping and "data:image" not in text.lower() and not _OUTLET_LOOKS_B64.match(text):
                _OUTLET_DROP.discard(key)
            rewritten = _outlet_rewrite_text(text, {})
            if "data:image" in text.lower() or rewritten != text:
                if key:
                    if len(_OUTLET_DROP) > 128:
                        _OUTLET_DROP.clear()
                    _OUTLET_DROP.add(key)
            return rewritten

        for choice in event.get("choices") or []:
            if not isinstance(choice, dict):
                continue
            delta = choice.get("delta")
            if isinstance(delta, dict) and isinstance(delta.get("content"), str):
                delta["content"] = await clean_delta(delta["content"])
            message = choice.get("message")
            if isinstance(message, dict):
                message["content"] = await self._outlet_rewrite_value(
                    message.get("content"), user_id, persist=True
                )
            if choice.get("finish_reason") and key:
                _OUTLET_DROP.discard(key)

        event_type = str(event.get("type") or "")
        if event_type == "response.output_text.delta" and isinstance(event.get("delta"), str):
            event["delta"] = await clean_delta(event["delta"])
        elif event_type == "response.output_text.done" and isinstance(event.get("text"), str):
            event["text"] = await self._outlet_rewrite_value(event["text"], user_id, persist=True)
        elif event_type == "response.content_part.done":
            part = event.get("part")
            if isinstance(part, dict) and "text" in part:
                part["text"] = await self._outlet_rewrite_value(part.get("text"), user_id, persist=True)
        elif event_type == "response.output_item.done":
            item = event.get("item")
            if isinstance(item, dict) and item.get("type") == "message":
                item["content"] = await self._outlet_rewrite_value(item.get("content"), user_id, persist=True)
        elif event_type == "response.completed":
            response = event.get("response")
            if isinstance(response, dict):
                output = response.get("output")
                if isinstance(output, list):
                    response["output"] = await self._outlet_rewrite_value(output, user_id, persist=True)
            if key:
                _OUTLET_DROP.discard(key)
        if event.get("done") and key:
            _OUTLET_DROP.discard(key)
        return event

    async def outlet(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __metadata__: Optional[dict] = None,
    ) -> dict:
        if not isinstance(body, dict):
            return body
        user_id = __user__.get("id") if isinstance(__user__, dict) else None
        messages = body.get("messages")
        if isinstance(messages, list):
            for msg in messages:
                if not isinstance(msg, dict):
                    continue
                if msg.get("role") != "assistant":
                    continue
                msg["content"] = await self._outlet_rewrite_value(msg.get("content"), user_id, persist=True)
                if "output" in msg:
                    msg["output"] = await self._outlet_rewrite_value(msg.get("output"), user_id, persist=True)
        for choice in body.get("choices") or []:
            if not isinstance(choice, dict):
                continue
            message = choice.get("message")
            if isinstance(message, dict):
                message["content"] = await self._outlet_rewrite_value(
                    message.get("content"), user_id, persist=True
                )
        key = self._outlet_meta_key(__metadata__, None)
        if key:
            _OUTLET_DROP.discard(key)
        return body
'''


def content_sha12(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def patch_content(original: str) -> str:
    if MARKER in original:
        return original
    if MARKER_V1 in original:
        content = original
        content = content.replace(
            '                return f"![{alt}]({url})"',
            '                return ""',
        )
        content = content.replace(
            '                return f"![image]({url})"',
            '                return ""',
        )
        content = content.replace(
            "async def _outlet_persist_image(self, raw: bytes, mime: str, user_id: str | None) -> str | None:\n        if not raw or not user_id:\n            return None",
            "async def _outlet_persist_image(self, raw: bytes, mime: str, user_id: str | None) -> str | None:\n        return None\n        if not raw or not user_id:\n            return None",
        )
        content = content.replace(MARKER_V1, MARKER)
        content = content.replace(
            "persist-or-strip assistant inline data-URI markdown (ST-14).",
            "strip assistant inline data-URI markdown; keep http(s) links (ST-14).",
        )
        content = content.replace(
            "persist-or-strip assistant inline data:image markdown.",
            "strip assistant inline data:image markdown; keep http(s) links.",
        )
        if MARKER not in content:
            raise RuntimeError("V1→V2 upgrade failed to insert marker")
        return content
    if "class Filter:" not in original:
        raise RuntimeError("guard missing class Filter")
    if "def inlet(" not in original:
        raise RuntimeError("guard missing inlet")
    content = original
    content = content.replace(
        "description: Trim historical images in multi-turn image chats to avoid context token overflows.",
        "description: Trim historical image chats; strip assistant inline data-URI markdown; keep http(s) links (ST-14).",
        1,
    )
    content = content.replace("version: 0.1.0", "version: 0.2.0", 1)
    content = content.replace("class Filter:", HELPERS.rstrip() + "\n\nclass Filter:", 1)
    if not content.endswith("\n"):
        content += "\n"
    content += "\n" + METHODS.lstrip("\n")
    if MARKER not in content:
        raise RuntimeError("patch failed to insert marker")
    if "async def outlet(" not in content or "async def stream(" not in content:
        raise RuntimeError("patch failed to insert stream/outlet")
    return content


def _login_candidates() -> list[str]:
    candidates: list[str] = []
    for value in (os.environ.get("OPENWEBUI_USERNAME"), os.environ.get("OPENWEBUI_EMAIL")):
        if value and value not in candidates:
            candidates.append(value)
    return candidates


def signin() -> str:
    if not OPENWEBUI_URL or not os.environ.get("OPENWEBUI_PASSWORD"):
        raise SystemExit("Missing OPENWEBUI_URL / OPENWEBUI_PASSWORD")
    last = ""
    for ident in _login_candidates():
        resp = requests.post(
            f"{OPENWEBUI_URL}/api/v1/auths/signin",
            json={"email": ident, "password": os.environ["OPENWEBUI_PASSWORD"]},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()["token"]
        last = f"{resp.status_code} {resp.text[:160]}"
    raise SystemExit(f"signin failed: {last}")


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _assistant_source_text(msg: dict) -> str:
    content = msg.get("content")
    if isinstance(content, str) and "data:image" in content.lower():
        return content
    output = msg.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            inner = item.get("content")
            if isinstance(inner, str) and "data:image" in inner.lower():
                return inner
            if isinstance(inner, list):
                for part in inner:
                    if isinstance(part, dict) and isinstance(part.get("text"), str) and "data:image" in part["text"].lower():
                        return part["text"]
    if isinstance(content, str):
        return content
    return ""


def sanitize_chat(token: str, chat_id: str) -> int:
    h = headers(token)
    resp = requests.get(f"{OPENWEBUI_URL}/api/v1/chats/{chat_id}", headers=h, timeout=60)
    if resp.status_code != 200:
        raise SystemExit(f"get chat: {resp.status_code} {resp.text[:300]}")
    doc = resp.json()
    chat = doc.get("chat") or {}
    messages = ((chat.get("history") or {}).get("messages")) or {}
    updated = 0
    for mid, msg in messages.items():
        if not isinstance(msg, dict) or msg.get("role") != "assistant":
            continue
        source = _assistant_source_text(msg)
        if "data:image" not in source.lower() and "iVBORw0KGgo" not in source:
            continue
        cleaned = rewrite_assistant_text(source)
        if cleaned == msg.get("content"):
            continue
        # Admin can edit another user's message content; POST /chats/{id} is owner-only.
        patch = requests.post(
            f"{OPENWEBUI_URL}/api/v1/chats/{chat_id}/messages/{mid}",
            headers=h,
            json={"content": cleaned},
            timeout=60,
        )
        if patch.status_code != 200:
            raise SystemExit(f"update message {mid}: {patch.status_code} {patch.text[:400]}")
        updated += 1
        print(f"updated message {mid} len {len(source)} -> {len(cleaned)}")

    check = requests.get(f"{OPENWEBUI_URL}/api/v1/chats/{chat_id}", headers=h, timeout=60).json()
    hist = ((check.get("chat") or {}).get("history") or {}).get("messages") or {}
    leftover_content = 0
    leftover_output = 0
    for msg in hist.values():
        if not isinstance(msg, dict):
            continue
        content = msg.get("content") or ""
        if isinstance(content, str) and "data:image" in content:
            leftover_content += 1
        if "data:image" in str(msg.get("output") or ""):
            leftover_output += 1
    print(
        f"chat {chat_id}: messages_updated={updated} "
        f"leftover_content={leftover_content} leftover_output={leftover_output}"
    )
    if leftover_content:
        raise SystemExit("sanitize left data:image in visible content")
    return 0


def apply_guard(token: str, dry_run: bool = False) -> int:
    h = headers(token)
    fn = requests.get(f"{OPENWEBUI_URL}/api/v1/functions/id/{GUARD_ID}", headers=h, timeout=60)
    if fn.status_code != 200:
        raise SystemExit(f"get guard: {fn.status_code} {fn.text[:300]}")
    guard = fn.json()
    original = guard.get("content") or ""
    new_content = patch_content(original)
    print(f"guard={GUARD_ID}")
    print(f"sha256[:12] before={content_sha12(original)} after={content_sha12(new_content)}")
    print(f"marker={MARKER} present={MARKER in new_content}")
    print(f"is_active={guard.get('is_active')} is_global={guard.get('is_global')}")
    if new_content == original:
        print("already patched; no content change")
        return 0
    if dry_run:
        print("dry-run: not POSTing")
        return 0
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/functions/id/{GUARD_ID}/update",
        headers=h,
        json={
            "id": GUARD_ID,
            "name": guard.get("name"),
            "meta": guard.get("meta") or {},
            "content": new_content,
        },
        timeout=120,
    )
    if resp.status_code != 200:
        raise SystemExit(f"update guard: {resp.status_code} {resp.text[:500]}")
    print("guard content updated DATA_URI_OUTLET_V2 (content-only; valves untouched)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--from-file", default="")
    parser.add_argument("--write-patched", default="")
    parser.add_argument("--sanitize-chat", default="")
    args = parser.parse_args()

    if args.from_file:
        with open(args.from_file, encoding="utf-8") as fh:
            original = fh.read()
        new_content = patch_content(original)
        print(f"sha256[:12] before={content_sha12(original)} after={content_sha12(new_content)}")
        print(f"marker present={MARKER in new_content}")
        if args.write_patched:
            with open(args.write_patched, "w", encoding="utf-8") as fh:
                fh.write(new_content)
            print(f"wrote {args.write_patched}")
        return 0

    token = signin()
    rc = apply_guard(token, dry_run=args.dry_run)
    if args.sanitize_chat and not args.dry_run:
        rc = sanitize_chat(token, args.sanitize_chat) or rc
    return rc


if __name__ == "__main__":
    sys.exit(main())
