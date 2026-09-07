#!/usr/bin/env python3
"""Detach ST-16 Amap drive-route Tool from all models. Leaves the Tool installed."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apply_amap_drive_route import attach_tool
from text_web_search_ops import headers, signin


def main() -> int:
    h = headers(signin())
    attach_tool(h, [], attach=False)
    print("rollback ok: amap toolIds stripped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
