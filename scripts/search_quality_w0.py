"""W0 helpers: temporary native + max_tool_calls=3, message-scoped.

Live Filter/Pipe are patched only while the probe runs, then restored from
saved originals. Unmarked production chats keep counted Exa.
"""

from __future__ import annotations

import hashlib
from typing import Any

FILTER_MARKER = "W0_MAX_TOOL_CALLS_PROBE_V1"
PIPE_MARKER = "W0_MAX_TOOL_CALLS_PIPE_V1"
MAX_TOOL_CALLS = 3

FILTER_RETURN_ANCHOR = """            if pipe_meta.get("stop_server_tools_when"):
                pipe_meta.pop("stop_server_tools_when", None)

        return body
"""

FILTER_RETURN_PATCH = FILTER_RETURN_ANCHOR.replace(
    "        return body\n",
    f'''        # {FILTER_MARKER}: unmarked traffic stays counted Exa.
        _w0_blob = ""
        _msgs = body.get("messages")
        if isinstance(_msgs, list):
            for _m in _msgs:
                if not isinstance(_m, dict):
                    continue
                _c = _m.get("content")
                if isinstance(_c, str):
                    _w0_blob += _c
                elif isinstance(_c, list):
                    for _p in _c:
                        if isinstance(_p, dict) and isinstance(_p.get("text"), str):
                            _w0_blob += _p["text"]
        if "{FILTER_MARKER}" in _w0_blob and self._uses_counted_search_engine(body, __model__):
            if isinstance(server_tools.get("web_search"), dict):
                server_tools["web_search"]["engine"] = "native"
            if isinstance(server_tools.get("web_fetch"), dict):
                server_tools["web_fetch"]["engine"] = "native"
            body["max_tool_calls"] = {MAX_TOOL_CALLS}
            pipe_meta["max_tool_calls"] = {MAX_TOOL_CALLS}
            pipe_meta.pop("stop_server_tools_when", None)
            pipe_meta["w0_probe"] = {{
                "r": 1,
                "max_tool_calls": {MAX_TOOL_CALLS},
                "engine": "native",
            }}
        return body
''',
)

PIPE_STOP_ANCHOR = """    stop_when = pipe_meta.get("stop_server_tools_when")
    if isinstance(stop_when, list) and stop_when:
        responses_body.stop_server_tools_when = stop_when
"""

PIPE_STOP_PATCH = PIPE_STOP_ANCHOR + f"""    # {PIPE_MARKER}
    _mtc = pipe_meta.get("max_tool_calls")
    if isinstance(_mtc, int) and not isinstance(_mtc, bool) and _mtc > 0:
        responses_body.max_tool_calls = _mtc
"""

PIPE_CALL_ANCHOR = (
    "        _apply_server_tools_metadata(responses_body, __metadata__, logger=self.logger)\n"
)

PIPE_CALL_PATCH = PIPE_CALL_ANCHOR + f'''        # {PIPE_MARKER}
        if __event_emitter__:
            try:
                _pm = (__metadata__ or {{}}).get(_PIPE_METADATA_KEY) or {{}}
                _st = _pm.get("server_tools") if isinstance(_pm, dict) else {{}}
                _ws = _st.get("web_search") if isinstance(_st, dict) else {{}}
                _eng = _ws.get("engine") if isinstance(_ws, dict) else None
                _mtc = getattr(responses_body, "max_tool_calls", None)
                _stop = getattr(responses_body, "stop_server_tools_when", None)
                await __event_emitter__({{
                    "type": "status",
                    "data": {{
                        "description": (
                            "{PIPE_MARKER} "
                            f"eng={{_eng}} mtc={{_mtc}} stop={{bool(_stop)}} "
                            f"probe={{_pm.get('w0_probe')}}"
                        ),
                        "done": False,
                    }},
                }})
            except Exception:
                pass
'''


def sha12(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _replace_once(src: str, anchor: str, patch: str, *, what: str) -> str:
    count = src.count(anchor)
    if count != 1:
        raise RuntimeError(f"{what} anchor count={count}, want 1")
    return src.replace(anchor, patch, 1)


def inject_filter(src: str) -> str:
    if FILTER_MARKER in src:
        return src
    return _replace_once(src, FILTER_RETURN_ANCHOR, FILTER_RETURN_PATCH, what="filter")


def inject_pipe(src: str) -> str:
    if PIPE_MARKER in src:
        return src
    src = _replace_once(src, PIPE_STOP_ANCHOR, PIPE_STOP_PATCH, what="pipe stop")
    return _replace_once(src, PIPE_CALL_ANCHOR, PIPE_CALL_PATCH, what="pipe call")


def load_filter_class(src: str) -> type:
    namespace: dict[str, Any] = {"__name__": "w0_filter_probe"}
    exec(compile(src, "<w0_filter>", "exec"), namespace)
    cls = namespace.get("Filter")
    if cls is None:
        raise RuntimeError("patched filter missing Filter")
    return cls
