#!/usr/bin/env python3
"""W5: install/attach official X recent-search tool.

Does not change Pipe valves. Merges tool valves. Does not overwrite an existing token.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apply_x_recent_search import attach_tool, merge_valves, upsert_tool
from stack_contract import X_RECENT_SEARCH_MODEL_IDS
from text_web_search_ops import headers, signin
from verify_x_recent_search import main as verify_x_main


def main() -> int:
    h = headers(signin())
    upsert_tool(h)
    merge_valves(h)
    attach_tool(h, X_RECENT_SEARCH_MODEL_IDS, attach=True)
    print("apply W5 X recent search ok")
    return verify_x_main()


if __name__ == "__main__":
    sys.exit(main())
