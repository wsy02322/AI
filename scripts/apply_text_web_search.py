#!/usr/bin/env python3
"""Install or attach the thin text Web Search Filter. Does not change Pipe valves."""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import TEXT_WEB_SEARCH_CANARY_MODEL_ID, TEXT_WEB_SEARCH_MODEL_IDS
from text_web_search_ops import (
    attach_models,
    headers,
    set_active,
    set_global,
    set_valves,
    signin,
    upsert_filter,
)
from verify_text_web_search import verify_mode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        required=True,
        choices=("install", "canary", "attach", "final"),
        help="install=inactive no attach; canary=Flash only; attach=7 models; final=default-on",
    )
    args = parser.parse_args()
    h = headers(signin())
    upsert_filter(h)
    set_global(h, "openrouter_text_web_search", False)
    set_valves(h)
    if args.mode == "install":
        set_active(h, "openrouter_text_web_search", False)
        attach_models(h, [], default_on=False)
    elif args.mode == "canary":
        set_active(h, "openrouter_text_web_search", True)
        attach_models(h, [TEXT_WEB_SEARCH_CANARY_MODEL_ID], default_on=False)
    elif args.mode == "attach":
        set_active(h, "openrouter_text_web_search", True)
        attach_models(h, TEXT_WEB_SEARCH_MODEL_IDS, default_on=False)
    else:
        set_active(h, "openrouter_text_web_search", True)
        attach_models(h, TEXT_WEB_SEARCH_MODEL_IDS, default_on=True)
    print(f"apply mode={args.mode} ok")
    return verify_mode(h, args.mode)


if __name__ == "__main__":
    sys.exit(main())
