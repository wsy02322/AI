#!/usr/bin/env python3
"""F1: temporary Filter probe + Astra attach. Revert after reading stamps.

Injects Astra suffixes and a body-metadata filter_probe stamp into the live
thin Filter without leaving that content in the repo source. Does not change
Pipe valves or Banner.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import (
    ASTRA_PUBLIC_MODEL_IDS,
    PIPE,
    TEXT_WEB_SEARCH_FILTER,
    TEXT_WEB_SEARCH_MODEL_IDS,
)
from text_web_search_ops import (
    attach_models,
    chat_with_optional_search,
    event_actions,
    filter_source,
    headers,
    set_active,
    set_global,
    set_valves,
    signin,
    upsert_filter,
    web_search_requests,
)

PROBE_MARKER = "ASTRA_SEARCH_FILTER_PROBE_V1"
SOL_ID = f"{PIPE}.openai.gpt-5.6-sol"
ASTRA_ID = f"{PIPE}.openai.gpt-6-astra"
ASTRA_SUFFIXES = (
    '    "openai.gpt-6-astra-pro",\n',
    '    "openai.gpt-6-astra",\n',
)

INLET_DENY = """        if self._is_denied(body, __model__, __metadata__) or not self._is_allowlisted(body, __model__):
            return body
"""

INLET_PROBE = f"""        # {PROBE_MARKER}
        _denied = self._is_denied(body, __model__, __metadata__)
        _allow = self._is_allowlisted(body, __model__)
        _meta_is_dict = isinstance(__metadata__, dict)
        _refs = self._refs(body, __model__)
        _body_meta = body.get("__metadata__")
        if not isinstance(_body_meta, dict):
            _body_meta = {{}}
            body["__metadata__"] = _body_meta
        _pipe_on_body = _body_meta.get("openrouter_pipe")
        if not isinstance(_pipe_on_body, dict):
            _pipe_on_body = {{}}
            _body_meta["openrouter_pipe"] = _pipe_on_body
        _pipe_on_body["filter_probe"] = {{
            "r": 1,
            "a": int(bool(_allow)),
            "d": int(bool(_denied)),
            "m": int(_meta_is_dict),
            "refs": _refs[:240],
        }}
        if _meta_is_dict:
            _pm = __metadata__.get("openrouter_pipe")
            if not isinstance(_pm, dict):
                _pm = {{}}
                __metadata__["openrouter_pipe"] = _pm
            _pm["filter_probe"] = dict(_pipe_on_body["filter_probe"])
        if _denied or not _allow:
            return body
"""

SEARCH_PROMPT = (
    "You must call web_search. Do not answer from memory. "
    "What official product news did OpenAI announce this week? "
    "Cite at least one live source URL from the search results."
)


def inject_probe(src: str) -> str:
    if PROBE_MARKER in src:
        return src
    if "openai.gpt-6-astra" not in src:
        needle = '    "google.gemini-3.8-flash",\n'
        if needle not in src:
            raise SystemExit("allowlist needle missing")
        src = src.replace(needle, needle + "".join(ASTRA_SUFFIXES), 1)
    if INLET_DENY not in src:
        raise SystemExit("inlet deny block missing")
    return src.replace(INLET_DENY, INLET_PROBE, 1)


def upsert_probed_filter(h: dict[str, str]) -> None:
    probed = inject_probe(filter_source())
    if PROBE_MARKER not in probed or "openai.gpt-6-astra" not in probed:
        raise SystemExit("probe inject failed")
    upsert_filter(h, probed)
    set_global(h, TEXT_WEB_SEARCH_FILTER, False)
    set_valves(h)
    set_active(h, TEXT_WEB_SEARCH_FILTER, False)
    set_active(h, TEXT_WEB_SEARCH_FILTER, True)
    print(f"upsert probed filter marker={PROBE_MARKER}")


def restore_clean_filter(h: dict[str, str]) -> None:
    upsert_filter(h)
    set_global(h, TEXT_WEB_SEARCH_FILTER, False)
    set_valves(h)
    set_active(h, TEXT_WEB_SEARCH_FILTER, False)
    set_active(h, TEXT_WEB_SEARCH_FILTER, True)
    print("restored clean filter from repo source")


def attach_with_astra(h: dict[str, str], *, include_astra: bool) -> None:
    wanted = list(TEXT_WEB_SEARCH_MODEL_IDS)
    if include_astra:
        wanted.extend(ASTRA_PUBLIC_MODEL_IDS)
    attach_models(h, wanted, default_on=True, inspect_extra=list(ASTRA_PUBLIC_MODEL_IDS))


def run_probe_chats(h: dict[str, str]) -> int:
    errors = 0
    for model_id, label in ((SOL_ID, "sol"), (ASTRA_ID, "astra")):
        result = chat_with_optional_search(
            h,
            model_id,
            [{"role": "user", "content": SEARCH_PROMPT}],
            enable_search=True,
        )
        searches = web_search_requests(result["usage"])
        tokens = result["usage"].get("prompt_tokens") or result["usage"].get("input_tokens")
        print(f"\n=== {label} status={result['status']} web_search_requests={searches} tokens={tokens} ===")
        probes = [
            item.get("description")
            for item in event_actions(result["events"])
            if isinstance(item.get("description"), str) and PROBE_MARKER in item["description"]
        ]
        if probes:
            for desc in probes:
                print(desc)
        else:
            print("NO_FILTER_PROBE_IN_EVENTS")
            errors += 1
        print("text:", (result["text"] or result["error"] or "")[:240])
    return 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="upsert probed filter and attach Astra")
    parser.add_argument("--run", action="store_true", help="Sol + Astra search and print stamps")
    parser.add_argument("--revert", action="store_true", help="restore clean filter and strip Astra")
    args = parser.parse_args()
    if not (args.apply or args.run or args.revert):
        raise SystemExit("pass --apply and/or --run and/or --revert")
    h = headers(signin())
    if args.apply:
        upsert_probed_filter(h)
        attach_with_astra(h, include_astra=True)
    code = 0
    if args.run:
        code = run_probe_chats(h)
    if args.revert:
        restore_clean_filter(h)
        attach_with_astra(h, include_astra=False)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
