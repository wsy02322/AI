#!/usr/bin/env python3
"""W4: install/attach Google Routes overseas tool. Refresh Amap docstring.

Does not change Pipe valves. Merges tool valves. Does not overwrite existing keys.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apply_amap_drive_route import merge_valves as merge_amap_valves
from apply_amap_drive_route import upsert_tool as upsert_amap
from apply_google_drive_route import attach_tool, merge_valves, upsert_tool
from stack_contract import GOOGLE_DRIVE_ROUTE_MODEL_IDS
from text_web_search_ops import headers, signin
from verify_google_drive_route import main as verify_google_main


def main() -> int:
    h = headers(signin())
    upsert_amap(h)
    merge_amap_valves(h)
    upsert_tool(h)
    merge_valves(h)
    attach_tool(h, GOOGLE_DRIVE_ROUTE_MODEL_IDS, attach=True)
    print("apply W4 Google Routes ok")
    return verify_google_main()


if __name__ == "__main__":
    sys.exit(main())
