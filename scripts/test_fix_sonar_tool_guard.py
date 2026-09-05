#!/usr/bin/env python3
"""Unit tests for the Sonar filter repair payload (no live writes)."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import fix_sonar_tool_guard as target


class ResetSonarFiltersTests(unittest.TestCase):
    @patch.object(target.requests, "post")
    @patch.object(target.requests, "get")
    def test_preserves_complete_model_and_access_grants(self, get: Mock, post: Mock) -> None:
        get.return_value = Mock(
            status_code=200,
            json=lambda: {
                "id": "open_webui_openrouter_integration.perplexity.sonar-pro-search",
                "name": "Sonar Pro Search",
                "meta": {
                    "filterIds": ["openrouter_web_tools", "another_filter"],
                    "capabilities": {"builtin_tools": False, "web_search": False},
                    "description": "keep me",
                },
                "params": {"function_calling": "native"},
                "is_active": True,
                "access_grants": [
                    {"principal_id": "*", "permission": "read"},
                    {"principal_id": "admin", "permission": "write"},
                ],
            },
            text="",
        )
        post.return_value = Mock(status_code=200, text="")

        previous_url = target.OPENWEBUI_URL
        target.OPENWEBUI_URL = "https://example.invalid"
        try:
            target.reset_sonar_filters({"Authorization": "Bearer test"}, "model-id")
        finally:
            target.OPENWEBUI_URL = previous_url

        post.assert_called_once()
        url = post.call_args.args[0]
        payload = post.call_args.kwargs["json"]
        self.assertEqual(url, "https://example.invalid/api/v1/models/model/update")
        self.assertEqual(payload["meta"]["filterIds"], ["openrouter_direct_uploads"])
        self.assertEqual(payload["meta"]["description"], "keep me")
        self.assertEqual(
            payload["meta"]["capabilities"],
            {"builtin_tools": False, "web_search": False},
        )
        self.assertEqual(payload["params"], {"function_calling": "native"})
        self.assertTrue(payload["is_active"])
        self.assertEqual(
            payload["access_grants"],
            [
                {"principal_id": "*", "permission": "read"},
                {"principal_id": "admin", "permission": "write"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
