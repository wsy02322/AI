#!/usr/bin/env python3
"""W0 live probe: does max_tool_calls=3 stop OpenAI/Google/xAI native inner loops?

Temporarily patches Filter (message-scoped) and Pipe (copy max_tool_calls),
runs Flash / Grok / Sol, then restores saved originals. Budget ≤ $10.
Does not change valves / API_KEY / Banner / catalog.
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
from search_quality_w0 import (
    FILTER_MARKER,
    MAX_TOOL_CALLS,
    PIPE_MARKER,
    inject_filter,
    inject_pipe,
    sha12,
)
from stack_contract import PIPE, TEXT_WEB_SEARCH_FILTER
from text_web_search_ops import (
    chat_with_optional_search,
    event_actions,
    get_function,
    headers,
    search_called,
    signin,
    snapshot_search_state,
    tool_calls_executed,
    tool_calls_requested,
    upsert_filter,
    usage_cost_usd,
    web_search_requests,
)

OUT = Path(os.environ.get("SEARCH_QUALITY_W0_OUT", "/opt/cursor/artifacts/search-quality-w0.json"))
BACKUP_DIR = Path(os.environ.get("SEARCH_QUALITY_W0_BACKUP", "/tmp/search-quality-w0"))
BUDGET_USD = float(os.environ.get("SEARCH_QUALITY_W0_BUDGET", "10"))
ABORT_SINGLE_USD = float(os.environ.get("SEARCH_QUALITY_W0_ABORT_SINGLE", "5"))
ABORT_SEARCHES = int(os.environ.get("SEARCH_QUALITY_W0_ABORT_SEARCHES", "20"))
ABORT_INPUT_TOKENS = int(os.environ.get("SEARCH_QUALITY_W0_ABORT_TOKENS", "400000"))
CHAT_TIMEOUT = int(os.environ.get("SEARCH_QUALITY_W0_TIMEOUT", "180"))
# OpenRouter may execute in-flight tool calls after the budget fires (3 → 4).
CAP_SLACK = int(os.environ.get("SEARCH_QUALITY_W0_CAP_SLACK", "1"))

FLASH = f"{PIPE}.google.gemini-3.8-flash"
GROK = f"{PIPE}.x-ai.grok-4.6"
SOL = f"{PIPE}.openai.gpt-5.6-sol"
MODELS = (
    ("flash", FLASH),
    ("grok", GROK),
    ("sol", SOL),
)

SEARCH_PROMPT = (
    f"{FILTER_MARKER}\n"
    "You must call web_search. Do not answer from memory. Do not call web_fetch.\n"
    "Search these 10 independent topics separately — one distinct web_search query "
    "per topic, never merge them. After each search write one sentence. Do not write "
    "a final summary until all 10 have been searched. If you think you are finished, "
    "continue until all 10 have their own search. 你继续.\n"
    "Topics:\n"
    "1) Today's Shanghai Composite close\n"
    "2) Latest FOMC statement date\n"
    "3) SpaceX Starship most recent test\n"
    "4) OpenAI product news announced this week\n"
    "5) Amap driving API traffic field names\n"
    "6) What Grok posted on X about search this week\n"
    "7) NVIDIA most recent earnings headline number\n"
    "8) Bitcoin price USD right now\n"
    "9) Current northwest Pacific typhoon name\n"
    "10) Today's top Hacker News story title\n"
)

CONTINUE_PROMPT = (
    f"{FILTER_MARKER}\n"
    "你继续. Keep calling web_search for any of the 10 topics you have not searched yet. "
    "Do not call web_fetch. One distinct query per remaining topic."
)


def _short(model_id: str) -> str:
    prefix = PIPE + "."
    return model_id[len(prefix) :] if model_id.startswith(prefix) else model_id


def _cost(usage: dict[str, Any] | None) -> float:
    value = usage_cost_usd(usage)
    return float(value) if value is not None else 0.0


def _input_tokens(usage: dict[str, Any] | None) -> int:
    usage = usage or {}
    for key in ("prompt_tokens", "input_tokens"):
        value = usage.get(key)
        if isinstance(value, (int, float)):
            return int(value)
    return 0


def _probe_stamps(events: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for item in event_actions(events):
        desc = item.get("description")
        if isinstance(desc, str) and PIPE_MARKER in desc:
            out.append(desc)
    return out


def _verdict(status: int, searches: int, executed: int) -> str:
    if status != 200:
        return "error"
    steps = max(searches, executed)
    ceiling = MAX_TOOL_CALLS + CAP_SLACK
    if steps >= 1 and MAX_TOOL_CALLS <= steps <= ceiling:
        return "capped"
    if 1 <= steps < MAX_TOOL_CALLS:
        return "maybe_capped"
    if steps > ceiling:
        return "uncapped"
    return "no_search"


def _summarize(result: dict[str, Any]) -> dict[str, Any]:
    usage = result.get("usage") or {}
    searches = web_search_requests(usage)
    executed = tool_calls_executed(usage)
    requested = tool_calls_requested(usage)
    cost = usage_cost_usd(usage)
    stamps = _probe_stamps(result.get("events") or [])
    details = usage.get("server_tool_use_details") or usage.get("server_tool_use") or {}
    return {
        "status": result.get("status"),
        "verdict": _verdict(int(result.get("status") or 0), searches, executed),
        "web_search_requests": searches,
        "tool_calls_executed": executed,
        "tool_calls_requested": requested,
        "search_called": search_called(result),
        "cost_usd": cost,
        "cost_details": usage.get("cost_details") if isinstance(usage.get("cost_details"), dict) else None,
        "input_tokens": _input_tokens(usage),
        "output_tokens": usage.get("completion_tokens") or usage.get("output_tokens"),
        "turn_count": usage.get("turn_count"),
        "server_tool_use_details": details if isinstance(details, dict) else {},
        "usage_keys": sorted(str(key) for key in usage.keys()),
        "probe_stamps": stamps,
        "text_chars": len(result.get("text") or ""),
        "text_head": (result.get("text") or "")[:320],
        "error": (result.get("error") or "")[:400],
    }


def _should_abort(row: dict[str, Any], spent: float) -> str | None:
    cost = float(row.get("cost_usd") or 0)
    searches = int(row.get("web_search_requests") or 0)
    tokens = int(row.get("input_tokens") or 0)
    if cost >= ABORT_SINGLE_USD:
        return f"single cost ${cost:.3f} >= ${ABORT_SINGLE_USD}"
    if spent >= BUDGET_USD:
        return f"budget ${spent:.3f} >= ${BUDGET_USD}"
    if searches >= ABORT_SEARCHES:
        return f"web_search_requests={searches} >= {ABORT_SEARCHES}"
    if tokens >= ABORT_INPUT_TOKENS:
        return f"input_tokens={tokens} >= {ABORT_INPUT_TOKENS}"
    return None


def _upsert_pipe(h: dict[str, str], original: dict[str, Any], content: str) -> None:
    import requests
    from text_web_search_ops import OPENWEBUI_URL

    payload = {
        "id": PIPE,
        "name": original.get("name") or PIPE,
        "meta": original.get("meta") or {},
        "content": content,
    }
    response = requests.post(
        f"{OPENWEBUI_URL}/api/v1/functions/id/{PIPE}/update",
        headers=h,
        json=payload,
        timeout=180,
    )
    if response.status_code != 200:
        raise RuntimeError(f"update pipe: {response.status_code} {response.text[:400]}")


def _reload_filter(h: dict[str, str]) -> None:
    from text_web_search_ops import set_active, set_global

    set_global(h, TEXT_WEB_SEARCH_FILTER, False)
    set_active(h, TEXT_WEB_SEARCH_FILTER, False)
    set_active(h, TEXT_WEB_SEARCH_FILTER, True)


def restore(h: dict[str, str], filter_content: str, pipe_obj: dict[str, Any], pipe_content: str) -> dict[str, Any]:
    upsert_filter(h, filter_content)
    _reload_filter(h)
    _upsert_pipe(h, pipe_obj, pipe_content)
    _, live_filter = get_function(h, TEXT_WEB_SEARCH_FILTER)
    _, live_pipe = get_function(h, PIPE)
    live_fc = (live_filter or {}).get("content") or ""
    live_pc = (live_pipe or {}).get("content") or ""
    result = {
        "filter_sha12": sha12(live_fc),
        "pipe_sha12": sha12(live_pc),
        "filter_probe_gone": FILTER_MARKER not in live_fc,
        "pipe_probe_gone": PIPE_MARKER not in live_pc,
        "counted_exa": "TEXT_WEB_SEARCH_COUNTED_EXA_V1" in live_fc,
        "filter_matches": live_fc == filter_content,
        "pipe_matches": live_pc == pipe_content,
    }
    print(
        "restored "
        f"filter={result['filter_sha12']} probe_gone={result['filter_probe_gone']} "
        f"pipe={result['pipe_sha12']} probe_gone={result['pipe_probe_gone']}"
    )
    return result


def apply_probe(h: dict[str, str], filter_content: str, pipe_obj: dict[str, Any], pipe_content: str) -> None:
    probed_filter = inject_filter(filter_content)
    probed_pipe = inject_pipe(pipe_content)
    if FILTER_MARKER not in probed_filter or PIPE_MARKER not in probed_pipe:
        raise RuntimeError("probe inject failed")
    upsert_filter(h, probed_filter)
    _reload_filter(h)
    _upsert_pipe(h, pipe_obj, probed_pipe)
    print(f"applied probe filter={sha12(probed_filter)} pipe={sha12(probed_pipe)}")


def _chat(h: dict[str, str], model_id: str, messages: list[dict[str, str]]) -> dict[str, Any]:
    return chat_with_optional_search(
        h,
        model_id,
        messages,
        enable_search=True,
        timeout=CHAT_TIMEOUT,
    )


def run_probe(h: dict[str, str]) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    errors: list[str] = []
    abort_reason: str | None = None
    spent = 0.0
    for label, model_id in MODELS:
        if abort_reason:
            rows[f"{label}.search"] = {"skipped": True, "reason": abort_reason}
            continue
        print(f"\n=== {label} {_short(model_id)} ===")
        first = _chat(h, model_id, [{"role": "user", "content": SEARCH_PROMPT}])
        first_row = _summarize(first)
        spent += float(first_row.get("cost_usd") or 0)
        first_row["spent_usd"] = round(spent, 6)
        rows[f"{label}.search"] = first_row
        print(
            f"{label} search status={first_row['status']} "
            f"verdict={first_row['verdict']} "
            f"web_search_requests={first_row['web_search_requests']} "
            f"tool_calls_executed={first_row['tool_calls_executed']} "
            f"cost={first_row['cost_usd']} stamps={len(first_row['probe_stamps'])}"
        )
        if first_row["probe_stamps"]:
            print("stamp:", first_row["probe_stamps"][0][:240])
        else:
            errors.append(f"{label} missing pipe stamp")
        abort_reason = _should_abort(first_row, spent)
        if abort_reason:
            errors.append(f"{label} abort: {abort_reason}")
            continue
        if first_row["verdict"] == "uncapped":
            errors.append(
                f"{label} uncapped on first turn "
                f"searches={first_row['web_search_requests']} executed={first_row['tool_calls_executed']}"
            )
            # Keep measuring other families unless this already blew the budget.
        cont = _chat(
            h,
            model_id,
            [
                {"role": "user", "content": SEARCH_PROMPT},
                {"role": "assistant", "content": first.get("text") or "已根据检索整理。"},
                {"role": "user", "content": CONTINUE_PROMPT},
            ],
        )
        cont_row = _summarize(cont)
        spent += float(cont_row.get("cost_usd") or 0)
        cont_row["spent_usd"] = round(spent, 6)
        rows[f"{label}.continue"] = cont_row
        print(
            f"{label} continue status={cont_row['status']} "
            f"verdict={cont_row['verdict']} "
            f"web_search_requests={cont_row['web_search_requests']} "
            f"cost={cont_row['cost_usd']}"
        )
        abort_reason = _should_abort(cont_row, spent)
        if abort_reason:
            errors.append(f"{label} continue abort: {abort_reason}")
        elif cont_row["verdict"] == "uncapped":
            errors.append(
                f"{label} uncapped on continue "
                f"searches={cont_row['web_search_requests']} executed={cont_row['tool_calls_executed']}"
            )
    openai_rows = [rows.get("sol.search") or {}, rows.get("sol.continue") or {}]
    google_rows = [rows.get("flash.search") or {}, rows.get("flash.continue") or {}]
    xai_rows = [rows.get("grok.search") or {}, rows.get("grok.continue") or {}]

    def _family_gate(family_rows: list[dict[str, Any]]) -> str:
        live = [row for row in family_rows if row and not row.get("skipped")]
        if not live:
            return "skipped"
        if any(row.get("verdict") == "uncapped" for row in live):
            return "fail"
        if any(row.get("verdict") == "capped" for row in live):
            return "pass"
        if any(row.get("verdict") == "maybe_capped" for row in live):
            return "weak"
        return "inconclusive"

    gates = {
        "google_native_max_tool_calls": _family_gate(google_rows),
        "xai_native_max_tool_calls": _family_gate(xai_rows),
        "openai_native_max_tool_calls": _family_gate(openai_rows),
    }
    w6_blocker = None
    if gates["openai_native_max_tool_calls"] != "pass":
        w6_blocker = "Sol did not stay within max_tool_calls+1"
    else:
        w6_blocker = (
            "Sol capped, but the $19 spike was Astra Pro continue; "
            "Astra Pro was not probed. Grok continue already leaked to 11."
        )
    return {
        "budget_usd": BUDGET_USD,
        "spent_usd": round(spent, 6),
        "abort_reason": abort_reason,
        "max_tool_calls": MAX_TOOL_CALLS,
        "cap_slack": CAP_SLACK,
        "gates": gates,
        "w6_openai_native_allowed": False,
        "w6_blocker": w6_blocker,
        "rows": rows,
        "errors": errors,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path
    except OSError as exc:
        fallback = Path("/tmp/search-quality-w0.json")
        fallback.write_text(text, encoding="utf-8")
        print(f"WARN write {path} failed ({exc}); wrote {fallback}")
        return fallback


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
    filter_backup = BACKUP_DIR / "w0-filter-original.py"
    pipe_backup = BACKUP_DIR / "w0-pipe-original.py"
    restore_info: dict[str, Any] | None = None
    payload: dict[str, Any] = {
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "original": {
            "filter_sha12": sha12(original_filter),
            "pipe_sha12": sha12(original_pipe),
            "snapshot": snapshot_search_state(h),
        },
    }

    if args.revert and not args.apply and not args.run:
        if filter_backup.exists() and pipe_backup.exists():
            original_filter = filter_backup.read_text(encoding="utf-8")
            original_pipe = pipe_backup.read_text(encoding="utf-8")
        restore_info = restore(h, original_filter, pipe_obj, original_pipe)
        payload["restore"] = restore_info
        written = _write_json(OUT, payload)
        print(f"wrote {written}")
        return 0 if restore_info["filter_matches"] and restore_info["pipe_matches"] else 1

    try:
        filter_backup.write_text(original_filter, encoding="utf-8")
        pipe_backup.write_text(original_pipe, encoding="utf-8")
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
    return code


if __name__ == "__main__":
    raise SystemExit(main())
