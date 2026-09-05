#!/usr/bin/env python3
"""Read-only ST-14 quality baseline. Does not write Filter / Pipe / models / Banner."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import TEXT_WEB_SEARCH_MODEL_IDS
from text_web_search_eval import score_case, summarize
from text_web_search_eval_cases import CASES
from text_web_search_ops import chat_with_optional_search, headers, signin

DEFAULT_OUT = Path("/opt/cursor/artifacts/text_web_search_eval.json")


def _short(model_id: str) -> str:
    return model_id.rsplit(".", 1)[-1]


def _select_models(raw: str | None) -> list[str]:
    if not raw:
        return list(TEXT_WEB_SEARCH_MODEL_IDS)
    wanted = {part.strip().lower() for part in raw.split(",") if part.strip()}
    picked = [model_id for model_id in TEXT_WEB_SEARCH_MODEL_IDS if _short(model_id).lower() in wanted or model_id in wanted]
    if not picked:
        raise SystemExit(f"no models matched --models {raw}")
    return picked


def _select_cases(raw: str | None) -> list[dict]:
    if not raw:
        return list(CASES)
    wanted = {part.strip() for part in raw.split(",") if part.strip()}
    picked = [case for case in CASES if case["id"] in wanted]
    if not picked:
        raise SystemExit(f"no cases matched --cases {raw}")
    return picked


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only ST-14 search quality eval")
    parser.add_argument("--models", help="Comma-separated short names or full ids")
    parser.add_argument("--cases", help="Comma-separated case ids")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="JSON output path")
    parser.add_argument("--sleep", type=float, default=2.0, help="Seconds between live calls")
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()

    models = _select_models(args.models)
    cases = _select_cases(args.cases)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    token = signin()
    h = headers(token)
    rows: list[dict] = []
    started = datetime.now(timezone.utc).isoformat()
    print(f"eval start models={len(models)} cases={len(cases)} out={out_path}")

    for model_id in models:
        for case in cases:
            result = chat_with_optional_search(
                h,
                model_id,
                [{"role": "user", "content": case["prompt"]}],
                enable_search=True,
                timeout=args.timeout,
            )
            if result["status"] == 401:
                token = signin()
                h = headers(token)
                result = chat_with_optional_search(
                    h,
                    model_id,
                    [{"role": "user", "content": case["prompt"]}],
                    enable_search=True,
                    timeout=args.timeout,
                )
            row = score_case(case, result, model_id=model_id)
            rows.append(row)
            mark = "PASS" if row["passed"] else "FAIL"
            print(
                f"{mark} {_short(model_id)} {case['id']} "
                f"status={row['status']} search={row['web_search_requests']} "
                f"fetch={row['web_fetch_requests']} cost={row['cost_usd']} "
                f"searched={row['searched']} fetched={row['fetched']}"
            )
            if args.sleep:
                time.sleep(args.sleep)

    summary = summarize(rows)
    payload = {
        "started": started,
        "finished": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "models": models,
        "case_ids": [case["id"] for case in cases],
        "summary": summary,
        "rows": rows,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    rec = summary["recommendation"]
    print(
        f"eval done passed={summary['passed']}/{summary['total']} "
        f"auto_search={summary['auto_search_rate']} "
        f"idle_fp={summary['idle_false_positive_rate']} "
        f"citation={summary['citation_rate']} "
        f"recommend={rec['choice']}"
    )
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
