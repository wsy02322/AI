# ST-14 EVAL-B 结果（2026-09-05，`eval-b-v2` 重算）

> **状态：质量已收口**（2026-09-05 用户确认）。保持现网薄 Filter；不上 Controller；不加 Filter 指引；不抬 `$0.05`。  
> **只读**。本页按精确 oracle（`github-release-v2`）重算原 70 次调用，**没有**重跑模型。  
> 原 JSON：`/opt/cursor/artifacts/text_web_search_eval_b.json`  
> 重算：`/opt/cursor/artifacts/text_web_search_eval_b_rescored.json`  
> 70 次新调用 + 复用 v1 7 道算术题；EVAL-B 账单约 **$3.66**（次数与成本未变）。

机械建议曾是 `diagnose_fetch`；A/B 之后决定收口。未再改 Filter / Pipe / Banner。  
文档只写「本波比对过的字段」：薄 Filter SHA / 挂载 / broad Filter。扩展指纹（Pipe content SHA、Banner、OWUI version、picker 摘要）见诊断波快照。

---

## 1. 验收门

| 门 | 结果 | 判定 |
|----|------|------|
| 隐含时效自动搜 | **42 / 42**，每模型 6/6 | **绿** |
| 无需搜索误搜 | **0 / 21**（14 新 + 7 道 v1 算术） | **绿** |
| 动态 Fetch 精确答案 | **10 / 14** | **红**（绿要 ≥13/14；黄要 ≥11/14） |
| 动态 Fetch 完整 URL | **14 / 14** | 绿 |
| 外层 chat 传输 | **14 / 14** 200 | 绿（**不是** Fetch 工具成功） |
| Fetch 硬证据 | **0 / 14** | 观察 |
| Fetch 软证据 | **10 / 14** | 观察 |
| 正文声称 Fetch 失败 | **4 / 14**（全是 Anthropic） | 观察 |
| 实例 Filter/挂载 | 开跑前 SHA `c6aed4ea80d6` | 只覆盖薄 Filter + 7 挂载 + disabled Filters |

v1 冲突题用新规则重评：**7 / 7** 仍过（官方 + 非官方域名、两个 URL、明确分歧）。

撤回 v1 口径的 **11/14 黄门** 和机械建议 `filter_guidance`。Opus#0 写了近似时间 `2026-08-31T14:55:00Z`，精确 RFC3339 `2026-08-31T14:55:53Z` 不通过。

---

## 2. 现在可以确定的

1. **弱提示也会搜。** 「OpenAI 这周发布了什么」「Claude Opus 现在价格」「OpenRouter 怎么给聊天加网页搜索」没有要求来源或 URL，7 个模型 42 次全搜了。自动触发不是本波缺口。
2. **误搜不是问题。** 算术、改写、求导 21 次零误搜。
3. **缺口在 Fetch，而且集中在 Anthropic。** 4 次失败都声称 GitHub API 不可达；Opus 两次改走 Search，Fable 两次既不 Fetch 也不 Search。Grok / Sol / Gemini 10 次 soft Fetch + 精确时间戳，答案全对。
4. **`web_fetch_requests` / `action=web_fetch` 仍然几乎看不到。** 本波硬证据 0/14。不能只靠这个字段验收，也不能把外层 chat 200 当成 Fetch 成功。
5. **成本只作观察：** p50 `$0.046`，p90 `$0.114`，max `$0.177`。不和 `$0.05` 工具门比，也不据此调阈值。
6. **还不能据此上薄 Filter 指引。** 失败形态是「声称 API 不可达」，不是「不知道该 Fetch」。指引是否有效要看 12 次 A/B。

---

## 3. Anthropic Fetch A/B（12 次 live）

对象：Opus 5、Fable 5.1。每模型 × 3 URL × 提示 A（基线）/ B（请求级 system，**未**写入 Filter）。  
JSON：`/opt/cursor/artifacts/text_web_search_eval_b_fetch_diag.json`  
账单约 **$0.62**。扩展指纹验证：**未变**（OWUI `0.11.3`，Pipe `f797e92d6d3f`，Filter `c6aed4ea80d6`，Banner `usage-guide-v4`，picker 21）。

| URL | A | B |
|-----|---|---|
| OpenRouter HTML | 2/2 | 2/2 |
| GitHub release HTML | 2/2 | 2/2 |
| GitHub API JSON | **0/2** | **0/2** |

B 没有优于 A（两边都是 4/6）。HTML 8/8 可读；API 4/4 正文声称失败，其中 Opus A 还改走 Search。硬证据仍是 0。B 没有读出 JSON。

### W6 决策（本波）

| 规则 | 结果 |
|------|------|
| B 明显优于 A，至少 5/6 精确通过 | **否**（B 仍是 4/6，API 全灭） |
| HTML 能读、GitHub API 不能 | **是** |
| GitHub HTML 可读 | **是**（API JSON 特殊受限） |
| A/B 都普遍失败 | 否，只失败在 API |
| B 增加无意义 Fetch/误搜 | 否 |
| 只有 Fable 失败 | 否，Opus 同样读不了 API |

**结论：不上薄 Filter 指引。** 缺口是 GitHub API 路由/访问限制，不是「模型不知道该 Fetch」。普通 HTML（含 GitHub 发布页）现网已经能读。

顶级档仍是 Pipe Controller（失败则改走 HTML / 受控重试），已列入 SPEC Later，须另 plan、另确认。

用户已确认 **收口 Search**：现网薄 Filter 保持；已知限制写进 SPEC ST-14。

---

## 4. 冻结

**不**抬 `$0.05`、**不**扩模型、**不上** Deep Research、**不**重开 broad Web Tools、**不**改 Filter / Pipe / Banner、**未确认不上** Search Controller。
