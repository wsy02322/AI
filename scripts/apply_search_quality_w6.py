#!/usr/bin/env python3
"""W6: OpenAI Search+Fetch engine=native + max_tool_calls=3.

Upserts the thin Filter and forwards max_tool_calls on the Pipe.
Does not change Pipe valves. Google/xAI native unchanged.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from patch_pipe_max_tool_calls import main as patch_pipe_main
from text_web_search_ops import headers, refresh_runtime_models, signin, upsert_filter
from verify_text_web_search import verify_mode


def main() -> int:
    h = headers(signin())
    upsert_filter(h)
    refresh_runtime_models(h)
    pipe_code = patch_pipe_main()
    if pipe_code != 0:
        return pipe_code
    print("apply W6 OpenAI native + max_tool_calls=3 ok")
    return verify_mode(h, "final")


if __name__ == "__main__":
    sys.exit(main())
