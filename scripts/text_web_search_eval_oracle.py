"""Independent oracle for EVAL-B dynamic Fetch. No model calls."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import requests

FETCH_URL = "https://api.github.com/repos/open-webui/open-webui/releases/latest"
ORACLE_HEADERS = {
    "User-Agent": "micropigeon-st14-eval/1.0",
    "Accept": "application/vnd.github+json",
}
ORACLE_SCHEMA = "github-release-v2"
# tag_name is a whole token: v0.11.3 must not match v0.11.30.
_TOKEN_EDGE = r"A-Za-z0-9._-"


class OracleError(RuntimeError):
    pass


def fetch_github_latest_oracle(*, timeout: int = 30) -> dict[str, Any]:
    response = requests.get(FETCH_URL, headers=ORACLE_HEADERS, timeout=timeout)
    if response.status_code != 200:
        raise OracleError(f"oracle GET {response.status_code} {response.text[:200]}")
    data = response.json()
    tag = data.get("tag_name")
    published = data.get("published_at")
    if not isinstance(tag, str) or not tag:
        raise OracleError("oracle missing tag_name")
    if not isinstance(published, str) or "T" not in published:
        raise OracleError("oracle missing published_at RFC3339")
    return {
        "url": FETCH_URL,
        "tag_name": tag,
        "published_at": published,
        "published_day": published[:10],
        "oracle_schema": ORACLE_SCHEMA,
        "etag": response.headers.get("ETag"),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def normalize_tag(tag: str) -> str:
    return tag.lstrip("vV").strip().lower()


def token_in_text(token: str, text: str) -> bool:
    if not token:
        return False
    pattern = re.compile(
        rf"(?<![{_TOKEN_EDGE}]){re.escape(token)}(?![{_TOKEN_EDGE}])",
        re.IGNORECASE,
    )
    return bool(pattern.search(text or ""))


def oracle_fields_in_text(text: str, oracle: dict[str, Any] | None) -> dict[str, bool]:
    if not oracle:
        return {"tag_ok": False, "date_ok": False, "url_ok": False}
    body = text or ""
    tag = str(oracle.get("tag_name") or "")
    tag_ok = token_in_text(tag, body) or token_in_text(normalize_tag(tag), body)
    published = str(oracle.get("published_at") or "")
    date_ok = bool(published) and published in body
    url = str(oracle.get("url") or FETCH_URL)
    url_ok = url in body
    return {"tag_ok": tag_ok, "date_ok": date_ok, "url_ok": url_ok}


def oracle_answer_ok(text: str, oracle: dict[str, Any] | None) -> bool:
    fields = oracle_fields_in_text(text, oracle)
    return fields["tag_ok"] and fields["date_ok"]
