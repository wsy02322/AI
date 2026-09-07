"""
title: X Recent Posts
author: micropigeon
id: x_recent_search
description: Official X recent search (7 days). Compact posts, no embed UI.
version: 1.0.0
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from pydantic import BaseModel, Field

X_RECENT_SEARCH_V1 = "X_RECENT_SEARCH_V1"
UNAVAILABLE = "X 接口不可用"
SEARCH_URL = "https://api.x.com/2/tweets/search/recent"
QUERY_MAX = 512
TEXT_MAX = 180
API_MIN_RESULTS = 10
API_MAX_RESULTS = 20

_CALLS: dict[str, tuple[float, int]] = {}
HttpFn = Callable[[str, str, dict[str, str]], dict[str, Any]]


def fail(message: str = UNAVAILABLE, **extra: Any) -> str:
    payload = {
        "ok": False,
        "error": message,
        "hint": "不要编造 x.com/status 链接或推文正文",
    }
    payload.update(extra)
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def clip_text(text: str, limit: int = TEXT_MAX) -> str:
    raw = " ".join(str(text or "").split())
    if len(raw) <= limit:
        return raw
    return raw[: max(0, limit - 1)].rstrip() + "…"


def sanitize_query(query: str) -> str:
    text = " ".join(str(query or "").split())
    if len(text) > QUERY_MAX:
        text = text[:QUERY_MAX].rstrip()
    return text


def post_url(username: str, post_id: str) -> str:
    handle = (username or "").lstrip("@").strip()
    if handle:
        return f"https://x.com/{handle}/status/{post_id}"
    return f"https://x.com/i/status/{post_id}"


def compact_posts(data: dict[str, Any], *, query: str, limit: int) -> dict[str, Any]:
    users: dict[str, str] = {}
    includes = data.get("includes") if isinstance(data.get("includes"), dict) else {}
    raw_users = includes.get("users") if isinstance(includes, dict) else None
    if isinstance(raw_users, list):
        for user in raw_users:
            if not isinstance(user, dict):
                continue
            uid = str(user.get("id") or "")
            name = str(user.get("username") or "").strip()
            if uid and name:
                users[uid] = name
    posts: list[dict[str, str]] = []
    rows = data.get("data")
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            post_id = str(row.get("id") or "").strip()
            text = clip_text(str(row.get("text") or ""))
            if not post_id or not text:
                continue
            author_id = str(row.get("author_id") or "")
            author = users.get(author_id, "")
            posts.append(
                {
                    "author": author or author_id,
                    "time": str(row.get("created_at") or ""),
                    "text": text,
                    "url": post_url(author, post_id),
                }
            )
            if len(posts) >= limit:
                break
    return {
        "ok": True,
        "provider": "x_api",
        "window": "7d",
        "query": query,
        "posts": posts,
    }


def x_get(url: str, token: str, params: dict[str, str], http: HttpFn | None = None) -> dict[str, Any]:
    if http is not None:
        return http(url, token, params)
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{url}?{query}",
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "micropigeon-x-recent/1.0",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read().decode("utf-8", errors="replace")
        except Exception:
            return {}
    except Exception:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def lookup_posts(
    token: str,
    query: str,
    *,
    max_results: int,
    http: HttpFn | None = None,
) -> str:
    query = sanitize_query(query)
    if not query:
        return fail()
    count = max(API_MIN_RESULTS, min(int(max_results), API_MAX_RESULTS))
    data = x_get(
        SEARCH_URL,
        token,
        {
            "query": query,
            "max_results": str(count),
            "tweet.fields": "created_at,author_id",
            "expansions": "author_id",
            "user.fields": "username",
        },
        http,
    )
    if not data or data.get("errors") or data.get("title") or data.get("status") in (400, 401, 403, 429):
        return fail()
    compact = compact_posts(data, query=query, limit=count)
    return json.dumps(compact, ensure_ascii=False, separators=(",", ":"))


def allow_call(chat_id: str, limit: int, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    stamp, count = _CALLS.get(chat_id, (now, 0))
    if now - stamp > 120:
        count = 0
        stamp = now
    if count >= limit:
        _CALLS[chat_id] = (stamp, count)
        return False
    _CALLS[chat_id] = (stamp, count + 1)
    return True


class Tools:
    class Valves(BaseModel):
        X_BEARER_TOKEN: str = Field(default="", description="X API Bearer Token. Not committed.")
        MAX_CALLS_PER_TURN: int = Field(default=3, ge=1, le=5)
        MAX_RESULTS: int = Field(default=10, ge=10, le=20)

    def __init__(self) -> None:
        self.valves = self.Valves()

    def _token(self) -> str:
        valve = (self.valves.X_BEARER_TOKEN or "").strip()
        if valve:
            return valve
        return (
            os.environ.get("X_BEARER_TOKEN")
            or os.environ.get("X_API_BEARER")
            or os.environ.get("TWITTER_BEARER_TOKEN")
            or ""
        ).strip()

    def search_x_posts(
        self,
        query: str,
        __metadata__: dict | None = None,
    ) -> str:
        """Must-use tool for posts on X (Twitter) from the last 7 days.

        Call this instead of inventing tweets or x.com/status URLs. query:
        keyword or from:handle. Returns compact JSON: author, time, short
        text, x.com URL. No embed UI, no like/view counts. If ok is false,
        say X 接口不可用 and do not invent posts.
        """
        # X_RECENT_SEARCH_V1
        query = sanitize_query(query)
        if not query:
            return fail()
        token = self._token()
        if not token:
            return fail()
        chat_id = "anon"
        if isinstance(__metadata__, dict):
            chat_id = str(__metadata__.get("chat_id") or __metadata__.get("chatId") or "anon")
        if not allow_call(chat_id, int(self.valves.MAX_CALLS_PER_TURN)):
            return fail("本轮 X 查询已达上限", capped=True)
        return lookup_posts(token, query, max_results=int(self.valves.MAX_RESULTS))
