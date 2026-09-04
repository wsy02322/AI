from __future__ import annotations

import os
from pathlib import Path


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


OPENWEBUI_URL = _env("OPENWEBUI_URL", "https://micropigeon.com").rstrip("/")
HOST = _env("STUDIO_HOST", "127.0.0.1")
PORT = int(_env("STUDIO_PORT", "8091"))
PUBLIC_URL = _env("STUDIO_PUBLIC_URL", "https://image.micropigeon.com").rstrip("/")
DATA_DIR = Path(_env("STUDIO_DATA_DIR") or str(Path(__file__).resolve().parent.parent / "data"))
SECRET_KEY = _env("STUDIO_SECRET_KEY") or "dev-only-change-me"
COOKIE_NAME = "studio_session"
SESSION_DAYS = 7

COOKIE_SECURE = _env("STUDIO_COOKIE_SECURE") in {"1", "true", "yes"}

OPENAI_KEY = _env("STUDIO_OPENAI_API_KEY")
GEMINI_KEY = _env("STUDIO_GEMINI_API_KEY")
XAI_KEY = _env("STUDIO_XAI_API_KEY")
OPENROUTER_KEY = _env("STUDIO_OPENROUTER_API_KEY")


def key_status() -> dict[str, bool]:
    return {
        "openai": bool(OPENAI_KEY),
        "google": bool(GEMINI_KEY),
        "xai": bool(XAI_KEY),
        "openrouter": bool(OPENROUTER_KEY),
    }


def require_key(provider: str) -> str:
    mapping = {
        "openai": OPENAI_KEY,
        "google": GEMINI_KEY,
        "xai": XAI_KEY,
        "openrouter": OPENROUTER_KEY,
    }
    key = mapping.get(provider) or ""
    if not key:
        raise RuntimeError(f"missing key for {provider}")
    return key
