#!/usr/bin/env python3
"""Retire openai.gpt-image-2 on OWUI. Keep Flare / Sunburst public.

Disable + strip * read. Does not sync, rewrite banners, or touch Studio.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apply_picker_prune import get_model, headers, signin, strip_public_grant, update_active
from stack_contract import GPT_IMAGE_25_FLARE_ID, GPT_IMAGE_25_SUNBURST_ID, PIPE

IMAGE2_ID = f"{PIPE}.openai.gpt-image-2"


def is_public(grants: list) -> bool:
    return any(g.get("principal_id") == "*" and g.get("permission") == "read" for g in (grants or []))


def main() -> int:
    h = headers(signin())
    model = get_model(h, IMAGE2_ID)
    if not model:
        raise SystemExit(f"missing {IMAGE2_ID}")
    if strip_public_grant(h, model):
        print(f"strip * {model.get('name')}")
        model = get_model(h, IMAGE2_ID) or model
    if update_active(h, model, False):
        print(f"disable {model.get('name')}")
    else:
        print(f"already inactive {model.get('name')}")

    saved = get_model(h, IMAGE2_ID) or {}
    if saved.get("is_active"):
        raise SystemExit("image-2 still active")
    if is_public(saved.get("access_grants") or []):
        raise SystemExit("image-2 still public")

    for mid, label in (
        (GPT_IMAGE_25_FLARE_ID, "flare"),
        (GPT_IMAGE_25_SUNBURST_ID, "sunburst"),
    ):
        row = get_model(h, mid)
        if not row or row.get("is_active") is False or not is_public(row.get("access_grants") or []):
            raise SystemExit(f"{label} must stay public active")
        print(f"keep {row.get('name')} public")
    print("gpt-image-2 retired")
    return 0


if __name__ == "__main__":
    sys.exit(main())
