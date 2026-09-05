# ST-14 EVAL-B：修正评测口径并定向补测

> **状态**：**修正波进行中**（`eval-b-v2` / `oracle_schema=github-release-v2`）。v1 口径的 11/14 黄门已撤回。未确认前不改 Filter / Pipe。  
> **日期**：2026-09-05  
> **现网**：OWUI 0.11.3；Pipe SHA `f797e92d6d3f`；薄 Filter `openrouter_text_web_search` default-on。

关联：`docs/open-webui-text-web-search-eval-plan.md`（v1 暂定）、`docs/open-webui-text-web-search-eval-results.md`。

---

## 0. 冻结

执行期间禁止写 Function / 模型 / Banner / Pipe。评测前后比对 Filter SHA、active/global/priority、7 模型挂载、broad Filter inactive。不读 Pipe 密钥。

v1 的 42 次结果保留为 `v1/provisional`。撤回「机械建议调阈值」和「不需要 Controller」。

---

## 1. 观测与评分

Search 只认 `web_search_requests` 或 `action=web_search`。Fetch 硬证据认 usage / `action=web_fetch` / 已完成 Fetch 状态；仅 “Fetching web page…” 为 soft。source URL 不得冒充 Search。

成本只报 `request_total_cost` 与分位数，**不**与 `$0.05` 工具门比较，也不据此自动选方案。

冲突题必须：两个注册域名、一个官方、一个非官方、正文明确分歧、至少两个 URL。`deprecated` 单独不算通过分析。

---

## 2. 题库（70 次新调用）

| 族 | 次数 | 内容 |
|----|------|------|
| `implicit_freshness` | 7×3×2 = 42 | 隐含时效，无「搜索/来源/URL/官网」指令 |
| `no_search_control` | 7×2 = 14 | 改写 + 永恒知识；加上 v1 算术共 21 |
| `dynamic_fetch` | 7×2 = 14 | 先 GET GitHub latest release，再让模型读同一 URL |

oracle GET 失败则停 Fetch，不花模型费用。

---

## 3. 跑法

```bash
python3 scripts/test_text_web_search_eval.py
python3 scripts/run_text_web_search_eval.py --suite eval-b --canary --resume
python3 scripts/run_text_web_search_eval.py --suite eval-b --resume
python3 scripts/run_text_web_search_eval.py --snapshot-out PATH
python3 scripts/run_text_web_search_eval.py --verify-snapshot PATH
python3 scripts/run_text_web_search_eval.py --rescore PATH --out PATH
python3 scripts/run_text_web_search_eval.py --suite fetch-diag --resume
```

每题原子 checkpoint；429/5xx 最多重试两次；质量失败不重试；HTTP/不完整非零退出；`--strict` 时验收门未绿也非零。

---

## 4. 验收门

- 隐含时效：绿 ≥38/42 且每模型 ≥5/6；黄 34–37 或有模型 4/6；红 ≤33 或有模型 ≤3/6。
- 无需搜索：21 题最多 1 次误搜；同一模型不得 2/3 误搜。
- Fetch：精确 `tag_name` token + 完整 RFC3339 `published_at` ≥13/14、完整 URL ≥13/14、外层 chat 200。**不**把外层 HTTP 叫 Fetch 成功。telemetry 与 `fetch_reported_failure` 单列。

---

## 5. 决策

隐含绿 + Fetch 非绿 → **`diagnose_fetch`**，先跑 Anthropic 12 次 A/B，**不**自动上 Filter 指引。

| 诊断结果 | 下一步 |
|------|--------|
| B 明显优于 A，至少 5/6 精确通过 | 可提案薄 Filter 指引 |
| HTML 能读、GitHub API 不能 | 域名/API 路由限制，不上全局指引 |
| GitHub HTML 可读 | API JSON 特殊受限；可 Search/HTML fallback |
| A/B 都普遍失败 | 指引无效，提案 Controller |
| B 增加无意义 Fetch/误搜 | 放弃指引 |
| 只有 Fable 失败 | provider-specific，不影响其余 6 模型 |
| 触发绿、Fetch 绿 | 不改实例 |
| 多数触发红 | 再提案 Controller 与简单档 |

成本高但质量好：单变量 A/B 预算。必须硬账单上限：另开 Pipe 自管循环 plan。

`python3 scripts/run_text_web_search_eval.py --suite fetch-diag` 只加请求级 system，不写 Filter。
