#!/usr/bin/env python3
"""M1a: upsert ST-16 drive tools with via[] + legs[]. Merge valves only."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apply_amap_drive_route import merge_valves as merge_amap_valves
from apply_amap_drive_route import upsert_tool as upsert_amap
from apply_google_drive_route import merge_valves as merge_google_valves
from apply_google_drive_route import upsert_tool as upsert_google
from text_web_search_ops import headers, signin
from verify_amap_drive_route import main as verify_amap_main
from verify_google_drive_route import main as verify_google_main


def main() -> int:
    h = headers(signin())
    upsert_amap(h)
    merge_amap_valves(h)
    upsert_google(h)
    merge_google_valves(h)
    print("apply M1a drive via/legs ok")
    amap = verify_amap_main()
    google = verify_google_main()
    return 0 if amap == 0 and google == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
