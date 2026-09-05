# ST-14 Search 质量评测结果（2026-09-05）

> **只读**。未改 Filter / Pipe / 挂载 / Banner。  
> 原始逐题 JSON：`/opt/cursor/artifacts/text_web_search_eval.json`  
> 跑次：2026-09-05 16:08–16:24 UTC；42 次 completions；账单合计约 **$3.02**。

机械建议（`recommend_next_step()`）：**tune_thresholds**。未确认前不改实例。

---

## 1. 总表

| 指标 | 值 | 含义 |
|------|----|------|
| 通过 | **37 / 42** | 失败 5 题全部是 `url_fetch` |
| 该搜就搜 | **28 / 28 = 100%** | freshness / official / conflict / zh_synth |
| 闲置误搜 | **0 / 7 = 0%** | 纯算术题无 search/fetch 硬证据 |
| 引用（非 idle） | **30 / 35 = 86%** | 5 个 Fetch 题读了页面但没给出 `https://` |
| 官方域名 | **7 / 7** | official 均命中 `anthropic.com` |
| Fetch 硬证据 | **5 / 7** | Sol 两条有；Anthropic 无计数；Grok/Gemini 有 “Fetching web page…” |
| 超 `$0.05` | **25 / 42 = 60%** | 配置的成本门几乎不是账单上限 |
| 机械建议 | `tune_thresholds` | 因超标比例 > 30% |

按模型（6 题）：Sol Pro **6/6**，Sol **6/6**，其余 **5/6**（皆栽在 Fetch 引用 URL）。

---

## 2. 和落地时假设的差异

落地 smoke 用弱提示（「今天 UTC 日期」）时多数不搜，强制 “You must call web_search” 才 7/7。本题库用**自然语言搜索意图**，7 个模型全部自动搜。

结论：ST-14 证明的「能搜」在真实搜题上已经变成「该搜就搜」。**不为自动触发去上 Controller。** 弱闲聊/常识题仍可能不搜，那是省钱，不是本基线的失败。

无需搜索（`17 × 23`）7/7 都没搜。误搜不是当前问题。

---

## 3. 真正的缺口

### A. `$0.05` 不是最终账单硬上限（主缺口）

Search 题普遍 `$0.08–$0.15`。Fable `zh_synth` `$0.34`（2 次 search）。Sol Pro `freshness` 搜了 **6** 次（`max_uses=3` 被忽略）。OpenRouter 会做完已挂起调用再出最终回答。

### B. 指定 URL 时常读页但不给可点 `https://`

7 个模型都引用了文档里 “`:online` variant are deprecated” 原句。只有两条 Sol 写出完整 OpenRouter URL。Grok / Gemini 有 Fetch 事件但正文无链接；Opus / Fable 无 Fetch 硬证据，正文用相对路径 `/docs/...`，仍像读过页。

这是引用卫生 + Anthropic telemetry，不是「不能读页」。

### C. `web_fetch_requests` 计数基本为 0

即使 status 出现 “Fetching web page…” 或 `tool_calls_executed=1`，usage 里的 `web_fetch_requests` 仍常为 0。验收不能只盯这一个字段。

---

## 4. 下一步两档（须确认再做）

评测脚本机械建议是 **先调阈值**。按宪法把顶级方案一并摆上：

### 顶级 — 成本硬闸 + Fetch 引用 Controller

在 Pipe / 请求路径上做**真正停工具**的成本闸（现网 `$0.05` 做不到），并对「用户给了 URL 却 0 次 fetch / 0 个 https」最多重试一次，只保留真实 URL。能把账单和 Fetch 引用收到 ChatGPT 档。要改 Pipe，回归面大。

### 简单稳 — 按实测改 Filter 预算 + 一句 Fetch 指引（建议先选）

不改 Pipe、不重试：

1. 把成本门改到接近实测（例如 `$0.15`）**或**把 `max_results` / `context` / `step_count` 往下收，让账单接近现在写的 `$0.05`。两者效果相反，确认时选一个方向。
2. Filter 加一句：用户给出 URL 时必须 `web_fetch`，回答里保留完整 `https://`。
3. 不扩 DeepSeek / Kimi / Qwen；不上 Deep Research；不重开 broad Web Tools。

不做的代价：Search 题会继续经常打到 `$0.10+`；Fetch 题部分模型不给可点击链接。做简单档的代价：改薄 Filter valves / 一段指引，可回滚。

**本波不实施。** 等确认选「抬门 / 收预算 / Controller / 先不动」。
