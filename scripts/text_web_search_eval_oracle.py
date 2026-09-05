"""Independent oracle for EVAL-B dynamic Fetch. No model calls."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

FETCH_URL = "https://api.github.com/repos/open-webui/open-webui/releases/latest"
ORACLE_HEADERS = {
    "User-Agent": "micropigeon-st14-eval/1.0",
    "Accept": "application/vnd.github+json",
}


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
    if not isinstance(published, str) or len(published) < 10:
        raise OracleError("oracle missing published_at")
    return {
        "url": FETCH_URL,
        "tag_name": tag,
        "published_at": published,
        "published_day": published[:10],
        "etag": response.headers.get("ETag"),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def normalize_tag(tag: str) -> str:
    return tag.lstrip("vV").strip().lower()


def oracle_fields_in_text(text: str, oracle: dict[str, Any] | None) -> dict[str, bool]:
    if not oracle:
        return {"tag_ok": False, "date_ok": False, "url_ok": False}
    body = text or ""
    lowered = body.lower()
    tag = str(oracle.get("tag_name") or "")
    tag_ok = bool(tag) and (tag.lower() in lowered or normalize_tag(tag) in lowered)
    day = str(oracle.get("published_day") or oracle.get("published_at") or "")[:10]
    date_ok = bool(day) and day in body
    url = str(oracle.get("url") or FETCH_URL)
    url_ok = url in body
    return {"tag_ok": tag_ok, "date_ok": date_ok, "url_ok": url_ok}


def oracle_answer_ok(text: str, oracle: dict[str, Any] | None) -> bool:
    fields = oracle_fields_in_text(text, oracle)
    return fields["tag_ok"] and fields["date_ok"]
