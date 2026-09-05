#!/usr/bin/env python3
"""IS0: read OpenRouter Images catalog. Direct-key probes only if env keys exist."""

from __future__ import annotations

import json
import os
import sys
from urllib.request import Request, urlopen

OR_URL = "https://openrouter.ai/api/v1/images/models"


def fetch_or_catalog() -> list[dict]:
    req = Request(OR_URL, headers={"User-Agent": "micropigeon-image-studio/0.1"})
    with urlopen(req, timeout=45) as resp:
        payload = json.loads(resp.read().decode())
    return payload.get("data") or payload.get("models") or []


def summarize(rows: list[dict]) -> None:
    print(f"openrouter images models: {len(rows)}")
    wanted = (
        "gpt-image-2",
        "gemini-3-pro-image",
        "gemini-3.1-flash-image",
        "grok-imagine-image-2.0",
        "seedream-5-0-pro",
        "seedream-5-0-lite",
        "qwen-image-3-pro",
        "mai-image-2.5-pro",
    )
    for row in rows:
        ident = row.get("id") or ""
        if not any(token in ident for token in wanted):
            continue
        params = row.get("supported_parameters") or row.get("parameters") or []
        print(f"- {ident} params={params}")


def main() -> int:
    rows = fetch_or_catalog()
    summarize(rows)
    keys = {
        "openai": bool(os.environ.get("STUDIO_OPENAI_API_KEY")),
        "gemini": bool(os.environ.get("STUDIO_GEMINI_API_KEY")),
        "xai": bool(os.environ.get("STUDIO_XAI_API_KEY")),
        "openrouter": bool(os.environ.get("STUDIO_OPENROUTER_API_KEY")),
    }
    print("direct keys present:", {k: v for k, v in keys.items()})
    if not any(keys.values()):
        print("no studio keys in env; skip live generate probes (expected in this repo agent)")
        return 0
    print("keys exist: run verify_studio.py --live-generate on the VPS, do not paste keys here")
    return 0


if __name__ == "__main__":
    sys.exit(main())
