#!/usr/bin/env python3
"""Read-only ST-14 eval runner. EVAL-B is the correction suite."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import PIPE, TEXT_WEB_SEARCH_CANARY_MODEL_ID, TEXT_WEB_SEARCH_MODEL_IDS
from text_web_search_eval import score_case, score_stored_row, summarize, summarize_eval_b
from text_web_search_eval_cases import CANARY_CASE_IDS, V1_CASES, case_by_id, cases_for_suite
from text_web_search_eval_oracle import OracleError, fetch_github_latest_oracle
from text_web_search_ops import chat_with_optional_search, headers, signin, snapshot_search_state

DEFAULT_OUT = Path("/opt/cursor/artifacts/text_web_search_eval_b.json")


def _short(model_id: str) -> str:
    prefix = f"{PIPE}."
    rest = model_id[len(prefix) :] if model_id.startswith(prefix) else model_id
    return rest.split(".", 1)[-1]


def _model_aliases(model_id: str) -> set[str]:
    prefix = f"{PIPE}."
    rest = model_id[len(prefix) :] if model_id.startswith(prefix) else model_id
    return {model_id.lower(), rest.lower(), _short(model_id).lower()}


def _select_models(raw: str | None) -> list[str]:
    if not raw:
        return list(TEXT_WEB_SEARCH_MODEL_IDS)
    wanted = {part.strip().lower() for part in raw.split(",") if part.strip()}
    picked = [model_id for model_id in TEXT_WEB_SEARCH_MODEL_IDS if _model_aliases(model_id) & wanted]
    if not picked:
        raise SystemExit(f"no models matched --models {raw}")
    return picked


def _select_cases(suite: str, raw: str | None, *, canary: bool) -> list[dict]:
    cases = cases_for_suite(suite)
    if canary:
        cases = [case for case in cases if case["id"] in CANARY_CASE_IDS]
    if raw:
        wanted = {part.strip() for part in raw.split(",") if part.strip()}
        cases = [case for case in cases if case["id"] in wanted]
    if not cases:
        raise SystemExit("no cases selected")
    return cases


def job_key(model_id: str, case_id: str, repeat_id: int) -> str:
    return f"{model_id}|{case_id}|{repeat_id}"


def expand_jobs(models: list[str], cases: list[dict], *, seed: int, canary: bool) -> list[tuple[str, dict, int]]:
    jobs: list[tuple[str, dict, int]] = []
    for model_id in models:
        for case in cases:
            repeats = 1 if canary else int(case.get("repeats") or 1)
            for repeat_id in range(repeats):
                jobs.append((model_id, case, repeat_id))
    by_model: dict[str, list[tuple[str, dict, int]]] = {model_id: [] for model_id in models}
    rng = random.Random(seed)
    for job in jobs:
        by_model[job[0]].append(job)
    for model_id in models:
        rng.shuffle(by_model[model_id])
    rotated: list[tuple[str, dict, int]] = []
    while any(by_model.values()):
        for model_id in models:
            if by_model[model_id]:
                rotated.append(by_model[model_id].pop(0))
    return rotated


def atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def load_payload(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _sleep_backoff(attempt: int) -> None:
    time.sleep(min(32, 4 * (2**attempt)))


def _call_with_retry(h: dict[str, str], model_id: str, prompt: str, *, timeout: int) -> tuple[dict[str, str], dict[str, Any]]:
    last: dict[str, Any] | None = None
    for attempt in range(3):
        result = chat_with_optional_search(
            h,
            model_id,
            [{"role": "user", "content": prompt}],
            enable_search=True,
            timeout=timeout,
        )
        if result["status"] == 401 and attempt == 0:
            h = headers(signin())
            continue
        if result["status"] in {429, 500, 502, 503, 504} and attempt < 2:
            _sleep_backoff(attempt)
            last = result
            continue
        return h, result
    return h, last or result


def final_exit(*, hard_errors: int, complete: bool, strict: bool, gates: dict[str, str] | None) -> int:
    if hard_errors or not complete:
        return 2
    if strict and any(band != "green" for band in (gates or {}).values()):
        return 1
    return 0


def _load_v1_controls(path: Path | None) -> list[dict[str, Any]]:
    if not path or not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    extra: list[dict[str, Any]] = []
    for row in payload.get("rows") or []:
        if row.get("case_id") != "idle":
            continue
        extra.append(score_stored_row(case_by_id("idle"), row))
    return extra


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only ST-14 search quality eval")
    parser.add_argument("--suite", default="eval-b", choices=("eval-b", "eval-v1"))
    parser.add_argument("--models", help="Comma-separated short names or full ids")
    parser.add_argument("--cases", help="Comma-separated case ids")
    parser.add_argument("--canary", action="store_true", help="Flash + one implicit + one control + one fetch")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--rescore", help="Rescore a previous JSON without live calls")
    parser.add_argument("--snapshot-out", help="Write a read-only instance fingerprint and exit")
    parser.add_argument("--verify-snapshot", help="Compare current instance to a saved fingerprint")
    parser.add_argument("--v1-json", default="/opt/cursor/artifacts/text_web_search_eval.json")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--sleep", type=float, default=2.0)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--seed", type=int, default=14)
    args = parser.parse_args()
    out_path = Path(args.out)

    if args.snapshot_out or args.verify_snapshot:
        h = headers(signin())
        current = snapshot_search_state(h)
        if args.snapshot_out:
            snap_path = Path(args.snapshot_out)
            atomic_write(snap_path, current)
            print(f"wrote snapshot {snap_path} sha={current['content_sha12']}")
            return 0
        previous = json.loads(Path(args.verify_snapshot).read_text(encoding="utf-8"))
        if current != previous:
            print("ERR instance fingerprint changed")
            print(json.dumps({"before": previous, "after": current}, ensure_ascii=False, indent=2)[:2000])
            return 2
        print("OK instance fingerprint unchanged")
        return 0

    if args.rescore:
        raw = json.loads(Path(args.rescore).read_text(encoding="utf-8"))
        rescored = []
        for row in raw.get("rows") or []:
            case = case_by_id(row["case_id"])
            rescored.append(score_stored_row(case, row))
        families: dict[str, list] = {}
        for row in rescored:
            families.setdefault(row["family"], []).append(row)
        report = {
            "source": args.rescore,
            "rescored": True,
            "passed": sum(1 for row in rescored if row["passed"]),
            "total": len(rescored),
            "conflict_pass": sum(1 for row in families.get("conflict", []) if row["conflict_ok"]),
            "conflict_total": len(families.get("conflict", [])),
            "rows": rescored,
        }
        out_path = Path(str(args.out).replace(".json", "_rescored.json")) if args.out == str(DEFAULT_OUT) else Path(args.out)
        atomic_write(out_path, report)
        print(
            f"rescore passed={report['passed']}/{report['total']} "
            f"conflict={report['conflict_pass']}/{report['conflict_total']} wrote {out_path}"
        )
        return 0

    models = [TEXT_WEB_SEARCH_CANARY_MODEL_ID] if args.canary else _select_models(args.models)
    cases = _select_cases(args.suite, args.cases, canary=args.canary)
    jobs = expand_jobs(models, cases, seed=args.seed, canary=args.canary)
    payload = load_payload(out_path) if args.resume else None
    completed: dict[str, dict[str, Any]] = {}
    if payload:
        for row in payload.get("rows") or []:
            completed[job_key(row["model_id"], row["case_id"], int(row.get("repeat_id") or 0))] = row
    started = (payload or {}).get("started") or datetime.now(timezone.utc).isoformat()
    snapshot_before = (payload or {}).get("snapshot_before")
    token = signin()
    h = headers(token)
    if snapshot_before is None:
        snapshot_before = snapshot_search_state(h)
    print(
        f"eval start suite={args.suite} models={len(models)} jobs={len(jobs)} "
        f"resume={len(completed)} out={out_path}"
    )

    hard_errors = 0
    for model_id, case, repeat_id in jobs:
        key = job_key(model_id, case["id"], repeat_id)
        if key in completed:
            print(f"SKIP {_short(model_id)} {case['id']}#{repeat_id}")
            continue
        oracle = None
        if case.get("needs_oracle"):
            try:
                oracle = fetch_github_latest_oracle()
            except OracleError as exc:
                print(f"ERR oracle {exc}")
                return 2
        h, result = _call_with_retry(h, model_id, case["prompt"], timeout=args.timeout)
        row = score_case(case, result, model_id=model_id, repeat_id=repeat_id, oracle=oracle)
        if oracle:
            row["oracle"] = {key: oracle[key] for key in ("tag_name", "published_at", "published_day", "url", "fetched_at")}
        completed[key] = row
        if not row["ok_http"]:
            hard_errors += 1
        mark = "PASS" if row["passed"] else "FAIL"
        print(
            f"{mark} {_short(model_id)} {case['id']}#{repeat_id} "
            f"status={row['status']} search={row['web_search_requests']} "
            f"fetch_hard={row['fetch_called_hard']} cost={row['request_total_cost_usd']} "
            f"search_ok={row['search_ok']} answer_ok={row['answer_ok']}"
        )
        rows = list(completed.values())
        extra = _load_v1_controls(Path(args.v1_json)) if args.suite == "eval-b" else []
        summary = summarize_eval_b(rows, extra_controls=extra) if args.suite == "eval-b" else summarize(rows)
        atomic_write(
            out_path,
            {
                "started": started,
                "finished": datetime.now(timezone.utc).isoformat(),
                "read_only": True,
                "suite": args.suite,
                "models": models,
                "case_ids": [case["id"] for case in cases],
                "snapshot_before": snapshot_before,
                "summary": summary,
                "rows": rows,
            },
        )
        if args.sleep:
            time.sleep(args.sleep)

    payload = load_payload(out_path) or {}
    extra = _load_v1_controls(Path(args.v1_json)) if args.suite == "eval-b" else []
    summary = summarize_eval_b(payload.get("rows") or [], extra_controls=extra) if args.suite == "eval-b" else summarize(payload.get("rows") or [])
    payload["summary"] = summary
    payload["finished"] = datetime.now(timezone.utc).isoformat()
    atomic_write(out_path, payload)
    rec = summary.get("recommendation") or {}
    print(
        f"eval done passed={summary.get('passed')}/{summary.get('total')} "
        f"gates={summary.get('gates')} recommend={rec.get('choice')} wrote {out_path}"
    )
    return final_exit(
        hard_errors=hard_errors,
        complete=len(payload.get("rows") or []) >= len(jobs),
        strict=args.strict,
        gates=summary.get("gates"),
    )


if __name__ == "__main__":
    sys.exit(main())
