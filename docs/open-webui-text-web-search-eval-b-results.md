# ST-14 EVAL-B 结果（2026-09-05）

> **只读**。实例指纹与开跑前一致（Filter SHA `c6aed4ea80d6`）。  
> JSON：`/opt/cursor/artifacts/text_web_search_eval_b.json`  
> 70 次新调用 + 复用 v1 7 道算术题；EVAL-B 账单约 **$3.66**。

机械建议：`filter_guidance`。未确认前不改 Filter / Pipe。

---

## 1. 验收门

| 门 | 结果 | 判定 |
|----|------|------|
| 隐含时效自动搜 | **42 / 42**，每模型 6/6 | **绿** |
| 无需搜索误搜 | **0 / 21**（14 新 + 7 道 v1 算术） | **绿** |
| 动态 Fetch 答案 | **11 / 14** | **黄**（绿要 ≥13/14） |
| 动态 Fetch 完整 URL | **14 / 14** | 绿 |
| Fetch HTTP 错 | **0** | 绿 |
| 实例指纹 | 未变 | 通过 |

v1 冲突题用新规则重评：**7 / 7** 仍过（官方 + 非官方域名、两个 URL、明确分歧）。

---

## 2. 现在可以确定的

1. **弱提示也会搜。** 「OpenAI 这周发布了什么」「Claude Opus 现在价格」「OpenRouter 怎么给聊天加网页搜索」没有要求来源或 URL，7 个模型 42 次全搜了。v1 的「不需要 Controller 管自动触发」这次站得住。
2. **误搜不是问题。** 算术、改写、求导 21 次零误搜。
3. **缺口在 Fetch，而且集中在 Anthropic。** Fable 两次都说 GitHub API 不可达，没给出 `tag_name`/`published_at`；Opus 一次同样失败，另一次答对但无 Fetch 硬证据。Grok / Sol / Gemini 14 次里 10 次 soft Fetch + 精确时间戳，答案全对。
4. **`web_fetch_requests` / `action=web_fetch` 仍然几乎看不到。** 本波硬证据 0/14。不能只靠这个字段验收。
5. **成本只作观察：** p50 `$0.046`，p90 `$0.114`，max `$0.177`。不和 `$0.05` 工具门比，也不据此调阈值。

---

## 3. 下一步两档（须确认）

### 顶级 — Fetch 失败重试 Controller

用户给了 URL、0 次 Fetch 或答案对不上 oracle 时，最多内部重试一次，强制 `web_fetch` 并只保留真实 URL。能补 Anthropic 的「声称 API 不可达」。要改 Pipe，回归面大。

### 简单稳 — 薄 Filter 加 Fetch 指引（建议先选）

不改 Pipe、不重试。Filter 加短指引：用户给出 URL 时必须 `web_fetch`，按页回答，保留完整 `https://`。只动薄 Filter，可回滚。

不做的代价：Opus/Fable 遇到部分 URL（尤其 GitHub API）会继续拒读。做简单档的代价：一段指引，可能略增 Fetch 次数。

**不**抬 `$0.05`、**不**扩模型、**不上** Deep Research、**不**重开 broad Web Tools。
