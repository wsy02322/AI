"""Score ST-14 live chat results. No instance writes."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from text_web_search_ops import (
    collect_source_urls,
    event_actions,
    has_fetch_evidence,
    has_search_evidence,
    tool_calls_executed,
    usage_cost_usd,
    web_fetch_requests,
    web_search_requests,
)

URL_RE = re.compile(r"https?://[^\s)\]>'\"，。]+", re.IGNORECASE)
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
CONFLICT_RE = re.compile(
    r"disagree|conflict|contradict|instead|deprecated|不再|不一致|冲突|相反|并不",
    re.IGNORECASE,
)
COST_CAP_USD = 0.05
AUTO_SEARCH_FLOOR = 0.60
CITATION_FLOOR = 0.50
IDLE_FALSE_POSITIVE_CEILING = 0.30
COST_OVER_SHARE = 0.30
CITATION_GUIDANCE_FLOOR = 0.75


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


def has_required_domain(urls: list[str], domains: list[str]) -> bool:
    wanted = tuple(domain.lower() for domain in domains)
    for url in urls:
        host = url_host(url)
        if any(host == domain or host.endswith(f".{domain}") for domain in wanted):
            return True
    return False


def failed_tools(result: dict[str, Any]) -> bool:
    blob = f"{result.get('blob') or ''}{result.get('error') or ''}{result.get('text') or ''}"
    return "No endpoints found that support tool use" in blob or "stream closed with reason: error" in blob


def score_case(case: dict[str, Any], result: dict[str, Any], *, model_id: str = "") -> dict[str, Any]:
    usage = result.get("usage") or {}
    events = result.get("events") or []
    text = result.get("text") or ""
    source_urls = collect_source_urls(events)
    text_urls = extract_text_urls(text)
    all_urls = list(dict.fromkeys([*source_urls, *text_urls]))
    searched = has_search_evidence(result)
    fetched = has_fetch_evidence(result)
    anthropic = "anthropic." in model_id
    page_quote = all(needle.lower() in text.lower() for needle in (case.get("required_needles") or []))
    anthropic_fetch_ok = bool(case.get("expect_fetch") and anthropic and searched and page_quote)
    cost = usage_cost_usd(usage)
    status = int(result.get("status") or 0)
    ok_http = status == 200 and not failed_tools(result)

    search_ok = True
    if case.get("expect_search"):
        search_ok = searched
    elif case["id"] == "idle":
        search_ok = not searched and not fetched

    fetch_ok = True
    if case.get("expect_fetch"):
        fetch_ok = fetched or anthropic_fetch_ok

    citation_ok = True
    if case.get("expect_search") or case.get("expect_fetch"):
        citation_ok = bool(all_urls)

    domain_ok = True
    if case.get("required_domains"):
        domain_ok = has_required_domain(all_urls, case["required_domains"])

    needles_ok = True
    if case.get("required_needles"):
        needles_ok = page_quote

    conflict_ok = True
    if case.get("expect_conflict"):
        conflict_ok = bool(CONFLICT_RE.search(text)) and citation_ok

    chinese_ok = True
    if case.get("expect_chinese"):
        chinese_ok = bool(CJK_RE.search(text))

    passed = ok_http and search_ok and fetch_ok and citation_ok and domain_ok and needles_ok and conflict_ok and chinese_ok
    return {
        "case_id": case["id"],
        "model_id": model_id,
        "status": status,
        "ok_http": ok_http,
        "searched": searched,
        "fetched": fetched,
        "anthropic_fetch_ok": anthropic_fetch_ok,
        "search_ok": search_ok,
        "fetch_ok": fetch_ok,
        "citation_ok": citation_ok,
        "domain_ok": domain_ok,
        "needles_ok": needles_ok,
        "conflict_ok": conflict_ok,
        "chinese_ok": chinese_ok,
        "passed": passed,
        "web_search_requests": web_search_requests(usage),
        "web_fetch_requests": web_fetch_requests(usage),
        "tool_calls_executed": tool_calls_executed(usage),
        "cost_usd": cost,
        "over_cost_cap": bool(cost is not None and cost > COST_CAP_USD),
        "source_urls": source_urls,
        "text_urls": text_urls,
        "actions": event_actions(events),
        "text_excerpt": text[:800],
    }


def _rate(ok: int, total: int) -> float | None:
    if total <= 0:
        return None
    return ok / total


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    search_expected = [row for row in rows if row["case_id"] in {"freshness", "official", "conflict", "zh_synth"}]
    fetch_expected = [row for row in rows if row["case_id"] == "url_fetch"]
    idle_rows = [row for row in rows if row["case_id"] == "idle"]
    cite_rows = [row for row in rows if row["case_id"] != "idle"]
    auto_search = _rate(sum(1 for row in search_expected if row["searched"]), len(search_expected))
    idle_fp = _rate(sum(1 for row in idle_rows if row["searched"] or row["fetched"]), len(idle_rows))
    citation = _rate(sum(1 for row in cite_rows if row["citation_ok"]), len(cite_rows))
    official = _rate(
        sum(1 for row in rows if row["case_id"] == "official" and row["domain_ok"]),
        sum(1 for row in rows if row["case_id"] == "official"),
    )
    fetch_hard = _rate(sum(1 for row in fetch_expected if row["fetched"]), len(fetch_expected))
    fetch_pass = _rate(sum(1 for row in fetch_expected if row["fetch_ok"]), len(fetch_expected))
    costed = [row for row in rows if row.get("cost_usd") is not None]
    cost_over = _rate(sum(1 for row in costed if row["over_cost_cap"]), len(costed))
    by_model: dict[str, dict[str, Any]] = {}
    for row in rows:
        bucket = by_model.setdefault(row["model_id"], {"passed": 0, "total": 0, "searched": 0, "cost_usd": 0.0})
        bucket["total"] += 1
        bucket["passed"] += int(row["passed"])
        bucket["searched"] += int(row["searched"])
        if row.get("cost_usd") is not None:
            bucket["cost_usd"] = round(bucket["cost_usd"] + float(row["cost_usd"]), 6)
    return {
        "total": len(rows),
        "passed": sum(1 for row in rows if row["passed"]),
        "auto_search_rate": auto_search,
        "idle_false_positive_rate": idle_fp,
        "citation_rate": citation,
        "official_domain_rate": official,
        "fetch_hard_evidence_rate": fetch_hard,
        "fetch_pass_rate": fetch_pass,
        "cost_over_cap_rate": cost_over,
        "cost_usd_total": round(sum(float(row["cost_usd"]) for row in costed), 6),
        "by_model": by_model,
        "recommendation": recommend_next_step(
            {
                "auto_search_rate": auto_search,
                "idle_false_positive_rate": idle_fp,
                "citation_rate": citation,
                "cost_over_cap_rate": cost_over,
            }
        ),
    }


def recommend_next_step(rates: dict[str, float | None]) -> dict[str, Any]:
    auto_search = rates.get("auto_search_rate")
    idle_fp = rates.get("idle_false_positive_rate")
    citation = rates.get("citation_rate")
    cost_over = rates.get("cost_over_cap_rate")
    reasons: list[str] = []
    if auto_search is not None and auto_search < AUTO_SEARCH_FLOOR:
        reasons.append(f"auto_search_rate {auto_search:.0%} < {AUTO_SEARCH_FLOOR:.0%}")
    if idle_fp is not None and idle_fp > IDLE_FALSE_POSITIVE_CEILING:
        reasons.append(f"idle_false_positive_rate {idle_fp:.0%} > {IDLE_FALSE_POSITIVE_CEILING:.0%}")
    if citation is not None and citation < CITATION_FLOOR:
        reasons.append(f"citation_rate {citation:.0%} < {CITATION_FLOOR:.0%}")
    if reasons:
        return {
            "choice": "controller",
            "label": "顶级：Search Quality Controller（须再确认）",
            "reasons": reasons,
        }
    if cost_over is not None and cost_over > COST_OVER_SHARE:
        return {
            "choice": "tune_thresholds",
            "label": "先按实测调步数/成本阈值（须再确认）",
            "reasons": [f"cost_over_cap_rate {cost_over:.0%} > {COST_OVER_SHARE:.0%}"],
        }
    if citation is not None and citation < CITATION_GUIDANCE_FLOOR:
        return {
            "choice": "filter_guidance",
            "label": "简单：薄 Filter 加判断/引用指引（须再确认）",
            "reasons": [f"citation_rate {citation:.0%} < {CITATION_GUIDANCE_FLOOR:.0%}"],
        }
    return {
        "choice": "hold",
        "label": "先不动实例，把本题库留作回归",
        "reasons": ["trigger, idle, and citation rates are within the hold band"],
    }
