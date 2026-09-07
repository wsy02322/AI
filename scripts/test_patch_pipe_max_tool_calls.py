#!/usr/bin/env python3
"""Unit tests for W6 Pipe max_tool_calls forward inject."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from patch_pipe_max_tool_calls import MARKER, inject
from search_quality_w0 import PIPE_STOP_ANCHOR


class PipeMaxToolCallsTests(unittest.TestCase):
    def test_inject_is_idempotent(self) -> None:
        stub = "prefix\n" + PIPE_STOP_ANCHOR + "\nnext\n"
        patched = inject(stub)
        self.assertIn(MARKER, patched)
        self.assertIn("responses_body.max_tool_calls = _mtc", patched)
        self.assertEqual(inject(patched), patched)
        self.assertEqual(patched.count(PIPE_STOP_ANCHOR), 1)


if __name__ == "__main__":
    unittest.main()
