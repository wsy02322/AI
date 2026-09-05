# ST-14 EVAL-B：修正评测口径并定向补测

> **状态**：**已确认执行**（2026-09-05）。只改评测脚本与文档，不改 Filter / Pipe / 挂载 / Banner。  
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
python3 scripts/run_text_web_search_eval.py --rescore PATH
```

每题原子 checkpoint；429/5xx 最多重试两次；质量失败不重试；HTTP/不完整非零退出；`--strict` 时验收门未绿也非零。

---

## 4. 验收门

- 隐含时效：绿 ≥38/42 且每模型 ≥5/6；黄 34–37 或有模型 4/6；红 ≤33 或有模型 ≤3/6。
- 无需搜索：21 题最多 1 次误搜；同一模型不得 2/3 误搜。
- Fetch：答案 ≥13/14、完整 URL ≥13/14、HTTP 错 0。telemetry 缺失单列。

---

## 5. 决策

| 结果 | 下一步 |
|------|--------|
| 触发绿、Fetch 绿 | 不改实例 |
| 触发绿、只有 URL 引用差 | 薄 Filter 指引 |
| 个别 provider 黄 | 只给该 provider 加指引 |
| 多数红 | 再提案 Controller 与简单档 |
| 成本高但质量好 | 单变量 A/B 预算 |
| 必须硬账单上限 | 另开 Pipe 自管循环 plan |
