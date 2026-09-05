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
from text_web_search_eval import (
    score_case,
    score_stored_row,
    summarize,
    summarize_eval_b,
    summarize_fetch_diag,
)
from text_web_search_eval_cases import (
    CANARY_CASE_IDS,
    FETCH_DIAG_MODEL_IDS,
    case_by_id,
    cases_for_suite,
)
from text_web_search_eval_oracle import ORACLE_SCHEMA, OracleError, fetch_github_latest_oracle
from text_web_search_ops import chat_with_optional_search, headers, signin, snapshot_eval_instance

DEFAULT_OUT = Path("/opt/cursor/artifacts/text_web_search_eval_b.json")
DEFAULT_FETCH_DIAG_OUT = Path("/opt/cursor/artifacts/text_web_search_eval_b_fetch_diag.json")
SUITE_VERSION = {
    "eval-b": "eval-b-v2",
    "eval-v1": "eval-v1",
    "fetch-diag": "fetch-diag-v1",
}


def _short(model_id: str) -> str:
    prefix = f"{PIPE}."
    rest = model_id[len(prefix) :] if model_id.startswith(prefix) else model_id
    return rest.split(".", 1)[-1]


def _model_aliases(model_id: str) -> set[str]:
    prefix = f"{PIPE}."
    rest = model_id[len(prefix) :] if model_id.startswith(prefix) else model_id
    return {model_id.lower(), rest.lower(), _short(model_id).lower()}


def _select_models(raw: str | None, *, suite: str) -> list[str]:
    pool = FETCH_DIAG_MODEL_IDS if suite == "fetch-diag" else TEXT_WEB_SEARCH_MODEL_IDS
    if not raw:
        return list(pool)
    wanted = {part.strip().lower() for part in raw.split(",") if part.strip()}
    picked = [model_id for model_id in pool if _model_aliases(model_id) & wanted]
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
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    try:
        tmp.replace(path)
    except OSError:
        path.write_text(text, encoding="utf-8")
        tmp.unlink(missing_ok=True)


def jsonl_path_for(path: Path) -> Path:
    return path.with_suffix(".jsonl")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def load_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            if index == len(lines) - 1:
                break
            raise
    return rows


def load_payload(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_checkpoint(out_path: Path) -> dict[str, Any] | None:
    compact = load_payload(out_path)
    rows = load_jsonl_rows(jsonl_path_for(out_path))
    if compact is None and not rows:
        return None
    payload = dict(compact or {})
    if rows:
        payload["rows"] = rows
    return payload


def build_manifest(
    *,
    suite: str,
    seed: int,
    models: list[str],
    cases: list[dict],
    jobs: list[tuple[str, dict, int]],
    filter_sha: str,
) -> dict[str, Any]:
    return {
        "suite_version": SUITE_VERSION[suite],
        "seed": seed,
        "models": list(models),
        "cases": [case["id"] for case in cases],
        "job_keys": [job_key(model_id, case["id"], repeat_id) for model_id, case, repeat_id in jobs],
        "oracle_schema": ORACLE_SCHEMA,
        "filter_sha": filter_sha,
    }


def manifest_mismatch(stored: dict[str, Any] | None, expected: dict[str, Any]) -> str | None:
    if not stored:
        return "missing campaign manifest"
    for key in ("suite_version", "seed", "models", "cases", "job_keys", "oracle_schema", "filter_sha"):
        if stored.get(key) != expected.get(key):
            return f"manifest {key} mismatch"
    return None


def recount_hard_errors(rows: list[dict[str, Any]]) -> int:
    return sum(1 for row in rows if not (row.get("chat_transport_ok") or row.get("ok_http")))


def jobs_complete(rows: list[dict[str, Any]], expected_keys: list[str]) -> bool:
    actual = {job_key(row["model_id"], row["case_id"], int(row.get("repeat_id") or 0)) for row in rows}
    return actual == set(expected_keys)


def messages_for_case(case: dict[str, Any]) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    system = case.get("system") or ""
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": case["prompt"]})
    return messages


def _sleep_backoff(attempt: int) -> None:
    time.sleep(min(32, 4 * (2**attempt)))


def _call_with_retry(
    h: dict[str, str],
    model_id: str,
    messages: list[dict[str, str]],
    *,
    timeout: int,
) -> tuple[dict[str, str], dict[str, Any]]:
    last: dict[str, Any] | None = None
    result: dict[str, Any] = {"status": 0}
    for attempt in range(3):
        result = chat_with_optional_search(
            h,
            model_id,
            messages,
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


def _summarize_suite(suite: str, rows: list[dict[str, Any]], extra: list[dict[str, Any]]) -> dict[str, Any]:
    if suite == "eval-b":
        return summarize_eval_b(rows, extra_controls=extra)
    if suite == "fetch-diag":
        return summarize_fetch_diag(rows)
    return summarize(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only ST-14 search quality eval")
    parser.add_argument("--suite", default="eval-b", choices=("eval-b", "eval-v1", "fetch-diag"))
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
    if args.suite == "fetch-diag" and args.out == str(DEFAULT_OUT):
        out_path = DEFAULT_FETCH_DIAG_OUT

    if args.snapshot_out or args.verify_snapshot:
        h = headers(signin())
        current = snapshot_eval_instance(h)
        if args.snapshot_out:
            snap_path = Path(args.snapshot_out)
            atomic_write(snap_path, current)
            print(
                f"wrote snapshot {snap_path} filter={current['content_sha12']} "
                f"pipe={current['pipe']['content_sha12']} owui={current['owui_version']}"
            )
            return 0
        previous = json.loads(Path(args.verify_snapshot).read_text(encoding="utf-8"))
        if current != previous:
            print("ERR instance fingerprint changed")
            print(json.dumps({"before": previous, "after": current}, ensure_ascii=False, indent=2)[:4000])
            return 2
        print("OK instance fingerprint unchanged")
        return 0

    if args.rescore:
        raw = json.loads(Path(args.rescore).read_text(encoding="utf-8"))
        rescored = []
        for row in raw.get("rows") or []:
            scored = score_stored_row(case_by_id(row["case_id"]), row)
            if row.get("oracle"):
                scored["oracle"] = row["oracle"]
            rescored.append(scored)
        extra = _load_v1_controls(Path(args.v1_json)) if (raw.get("suite") or args.suite) == "eval-b" else []
        summary = _summarize_suite(raw.get("suite") or args.suite, rescored, extra)
        families: dict[str, list] = {}
        for row in rescored:
            families.setdefault(row["family"], []).append(row)
        report = {
            "source": args.rescore,
            "rescored": True,
            "oracle_schema": ORACLE_SCHEMA,
            "suite": raw.get("suite") or args.suite,
            "started": raw.get("started"),
            "finished": datetime.now(timezone.utc).isoformat(),
            "read_only": True,
            "models": raw.get("models"),
            "case_ids": raw.get("case_ids"),
            "snapshot_before": raw.get("snapshot_before"),
            "summary": summary,
            "passed": summary.get("passed"),
            "total": len(rescored),
            "conflict_pass": sum(1 for row in families.get("conflict", []) if row["conflict_ok"]),
            "conflict_total": len(families.get("conflict", [])),
            "rows": rescored,
        }
        atomic_write(out_path, report)
        rec = summary.get("recommendation") or {}
        print(
            f"rescore passed={report['passed']}/{report['total']} "
            f"gates={summary.get('gates')} recommend={rec.get('choice')} wrote {out_path}"
        )
        return 0

    models = [TEXT_WEB_SEARCH_CANARY_MODEL_ID] if args.canary else _select_models(args.models, suite=args.suite)
    cases = _select_cases(args.suite, args.cases, canary=args.canary)
    jobs = expand_jobs(models, cases, seed=args.seed, canary=args.canary)
    expected_keys = [job_key(model_id, case["id"], repeat_id) for model_id, case, repeat_id in jobs]
    token = signin()
    h = headers(token)
    snapshot_before = snapshot_eval_instance(h)
    expected_manifest = build_manifest(
        suite=args.suite,
        seed=args.seed,
        models=models,
        cases=cases,
        jobs=jobs,
        filter_sha=snapshot_before["content_sha12"],
    )

    payload = load_checkpoint(out_path) if args.resume else None
    if args.resume:
        mismatch = manifest_mismatch((payload or {}).get("manifest"), expected_manifest)
        if mismatch:
            print(f"ERR resume rejected: {mismatch}")
            return 2

    completed: dict[str, dict[str, Any]] = {}
    if payload:
        for row in payload.get("rows") or []:
            completed[job_key(row["model_id"], row["case_id"], int(row.get("repeat_id") or 0))] = row
    started = (payload or {}).get("started") or datetime.now(timezone.utc).isoformat()
    if payload and payload.get("snapshot_before"):
        snapshot_before = payload["snapshot_before"]
    if not args.resume:
        jsonl_path_for(out_path).write_text("", encoding="utf-8")

    print(
        f"eval start suite={args.suite} version={expected_manifest['suite_version']} "
        f"models={len(models)} jobs={len(jobs)} resume={len(completed)} out={out_path}"
    )

    extra = _load_v1_controls(Path(args.v1_json)) if args.suite == "eval-b" else []
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
        h, result = _call_with_retry(h, model_id, messages_for_case(case), timeout=args.timeout)
        row = score_case(case, result, model_id=model_id, repeat_id=repeat_id, oracle=oracle)
        if oracle:
            row["oracle"] = {
                key_name: oracle[key_name]
                for key_name in ("tag_name", "published_at", "published_day", "url", "fetched_at", "oracle_schema")
                if key_name in oracle
            }
        completed[key] = row
        append_jsonl(jsonl_path_for(out_path), row)
        mark = "PASS" if row["passed"] else "FAIL"
        print(
            f"{mark} {_short(model_id)} {case['id']}#{repeat_id} "
            f"status={row['status']} search={row['web_search_requests']} "
            f"fetch_hard={row['fetch_called_hard']} cost={row['request_total_cost_usd']} "
            f"search_ok={row['search_ok']} answer_ok={row['answer_ok']} "
            f"reported_fail={row['fetch_reported_failure']}"
        )
        rows = list(completed.values())
        summary = _summarize_suite(args.suite, rows, extra)
        atomic_write(
            out_path,
            {
                "started": started,
                "finished": datetime.now(timezone.utc).isoformat(),
                "read_only": True,
                "suite": args.suite,
                "manifest": expected_manifest,
                "models": models,
                "case_ids": [case["id"] for case in cases],
                "snapshot_before": snapshot_before,
                "summary": summary,
                "rows": rows,
            },
        )
        if args.sleep:
            time.sleep(args.sleep)

    payload = load_checkpoint(out_path) or {}
    rows = payload.get("rows") or []
    summary = _summarize_suite(args.suite, rows, extra)
    payload["summary"] = summary
    payload["finished"] = datetime.now(timezone.utc).isoformat()
    payload["manifest"] = expected_manifest
    atomic_write(out_path, payload)
    rec = summary.get("recommendation") or {}
    hard_errors = recount_hard_errors(rows)
    complete = jobs_complete(rows, expected_keys)
    print(
        f"eval done passed={summary.get('passed')}/{summary.get('total')} "
        f"gates={summary.get('gates')} recommend={rec.get('choice')} "
        f"hard_errors={hard_errors} complete={complete} wrote {out_path}"
    )
    return final_exit(
        hard_errors=hard_errors,
        complete=complete,
        strict=args.strict,
        gates=summary.get("gates"),
    )


if __name__ == "__main__":
    sys.exit(main())
