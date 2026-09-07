#!/usr/bin/env python3
"""W3: upsert thin Web Search Filter so xAI class uses engine=native.

Does not change Pipe valves, Filter valves, attachments, or OpenAI/Google Exa.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from text_web_search_ops import headers, refresh_runtime_models, signin, upsert_filter
from verify_text_web_search import verify_mode


def main() -> int:
    h = headers(signin())
    upsert_filter(h)
    refresh_runtime_models(h)
    print("apply W3 xAI native ok")
    return verify_mode(h, "final")


if __name__ == "__main__":
    sys.exit(main())
