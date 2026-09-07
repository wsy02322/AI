#!/usr/bin/env python3
"""W6 live probe: does max_tool_calls=3 stop Astra Pro native inner loop?

Reuses the W0 message-scoped inject. Unmarked production OpenAI stays Exa.
Always restores Filter/Pipe. Does not flip production OpenAI to native.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_search_quality_w0 import (
    ABORT_INPUT_TOKENS,
    ABORT_SEARCHES,
    ABORT_SINGLE_USD,
    CONTINUE_PROMPT,
    SEARCH_PROMPT,
    _should_abort,
    _summarize,
    apply_probe,
    restore,
)
from search_quality_w0 import MAX_TOOL_CALLS, sha12
from stack_contract import PIPE, TEXT_WEB_SEARCH_FILTER
from text_web_search_ops import get_function, headers, signin, snapshot_search_state

OUT = Path(os.environ.get("SEARCH_QUALITY_W6_OUT", "/opt/cursor/artifacts/search-quality-w6.json"))
BACKUP_DIR = Path(os.environ.get("SEARCH_QUALITY_W6_BACKUP", "/tmp/search-quality-w6"))
BUDGET_USD = float(os.environ.get("SEARCH_QUALITY_W6_BUDGET", "10"))
CHAT_TIMEOUT = int(os.environ.get("SEARCH_QUALITY_W6_TIMEOUT", "300"))
ASTRA_PRO = f"{PIPE}.openai.gpt-6-astra-pro"


def _chat(h: dict[str, str], messages: list[dict[str, str]]) -> dict[str, Any]:
    from text_web_search_ops import chat_with_optional_search

    return chat_with_optional_search(
        h,
        ASTRA_PRO,
        messages,
        enable_search=True,
        timeout=CHAT_TIMEOUT,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path
    except OSError as exc:
        fallback = Path("/tmp/search-quality-w6.json")
        fallback.write_text(text, encoding="utf-8")
        print(f"WARN write {path} failed ({exc}); wrote {fallback}")
        return fallback


def run_probe(h: dict[str, str]) -> dict[str, Any]:
    errors: list[str] = []
    spent = 0.0
    print(f"\n=== astra_pro {ASTRA_PRO.rsplit('.', 1)[-1]} ===")
    first = _chat(h, [{"role": "user", "content": SEARCH_PROMPT}])
    first_row = _summarize(first)
    spent += float(first_row.get("cost_usd") or 0)
    first_row["spent_usd"] = round(spent, 6)
    print(
        f"astra_pro search status={first_row['status']} "
        f"verdict={first_row['verdict']} "
        f"web_search_requests={first_row['web_search_requests']} "
        f"tool_calls_executed={first_row['tool_calls_executed']} "
        f"input_tokens={first_row['input_tokens']} "
        f"cost={first_row['cost_usd']}"
    )
    if first_row["probe_stamps"]:
        print("stamp:", first_row["probe_stamps"][0][:240])
    else:
        errors.append("astra_pro missing pipe stamp")
    abort_reason = _should_abort(first_row, spent)
    cont_row: dict[str, Any] | None = None
    if abort_reason:
        errors.append(f"astra_pro abort: {abort_reason}")
    elif first_row["verdict"] == "uncapped":
        errors.append(
            "astra_pro uncapped on first turn "
            f"searches={first_row['web_search_requests']} executed={first_row['tool_calls_executed']}"
        )
    if not abort_reason:
        cont = _chat(
            h,
            [
                {"role": "user", "content": SEARCH_PROMPT},
                {"role": "assistant", "content": first.get("text") or "已根据检索整理。"},
                {"role": "user", "content": CONTINUE_PROMPT},
            ],
        )
        cont_row = _summarize(cont)
        spent += float(cont_row.get("cost_usd") or 0)
        cont_row["spent_usd"] = round(spent, 6)
        print(
            f"astra_pro continue status={cont_row['status']} "
            f"verdict={cont_row['verdict']} "
            f"web_search_requests={cont_row['web_search_requests']} "
            f"input_tokens={cont_row['input_tokens']} "
            f"cost={cont_row['cost_usd']}"
        )
        abort_reason = _should_abort(cont_row, spent)
        if abort_reason:
            errors.append(f"astra_pro continue abort: {abort_reason}")
        elif cont_row["verdict"] == "uncapped":
            errors.append(
                "astra_pro uncapped on continue "
                f"searches={cont_row['web_search_requests']} executed={cont_row['tool_calls_executed']}"
            )

    live = [first_row] + ([cont_row] if cont_row else [])
    if any(row.get("verdict") == "uncapped" for row in live):
        gate = "fail"
    elif any(row.get("verdict") == "capped" for row in live) and first_row.get("probe_stamps"):
        gate = "pass"
    elif any(row.get("verdict") == "maybe_capped" for row in live):
        gate = "weak"
    else:
        gate = "inconclusive"
    allowed = gate == "pass" and not abort_reason and not errors
    blocker = None
    if not allowed:
        if abort_reason:
            blocker = abort_reason
        elif errors:
            blocker = errors[0]
        else:
            blocker = f"Astra Pro gate={gate}; production OpenAI stays Exa"
    return {
        "budget_usd": BUDGET_USD,
        "spent_usd": round(spent, 6),
        "abort_reason": abort_reason,
        "max_tool_calls": MAX_TOOL_CALLS,
        "abort_single_usd": ABORT_SINGLE_USD,
        "abort_searches": ABORT_SEARCHES,
        "abort_input_tokens": ABORT_INPUT_TOKENS,
        "gate": gate,
        "w6_openai_native_allowed": allowed,
        "w6_blocker": blocker,
        "rows": {
            "astra_pro.search": first_row,
            **({"astra_pro.continue": cont_row} if cont_row else {}),
        },
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--revert", action="store_true")
    args = parser.parse_args()
    if not (args.apply or args.run or args.revert):
        args.apply = args.run = args.revert = True

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    h = headers(signin())
    filter_status, filter_obj = get_function(h, TEXT_WEB_SEARCH_FILTER)
    pipe_status, pipe_obj = get_function(h, PIPE)
    if filter_status != 200 or not filter_obj or pipe_status != 200 or not pipe_obj:
        raise SystemExit("missing Filter or Pipe")
    original_filter = filter_obj.get("content") or ""
    original_pipe = pipe_obj.get("content") or ""
    payload: dict[str, Any] = {
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": ASTRA_PRO,
        "original": {
            "filter_sha12": sha12(original_filter),
            "pipe_sha12": sha12(original_pipe),
            "snapshot": snapshot_search_state(h),
        },
    }
    restore_info: dict[str, Any] | None = None
    try:
        (BACKUP_DIR / "w6-filter-original.py").write_text(original_filter, encoding="utf-8")
        (BACKUP_DIR / "w6-pipe-original.py").write_text(original_pipe, encoding="utf-8")
    except OSError as exc:
        print(f"WARN backup write failed ({exc}); restore will use in-memory originals")
    code = 0
    try:
        if args.apply:
            apply_probe(h, original_filter, pipe_obj, original_pipe)
        if args.run:
            payload["probe"] = run_probe(h)
    finally:
        if args.revert or args.run or args.apply:
            try:
                restore_info = restore(h, original_filter, pipe_obj, original_pipe)
            except Exception as exc:
                print(f"RESTORE FAILED: {exc}")
                restore_info = {"error": str(exc)}
                code = 1
    payload["restore"] = restore_info
    payload["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    written = _write_json(OUT, payload)
    print(f"wrote {written}")
    if restore_info and not restore_info.get("filter_matches"):
        print("ERR filter did not restore to original")
        code = 1
    if restore_info and not restore_info.get("pipe_matches"):
        print("ERR pipe did not restore to original")
        code = 1
    probe = payload.get("probe") or {}
    if probe and not probe.get("w6_openai_native_allowed"):
        print(f"W6 not allowed: {probe.get('w6_blocker')}")
        code = 1
    elif probe.get("w6_openai_native_allowed"):
        print("W6 Astra Pro hard-cap gate passed; production still Exa until apply")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
