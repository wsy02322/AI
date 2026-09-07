"""
title: Web Search
author: micropigeon
id: openrouter_text_web_search
description: OpenRouter web search and fetch for selected text models only.
version: 1.0.0
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

TEXT_WEB_SEARCH_FILTER_V1 = "TEXT_WEB_SEARCH_FILTER_V1"
TEXT_WEB_SEARCH_OPENAI_NATIVE_V1 = "TEXT_WEB_SEARCH_OPENAI_NATIVE_V1"
TEXT_WEB_SEARCH_OPENAI_MAX_TOOL_CALLS_V1 = "TEXT_WEB_SEARCH_OPENAI_MAX_TOOL_CALLS_V1"
TEXT_WEB_SEARCH_XAI_NATIVE_V1 = "TEXT_WEB_SEARCH_XAI_NATIVE_V1"
TEXT_WEB_SEARCH_GOOGLE_NATIVE_V1 = "TEXT_WEB_SEARCH_GOOGLE_NATIVE_V1"
TEXT_WEB_SEARCH_DENY_CLASS_V1 = "TEXT_WEB_SEARCH_DENY_CLASS_V1"
OPENAI_MAX_TOOL_CALLS = 3

# Native search ignores max_uses except Anthropic. OpenAI is native (W6) with
# max_tool_calls=3; stop_server_tools_when is popped so it cannot override the
# cap (W6 Astra Pro probe). Google native (W2). xAI native (W3: web + X).
# Not a model-id allowlist. Image ids are denied before this runs.
OPENAI_NATIVE_MARKERS = (
    "openai.",
    "openai/",
)
COUNTED_EXA_MARKERS = OPENAI_NATIVE_MARKERS
GOOGLE_NATIVE_MARKERS = (
    "google.",
    "google/",
)
XAI_NATIVE_MARKERS = (
    "x-ai.",
    "x-ai/",
    "xai.",
    "xai/",
)
UNMETERED_NATIVE_MARKERS = GOOGLE_NATIVE_MARKERS + XAI_NATIVE_MARKERS

DENY_MARKERS = (
    "sonar",
    "perplexity/",
    "perplexity.",
    "-image",
    "gpt-image",
    "flux.",
    "seedream",
    "recraft/",
    "riverflow",
    "mai-image",
    "grok-imagine",
    "imagen",
    "banana",
    "sora",
    "veo",
    "kling",
    "hailuo",
    "seedance",
    "happyhorse",
    "wan-2",
    "video_generation",
)


class Filter:
    toggle = True

    class Valves(BaseModel):
        priority: int = Field(default=0, description="Run before image/Sonar tool guards.")
        WEB_SEARCH_ENGINE: str = Field(default="auto")
        WEB_SEARCH_MAX_RESULTS: int = Field(default=5, ge=1, le=25)
        WEB_SEARCH_MAX_USES: int = Field(default=3, ge=0)
        WEB_SEARCH_MAX_TOTAL_RESULTS: int = Field(default=15, ge=0)
        WEB_SEARCH_CONTEXT_SIZE: str = Field(default="medium")
        WEB_FETCH_ENGINE: str = Field(default="auto")
        WEB_FETCH_MAX_USES: int = Field(default=5, ge=0)
        WEB_FETCH_MAX_CONTENT_TOKENS: int = Field(default=12000, ge=0)
        SERVER_TOOLS_STEP_COUNT: int = Field(default=8, ge=1)
        SERVER_TOOLS_MAX_COST_USD: float = Field(default=0.05, ge=0)

    class UserValves(BaseModel):
        WEB_SEARCH: bool = Field(default=True, description="Let the model search the web.")
        WEB_FETCH: bool = Field(default=True, description="Let the model read full pages.")

    def __init__(self) -> None:
        self.valves = self.Valves()
        self.toggle = True

    @staticmethod
    def _refs(body: dict[str, Any], __model__: dict[str, Any] | None) -> str:
        parts = [str(body.get("model") or "")]
        if isinstance(__model__, dict):
            parts.append(str(__model__.get("id") or ""))
            parts.append(str(__model__.get("name") or ""))
            parts.append(str(__model__.get("base_model_id") or ""))
            info = __model__.get("info") if isinstance(__model__.get("info"), dict) else {}
            parts.append(str(info.get("id") or ""))
            parts.append(str(info.get("base_model_id") or ""))
        return " ".join(parts).lower()

    @staticmethod
    def _caps(body: dict[str, Any], __model__: dict[str, Any] | None, __metadata__: dict[str, Any] | None) -> dict[str, Any]:
        out: dict[str, Any] = {}
        buckets: list[Any] = []
        if isinstance(__model__, dict):
            buckets.append(__model__.get("meta") or {})
            info = __model__.get("info") if isinstance(__model__.get("info"), dict) else {}
            buckets.append(info.get("meta") or {})
        if isinstance(__metadata__, dict):
            buckets.append(__metadata__.get("openrouter_pipe") or {})
        for bucket in buckets:
            if not isinstance(bucket, dict):
                continue
            caps = bucket.get("capabilities")
            if isinstance(caps, dict):
                out.update(caps)
        return out

    def _is_denied(self, body: dict[str, Any], __model__: dict[str, Any] | None, __metadata__: dict[str, Any] | None) -> bool:
        lowered = self._refs(body, __model__)
        if any(marker in lowered for marker in DENY_MARKERS):
            return True
        caps = self._caps(body, __model__, __metadata__)
        return bool(caps.get("image_output") or caps.get("video_generation"))

    def _is_xai(self, body: dict[str, Any], __model__: dict[str, Any] | None) -> bool:
        refs = self._refs(body, __model__)
        return any(marker in refs for marker in XAI_NATIVE_MARKERS)

    def _is_google(self, body: dict[str, Any], __model__: dict[str, Any] | None) -> bool:
        refs = self._refs(body, __model__)
        return any(marker in refs for marker in GOOGLE_NATIVE_MARKERS)

    def _is_openai(self, body: dict[str, Any], __model__: dict[str, Any] | None) -> bool:
        refs = self._refs(body, __model__)
        return any(marker in refs for marker in OPENAI_NATIVE_MARKERS)

    def _uses_counted_search_engine(self, body: dict[str, Any], __model__: dict[str, Any] | None) -> bool:
        """OpenAI class (W0 probe still keys off this). Production engine is native."""
        if self._is_xai(body, __model__) or self._is_google(body, __model__):
            return False
        return self._is_openai(body, __model__)

    def _tool_engine(self, body: dict[str, Any], __model__: dict[str, Any] | None, default: str) -> str:
        # TEXT_WEB_SEARCH_OPENAI_NATIVE_V1 / XAI / GOOGLE
        if self._is_xai(body, __model__) or self._is_google(body, __model__) or self._is_openai(body, __model__):
            return "native"
        return default

    def _user_valves(self, __user__: dict[str, Any] | None) -> UserValves:
        raw = (__user__ or {}).get("valves") if isinstance(__user__, dict) else None
        if isinstance(raw, dict):
            return self.UserValves(**raw)
        if isinstance(raw, self.UserValves):
            return raw
        return self.UserValves()

    def inlet(
        self,
        body: dict[str, Any],
        __user__: Optional[dict] = None,
        __model__: Optional[dict] = None,
        __metadata__: Optional[dict] = None,
    ) -> dict[str, Any]:
        if not isinstance(body, dict):
            return body
        # TEXT_WEB_SEARCH_DENY_CLASS_V1: no model-id allowlist. Attachment is the
        # picker gate; deny keeps Sonar / image / video from receiving tools.
        if self._is_denied(body, __model__, __metadata__):
            return body

        user_valves = self._user_valves(__user__)
        if not isinstance(__metadata__, dict):
            __metadata__ = {}
        pipe_meta = __metadata__.get("openrouter_pipe")
        if not isinstance(pipe_meta, dict):
            pipe_meta = {}
            __metadata__["openrouter_pipe"] = pipe_meta
        server_tools = pipe_meta.get("server_tools")
        if not isinstance(server_tools, dict):
            server_tools = {}
            pipe_meta["server_tools"] = server_tools

        if user_valves.WEB_SEARCH:
            search: dict[str, Any] = {
                "engine": self._tool_engine(body, __model__, self.valves.WEB_SEARCH_ENGINE),
                "max_results": self.valves.WEB_SEARCH_MAX_RESULTS,
                "search_context_size": self.valves.WEB_SEARCH_CONTEXT_SIZE,
            }
            if self.valves.WEB_SEARCH_MAX_USES > 0:
                search["max_uses"] = self.valves.WEB_SEARCH_MAX_USES
            if self.valves.WEB_SEARCH_MAX_TOTAL_RESULTS > 0:
                search["max_total_results"] = self.valves.WEB_SEARCH_MAX_TOTAL_RESULTS
            server_tools["web_search"] = search
        else:
            server_tools.pop("web_search", None)

        if user_valves.WEB_FETCH:
            fetch: dict[str, Any] = {
                "engine": self._tool_engine(body, __model__, self.valves.WEB_FETCH_ENGINE)
            }
            if self.valves.WEB_FETCH_MAX_USES > 0:
                fetch["max_uses"] = self.valves.WEB_FETCH_MAX_USES
            if self.valves.WEB_FETCH_MAX_CONTENT_TOKENS > 0:
                fetch["max_content_tokens"] = self.valves.WEB_FETCH_MAX_CONTENT_TOKENS
            server_tools["web_fetch"] = fetch
        else:
            server_tools.pop("web_fetch", None)

        if server_tools.get("web_search") or server_tools.get("web_fetch"):
            pipe_meta["stop_server_tools_when"] = [
                {"type": "step_count_is", "step_count": self.valves.SERVER_TOOLS_STEP_COUNT},
                {"type": "max_cost", "max_cost_in_dollars": self.valves.SERVER_TOOLS_MAX_COST_USD},
            ]
            features = body.get("features")
            if not isinstance(features, dict):
                features = {}
                body["features"] = features
            features["web_search"] = False
            # TEXT_WEB_SEARCH_OPENAI_MAX_TOOL_CALLS_V1: stop_when overrides
            # max_tool_calls on OpenRouter. W6 Astra Pro probe only capped
            # after popping stop and sending mtc=3.
            if self._is_openai(body, __model__):
                body["max_tool_calls"] = OPENAI_MAX_TOOL_CALLS
                pipe_meta["max_tool_calls"] = OPENAI_MAX_TOOL_CALLS
                pipe_meta.pop("stop_server_tools_when", None)
        elif not server_tools:
            pipe_meta.pop("server_tools", None)
            if pipe_meta.get("stop_server_tools_when"):
                pipe_meta.pop("stop_server_tools_when", None)

        return body
