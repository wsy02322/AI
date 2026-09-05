#!/usr/bin/env python3
"""Detach and deactivate the thin text Web Search Filter. Leaves the Function installed."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from text_web_search_ops import detach_all, get_function, headers, set_active, set_global, signin


def main() -> int:
    h = headers(signin())
    status, existing = get_function(h, "openrouter_text_web_search")
    if status in (401, 404) or not existing:
        print("thin filter not installed; nothing to roll back")
        return 0
    detach_all(h)
    set_global(h, "openrouter_text_web_search", False)
    set_active(h, "openrouter_text_web_search", False)
    print("rollback ok: filter detached and inactive")
    return 0


if __name__ == "__main__":
    sys.exit(main())
