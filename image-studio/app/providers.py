from __future__ import annotations

import base64
import binascii
import io
from typing import Any

import httpx
from PIL import Image

from . import config
from .catalog import get_model, openai_size


def _require_key(provider: str) -> str:
    try:
        return config.require_key(provider)
    except RuntimeError as exc:
        raise ProviderError(str(exc), 503) from exc


class ProviderError(RuntimeError):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def _decode_b64(data: str) -> bytes:
    raw = data.split(",", 1)[-1] if data.startswith("data:") else data
    return base64.b64decode(raw)


def _png_data_url(image: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(image).decode("ascii")


def _extract_openai_image(payload: dict[str, Any]) -> bytes:
    rows = payload.get("data") or []
    if not rows:
        raise ProviderError("upstream returned no image")
    row = rows[0]
    if row.get("b64_json"):
        return _decode_b64(row["b64_json"])
    url = row.get("url")
    if not url:
        raise ProviderError("upstream image missing url/b64")
    with httpx.Client(timeout=60.0) as client:
        resp = client.get(url)
        if resp.status_code != 200:
            raise ProviderError(f"download image {resp.status_code}")
        return resp.content


def _extract_gemini_image(payload: dict[str, Any]) -> bytes:
    for cand in payload.get("candidates") or []:
        parts = ((cand.get("content") or {}).get("parts")) or []
        for part in parts:
            inline = part.get("inlineData") or part.get("inline_data") or {}
            data = inline.get("data")
            if data:
                return _decode_b64(data)
    raise ProviderError("gemini returned no image part")


def generate(*, model_id: str, prompt: str, aspect: str, resolution: str, quality: str) -> bytes:
    spec = get_model(model_id)
    provider = spec["provider"]
    if provider == "openai":
        return _openai_generate(spec, prompt, aspect, quality)
    if provider == "google":
        return _gemini_generate(spec, prompt, aspect, resolution, refs=[])
    if provider == "xai":
        return _xai_generate(spec, prompt, aspect, resolution, quality)
    if provider == "openrouter":
        return _openrouter_generate(spec, prompt, aspect, resolution, refs=[])
    raise ProviderError(f"unknown provider {provider}")


def edit(
    *,
    model_id: str,
    prompt: str,
    canvas: bytes,
    mask: bytes | None,
    aspect: str,
    resolution: str,
    quality: str,
) -> bytes:
    spec = get_model(model_id)
    provider = spec["provider"]
    if provider == "openai":
        return _openai_edit(spec, prompt, canvas, mask, aspect, quality)
    if provider == "google":
        return _gemini_generate(spec, prompt, aspect, resolution, refs=[canvas])
    if provider == "xai":
        return _xai_edit(spec, prompt, canvas, aspect)
    if provider == "openrouter":
        return _openrouter_generate(spec, prompt, aspect, resolution, refs=[canvas])
    raise ProviderError(f"unknown provider {provider}")


def _openai_generate(spec: dict[str, Any], prompt: str, aspect: str, quality: str) -> bytes:
    key = _require_key("openai")
    body: dict[str, Any] = {
        "model": spec["upstream"],
        "prompt": prompt,
        "size": openai_size(aspect),
        "n": 1,
    }
    if quality:
        body["quality"] = quality
    with httpx.Client(timeout=180.0) as client:
        resp = client.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {key}"},
            json=body,
        )
    if resp.status_code != 200:
        raise ProviderError(_short_err("openai", resp), resp.status_code)
    return _extract_openai_image(resp.json())


def _openai_edit(
    spec: dict[str, Any],
    prompt: str,
    canvas: bytes,
    mask: bytes | None,
    aspect: str,
    quality: str,
) -> bytes:
    key = _require_key("openai")
    files = {
        "image": ("image.png", canvas, "image/png"),
        "prompt": (None, prompt),
        "model": (None, spec["upstream"]),
        "size": (None, openai_size(aspect)),
        "n": (None, "1"),
    }
    if quality:
        files["quality"] = (None, quality)
    if mask:
        files["mask"] = ("mask.png", normalize_openai_mask(mask, canvas), "image/png")
    with httpx.Client(timeout=180.0) as client:
        resp = client.post(
            "https://api.openai.com/v1/images/edits",
            headers={"Authorization": f"Bearer {key}"},
            files=files,
        )
    if resp.status_code != 200:
        raise ProviderError(_short_err("openai", resp), resp.status_code)
    return _extract_openai_image(resp.json())


def _gemini_generate(
    spec: dict[str, Any],
    prompt: str,
    aspect: str,
    resolution: str,
    refs: list[bytes],
) -> bytes:
    key = _require_key("google")
    parts: list[dict[str, Any]] = [{"text": prompt}]
    for blob in refs[: spec["refs_max"]]:
        parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(blob).decode("ascii")}})
    body: dict[str, Any] = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {"aspectRatio": aspect},
        },
    }
    if resolution:
        body["generationConfig"]["imageConfig"]["imageSize"] = resolution
    model = spec["upstream"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    with httpx.Client(timeout=180.0) as client:
        resp = client.post(url, params={"key": key}, json=body)
        if resp.status_code == 404 and model.endswith("-preview"):
            fallback = model.replace("-preview", "")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{fallback}:generateContent"
            resp = client.post(url, params={"key": key}, json=body)
    if resp.status_code != 200:
        raise ProviderError(_short_err("gemini", resp), resp.status_code)
    return _extract_gemini_image(resp.json())


def _xai_generate(spec: dict[str, Any], prompt: str, aspect: str, resolution: str, quality: str) -> bytes:
    key = _require_key("xai")
    body: dict[str, Any] = {
        "model": spec["upstream"],
        "prompt": prompt,
        "n": 1,
        "aspect_ratio": aspect,
    }
    if resolution:
        body["resolution"] = resolution
    if quality:
        body["quality"] = quality
    with httpx.Client(timeout=180.0) as client:
        resp = client.post(
            "https://api.x.ai/v1/images/generations",
            headers={"Authorization": f"Bearer {key}"},
            json=body,
        )
    if resp.status_code != 200:
        raise ProviderError(_short_err("xai", resp), resp.status_code)
    return _extract_openai_image(resp.json())


def _xai_edit(spec: dict[str, Any], prompt: str, canvas: bytes, aspect: str) -> bytes:
    key = _require_key("xai")
    body = {
        "model": spec["upstream"],
        "prompt": prompt,
        "aspect_ratio": aspect,
        "image": {"url": _png_data_url(canvas), "type": "image_url"},
    }
    with httpx.Client(timeout=180.0) as client:
        resp = client.post(
            "https://api.x.ai/v1/images/edits",
            headers={"Authorization": f"Bearer {key}"},
            json=body,
        )
    if resp.status_code != 200:
        raise ProviderError(_short_err("xai", resp), resp.status_code)
    return _extract_openai_image(resp.json())


def _openrouter_generate(
    spec: dict[str, Any],
    prompt: str,
    aspect: str,
    resolution: str,
    refs: list[bytes],
) -> bytes:
    key = _require_key("openrouter")
    body: dict[str, Any] = {
        "model": spec["upstream"],
        "prompt": prompt,
        "aspect_ratio": aspect,
        "n": 1,
    }
    if resolution:
        body["resolution"] = resolution
    if refs:
        body["input_references"] = [
            {"type": "image_url", "image_url": {"url": _png_data_url(blob)}}
            for blob in refs[: spec["refs_max"]]
        ]
    with httpx.Client(timeout=180.0) as client:
        resp = client.post(
            "https://openrouter.ai/api/v1/images",
            headers={
                "Authorization": f"Bearer {key}",
                "HTTP-Referer": config.PUBLIC_URL,
                "X-Title": "micropigeon image studio",
            },
            json=body,
        )
    if resp.status_code != 200:
        raise ProviderError(_short_err("openrouter", resp), resp.status_code)
    payload = resp.json()
    if payload.get("data"):
        return _extract_openai_image(payload)
    images = payload.get("images") or []
    if images and images[0].get("b64_json"):
        return _decode_b64(images[0]["b64_json"])
    raise ProviderError("openrouter returned no image")


def normalize_openai_mask(mask: bytes, canvas: bytes) -> bytes:
    """OpenAI: transparent pixels are edited. UI paints the edit region as white."""
    try:
        src = Image.open(io.BytesIO(canvas)).convert("RGBA")
        painted = Image.open(io.BytesIO(mask)).convert("RGBA")
        painted = painted.resize(src.size)
        out = Image.new("RGBA", src.size, (0, 0, 0, 255))
        pixels = list(painted.getdata())
        dest = []
        for r, g, b, a in pixels:
            bright = (r + g + b) / 3
            if a > 20 and bright > 20:
                dest.append((0, 0, 0, 0))
            else:
                dest.append((0, 0, 0, 255))
        out.putdata(dest)
        buf = io.BytesIO()
        out.save(buf, format="PNG")
        return buf.getvalue()
    except (OSError, ValueError, binascii.Error) as exc:
        raise ProviderError(f"bad mask: {exc}") from exc


def _short_err(name: str, resp: httpx.Response) -> str:
    text = (resp.text or "")[:240].replace("\n", " ")
    return f"{name} {resp.status_code}: {text}"
