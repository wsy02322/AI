"""Score ST-14 eval results. Observation and verdicts are separate."""

from __future__ import annotations

import re
import statistics
from typing import Any
from urllib.parse import urlparse

from text_web_search_eval_oracle import FETCH_URL, oracle_answer_ok, oracle_fields_in_text
from text_web_search_ops import (
    collect_source_urls,
    event_actions,
    fetch_called_hard,
    fetch_called_soft,
    search_called,
    tool_calls_executed,
    tool_calls_requested,
    usage_cost_usd,
    web_fetch_requests,
    web_search_requests,
)

URL_RE = re.compile(r"https?://[^\s)\]>'\"，。]+", re.IGNORECASE)
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
DISAGREE_RE = re.compile(
    r"disagree|conflict|contradict|不一致|冲突|相反|并不相同|说法不同|互相矛盾",
    re.IGNORECASE,
)


def extract_text_urls(text: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for match in URL_RE.findall(text or ""):
        cleaned = match.rstrip(".,;:!?）)")
        if cleaned not in seen:
            seen.add(cleaned)
            urls.append(cleaned)
    return urls


def url_host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def registrable_domain(url: str) -> str:
    host = url_host(url)
    parts = [part for part in host.split(".") if part]
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def failed_tools(result: dict[str, Any]) -> bool:
    blob = f"{result.get('blob') or ''}{result.get('error') or ''}{result.get('text') or ''}"
    return "No endpoints found that support tool use" in blob or "stream closed with reason: error" in blob


def observe_result(result: dict[str, Any]) -> dict[str, Any]:
    usage = result.get("usage") or {}
    events = result.get("events") or []
    text = result.get("text") or ""
    source_urls = collect_source_urls(events)
    text_urls = extract_text_urls(text)
    status = int(result.get("status") or 0)
    return {
        "status": status,
        "ok_http": status == 200 and not failed_tools(result),
        "search_called": search_called(result),
        "fetch_called_hard": fetch_called_hard(result),
        "fetch_called_soft": fetch_called_soft(result),
        "source_present": bool(source_urls),
        "source_urls": source_urls,
        "text_urls": text_urls,
        "all_urls": list(dict.fromkeys([*source_urls, *text_urls])),
        "web_search_requests": web_search_requests(usage),
        "web_fetch_requests": web_fetch_requests(usage),
        "tool_calls_executed": tool_calls_executed(usage),
        "tool_calls_requested": tool_calls_requested(usage),
        "request_total_cost_usd": usage_cost_usd(usage),
        "usage": usage,
        "cost_details": usage.get("cost_details") if isinstance(usage.get("cost_details"), dict) else {},
        "prompt_tokens": usage.get("prompt_tokens") or usage.get("input_tokens"),
        "completion_tokens": usage.get("completion_tokens") or usage.get("output_tokens"),
        "actions": event_actions(events),
        "text": text,
        "text_excerpt": text[:800],
    }


def _conflict_ok(text: str, urls: list[str], official_domains: list[str]) -> dict[str, bool]:
    domains = [registrable_domain(url) for url in urls if registrable_domain(url)]
    official = {domain.lower() for domain in official_domains}
    has_official = any(domain in official for domain in domains)
    has_unofficial = any(domain not in official for domain in domains)
    two_urls = len(urls) >= 2
    disagreed = bool(DISAGREE_RE.search(text or ""))
    return {
        "has_official_domain": has_official,
        "has_unofficial_domain": has_unofficial,
        "two_urls": two_urls,
        "disagreed": disagreed,
        "conflict_ok": has_official and has_unofficial and two_urls and disagreed,
    }


def score_case(
    case: dict[str, Any],
    result: dict[str, Any],
    *,
    model_id: str = "",
    repeat_id: int = 0,
    oracle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    obs = observe_result(result)
    family = case.get("family") or "explicit_search"
    anthropic = "anthropic." in model_id
    text = obs["text"]
    urls = obs["all_urls"]

    search_ok = True
    fetch_ok = True
    citation_ok = True
    domain_ok = True
    needles_ok = True
    conflict_ok = True
    chinese_ok = True
    answer_ok = True
    url_ok = True
    telemetry_unobservable = False
    conflict_bits = {
        "has_official_domain": True,
        "has_unofficial_domain": True,
        "two_urls": True,
        "disagreed": True,
    }

    if family in {"implicit_freshness", "explicit_search"}:
        search_ok = obs["search_called"]
        if family == "explicit_search":
            citation_ok = bool(urls)
            if case.get("required_domains"):
                wanted = {domain.lower() for domain in case["required_domains"]}
                domain_ok = any(registrable_domain(url) in wanted for url in urls)
            if case.get("expect_chinese"):
                chinese_ok = bool(CJK_RE.search(text))
    elif family == "no_search_control":
        search_ok = not obs["search_called"] and not obs["fetch_called_hard"] and not obs["fetch_called_soft"]
    elif family == "dynamic_fetch":
        fields = oracle_fields_in_text(text, oracle)
        answer_ok = oracle_answer_ok(text, oracle)
        url_ok = fields["url_ok"] or FETCH_URL in text
        fetch_ok = obs["fetch_called_hard"]
        telemetry_unobservable = bool(answer_ok and not obs["fetch_called_hard"] and not obs["fetch_called_soft"])
    elif family == "v1_url_fetch":
        needles = case.get("required_needles") or []
        needles_ok = all(needle.lower() in text.lower() for needle in needles)
        url_ok = bool(urls)
        if case.get("required_domains"):
            wanted = {domain.lower() for domain in case["required_domains"]}
            domain_ok = any(registrable_domain(url) in wanted for url in urls)
        fetch_ok = obs["fetch_called_hard"] or obs["fetch_called_soft"]
        telemetry_unobservable = bool(needles_ok and anthropic and not fetch_ok)
        citation_ok = url_ok
    elif family == "conflict":
        search_ok = obs["search_called"]
        conflict_bits = _conflict_ok(text, urls, case.get("required_domains") or ["openrouter.ai"])
        conflict_ok = conflict_bits["conflict_ok"]
        citation_ok = conflict_bits["two_urls"]
        domain_ok = conflict_bits["has_official_domain"]

    passed = (
        obs["ok_http"]
        and search_ok
        and (fetch_ok if family == "v1_url_fetch" else True)
        and (answer_ok and url_ok if family == "dynamic_fetch" else True)
        and (citation_ok if family == "explicit_search" else True)
        and domain_ok
        and needles_ok
        and conflict_ok
        and chinese_ok
    )
    if family == "dynamic_fetch":
        passed = obs["ok_http"] and answer_ok and url_ok

    return {
        **obs,
        "case_id": case["id"],
        "family": family,
        "suite": case.get("suite") or "",
        "model_id": model_id,
        "repeat_id": repeat_id,
        "search_ok": search_ok,
        "fetch_ok": fetch_ok,
        "citation_ok": citation_ok,
        "domain_ok": domain_ok,
        "needles_ok": needles_ok,
        "conflict_ok": conflict_ok,
        "chinese_ok": chinese_ok,
        "answer_ok": answer_ok,
        "url_ok": url_ok,
        "telemetry_unobservable": telemetry_unobservable,
        "passed": passed,
        "cost_usd": obs["request_total_cost_usd"],
        "searched": obs["search_called"],
        "fetched": obs["fetch_called_hard"] or obs["fetch_called_soft"],
        **{f"conflict_{key}": value for key, value in conflict_bits.items() if key != "conflict_ok"},
    }


def score_stored_row(case: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    result = {
        "status": row.get("status") or 200,
        "text": row.get("text") or row.get("text_excerpt") or "",
        "usage": {
            "server_tool_use": {
                "web_search_requests": row.get("web_search_requests") or 0,
                "web_fetch_requests": row.get("web_fetch_requests") or 0,
                "tool_calls_executed": row.get("tool_calls_executed") or 0,
            },
            "cost": row.get("cost_usd") or row.get("request_total_cost_usd"),
        },
        "events": [],
        "blob": "",
        "error": "",
    }
    actions = row.get("actions") or []
    for item in actions:
        result["events"].append({"event": {"data": item}})
    for url in row.get("source_urls") or []:
        result["events"].append({"event": {"type": "source", "data": {"source": {"url": url}}}})
    return score_case(
        case,
        result,
        model_id=str(row.get("model_id") or ""),
        repeat_id=int(row.get("repeat_id") or 0),
    )


def _rate(ok: int, total: int) -> float | None:
    if total <= 0:
        return None
    return ok / total


def _cost_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    costs = [float(row["request_total_cost_usd"]) for row in rows if row.get("request_total_cost_usd") is not None]
    if not costs:
        costs = [float(row["cost_usd"]) for row in rows if row.get("cost_usd") is not None]
    if not costs:
        return {"count": 0, "total": 0.0, "p50": None, "p90": None, "max": None}
    ordered = sorted(costs)
    p90_index = min(len(ordered) - 1, max(0, round(0.9 * (len(ordered) - 1))))
    return {
        "count": len(ordered),
        "total": round(sum(ordered), 6),
        "p50": round(statistics.median(ordered), 6),
        "p90": round(ordered[p90_index], 6),
        "max": round(max(ordered), 6),
    }


def _band_implicit(ok: int, total: int, per_model: dict[str, tuple[int, int]]) -> str:
    if total <= 0:
        return "n/a"
    worst = min((passed / n if n else 0.0) for passed, n in per_model.values()) if per_model else 0.0
    if ok >= 38 and total == 42 and worst >= 5 / 6:
        return "green"
    if ok <= 33 or any((n and passed / n <= 3 / 6) for passed, n in per_model.values()):
        return "red"
    return "yellow"


def _band_control(false_positives: int, total: int, per_model: dict[str, int]) -> str:
    if total <= 0:
        return "n/a"
    if false_positives <= 1 and total >= 21 and max(per_model.values(), default=0) <= 1:
        return "green"
    if false_positives <= 1 and max(per_model.values(), default=0) <= 1:
        return "green"
    return "red" if max(per_model.values(), default=0) >= 2 or false_positives > 1 else "yellow"


def _band_fetch(answer_ok: int, url_ok: int, http_ok: int, total: int) -> str:
    if total <= 0:
        return "n/a"
    if http_ok == total and answer_ok >= 13 and url_ok >= 13 and total == 14:
        return "green"
    if http_ok == total and answer_ok >= 11 and url_ok >= 11:
        return "yellow"
    return "red"


def recommend_from_gates(gates: dict[str, str]) -> dict[str, Any]:
    implicit = gates.get("implicit_freshness") or "n/a"
    fetch = gates.get("dynamic_fetch") or "n/a"
    control = gates.get("no_search_control") or "n/a"
    if implicit == "red" or (implicit == "yellow" and fetch == "red"):
        return {
            "choice": "controller_or_guidance",
            "label": "多数触发偏弱：再提案 Controller 与简单指引两档",
            "reasons": [f"implicit={implicit}", f"fetch={fetch}", f"control={control}"],
        }
    if implicit == "green" and fetch == "green" and control == "green":
        return {
            "choice": "hold",
            "label": "不改实例，不上 Controller",
            "reasons": ["implicit, fetch, and control gates are green"],
        }
    if implicit == "green" and fetch != "green":
        return {
            "choice": "filter_guidance",
            "label": "触发够用，补薄 Filter 的 Fetch/完整 URL 指引",
            "reasons": [f"fetch={fetch}"],
        }
    if implicit == "yellow":
        return {
            "choice": "provider_guidance",
            "label": "个别 provider 偏弱：只给该家族加指引并 A/B",
            "reasons": [f"implicit={implicit}"],
        }
    return {
        "choice": "review",
        "label": "人工看分模型表后再选",
        "reasons": [f"implicit={implicit}", f"fetch={fetch}", f"control={control}"],
    }


def summarize_eval_b(rows: list[dict[str, Any]], *, extra_controls: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    implicit = [row for row in rows if row.get("family") == "implicit_freshness"]
    controls = [row for row in rows if row.get("family") == "no_search_control"]
    if extra_controls:
        controls = [*controls, *extra_controls]
    fetches = [row for row in rows if row.get("family") == "dynamic_fetch"]
    implicit_by: dict[str, list[dict[str, Any]]] = {}
    control_fp_by: dict[str, int] = {}
    for row in implicit:
        implicit_by.setdefault(row["model_id"], []).append(row)
    for row in controls:
        if not row.get("search_ok"):
            control_fp_by[row["model_id"]] = control_fp_by.get(row["model_id"], 0) + 1
    implicit_model = {
        model_id: (sum(1 for row in items if row.get("search_ok")), len(items))
        for model_id, items in implicit_by.items()
    }
    implicit_ok = sum(1 for row in implicit if row.get("search_ok"))
    control_fp = sum(1 for row in controls if not row.get("search_ok"))
    fetch_answer = sum(1 for row in fetches if row.get("answer_ok"))
    fetch_url = sum(1 for row in fetches if row.get("url_ok"))
    fetch_http = sum(1 for row in fetches if row.get("ok_http"))
    gates = {
        "implicit_freshness": _band_implicit(implicit_ok, len(implicit), implicit_model),
        "no_search_control": _band_control(control_fp, len(controls), control_fp_by),
        "dynamic_fetch": _band_fetch(fetch_answer, fetch_url, fetch_http, len(fetches)),
    }
    return {
        "total": len(rows),
        "passed": sum(1 for row in rows if row.get("passed")),
        "implicit_ok": implicit_ok,
        "implicit_total": len(implicit),
        "control_false_positives": control_fp,
        "control_total": len(controls),
        "fetch_answer_ok": fetch_answer,
        "fetch_url_ok": fetch_url,
        "fetch_http_ok": fetch_http,
        "fetch_total": len(fetches),
        "fetch_telemetry_unknown": sum(1 for row in fetches if row.get("telemetry_unobservable")),
        "implicit_by_model": {key: {"ok": ok, "total": total} for key, (ok, total) in implicit_model.items()},
        "cost": _cost_stats(rows),
        "gates": gates,
        "recommendation": recommend_from_gates(gates),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if any(row.get("suite") == "eval-b" or row.get("family") in {"implicit_freshness", "dynamic_fetch"} for row in rows):
        return summarize_eval_b(rows)
    explicit = [row for row in rows if row.get("family") == "explicit_search" or row.get("case_id") in {"freshness", "official", "zh_synth"}]
    return {
        "total": len(rows),
        "passed": sum(1 for row in rows if row.get("passed")),
        "explicit_search_rate": _rate(sum(1 for row in explicit if row.get("search_called") or row.get("searched")), len(explicit)),
        "cost": _cost_stats(rows),
        "note": "v1 summary does not recommend threshold tuning from total request cost",
    }
