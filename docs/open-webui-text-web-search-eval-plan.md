# ST-14 Search 质量评测基线（只读）

> **状态**：**基线已跑完**（2026-09-05）。结果见 `docs/open-webui-text-web-search-eval-results.md`。未确认前不改 Filter / Pipe。  
> **日期**：2026-09-05  
> **现网**：OWUI 0.11.3；Pipe SHA `f797e92d6d3f`；薄 Filter `openrouter_text_web_search` 已 default-on。  
> **本波禁止**：改 Filter 源码 / valves、改 Pipe、改挂载 / default-on、改 Banner、扩模型、部署 Deep Research。

关联：`docs/open-webui-text-web-search-plan.md`（ST-14 已落地）、`docs/SPEC.md` ST-14。

---

## 0. 为什么现在评测，而不是直接改

ST-14 smoke 证明的是「强制提示下能搜」。现网还剩三个实质缺口：

1. **自动触发不可靠**：工具已挂，弱提示多数不搜。
2. **Anthropic Fetch 缺硬证据**：Opus / Fable 常无 `web_fetch` 计数，但正文可能引用页面。
3. **`$0.05` 不是最终账单硬上限**：OpenRouter 会做完已挂起调用再出最终回答。

未测完就上 Search Quality Controller，会在还不知道失败分布的情况下改 Pipe / 重试门。未测完只加 Filter 指引，也可能修不到真正的缺口。

本波只测量，不施工实例。

---

## 1. 两档后续（评测后再选，本波不实施）

### 顶级 — Search Quality Controller

隐藏策略层：该搜却 0 工具时最多重试一次；只引真实 URL；注入防护；按 provider 调预算。重试可能要改 Pipe。维护面明显大于薄 Filter。

### 简单 — Filter 判断指引 + 调阈值

在现有薄 Filter 里加何时搜索 / 何时 Fetch / 如何引用的短指引，按实测调 `step_count` / `$0.05`。不改 Pipe，不重试。

| 观测 | 倾向 |
|------|------|
| 该搜题自动触发 < 60%，或无需搜索误搜 > 30%，或已搜却几乎不给真实 URL | **Controller** |
| 触发尚可，但引用 / 冲突处理弱 | **Filter 指引** |
| 经常明显超过 `$0.05` 或步数顶满 | **只调阈值**（仍可与上两档叠加，须再确认） |
| 触发、闲置、引用都够用 | **先不动**，把题库留作回归 |

本波结束时必须按数据写出建议，**不得**未确认就改实例。

---

## 2. 题库（每模型 6 题，自然语言，不写 “You must call web_search”）

对象：ST-14 的 7 个 allowlist 文本模型。共 42 次 chat completions。一律带顶层 `filter_ids=["openrouter_text_web_search"]`，复用 `text_web_search_ops.chat_with_optional_search`。

| id | 目的 | 期望 |
|----|------|------|
| `freshness` | 时效新闻 | 应搜；有硬工具证据；正文或 source 事件含 `https://` |
| `official` | 官方域名 | 应搜；来源含 `anthropic.com` |
| `url_fetch` | 指定 URL | 应 Fetch（或 Anthropic：同轮已搜 + 引用页面原文）；正文含 `:online` 与 `deprecated` |
| `conflict` | 冲突来源 | 应搜；指出官方文档与仍提 `:online` 的第三方不一致 |
| `zh_synth` | 中文综合 | 应搜；中文作答并保留英文官方 URL |
| `idle` | 无需搜索 | **不得**出现 search 硬证据（纯算术，不提示“不要搜索”） |

硬证据只认：`web_search_requests`、`tool_calls_executed` / `web_fetch_requests`、status `action=web_search` / `web_fetch`、description `Fetching web page…`、source URL 事件。**不**把正文里的 `https://` 单独当成“已经搜过”。

---

## 3. 脚本与产物

```bash
python3 scripts/test_text_web_search_eval.py
python3 scripts/run_text_web_search_eval.py
```

- 只读：登录后只打 `/api/chat/completions`，不写 Function / 模型 / Banner / Pipe。
- 记录：HTTP status、usage、成本、步数、工具计数、source URLs、正文摘录、逐题布尔分。
- 汇总：自动触发率、闲置误搜率、引用率、官方域名命中、Fetch 硬证据率、超 `$0.05` 比例、按模型拆开。
- 建议档位由 `recommend_next_step()` 按 §1 表机械给出，供人确认，不自动施工。

结果写入 `docs/open-webui-text-web-search-eval-results.md` 与 artifacts JSON。完整事件流不入库。

---

## 4. 不做

- 不激活 `openrouter_web_tools`，不启用 OWUI native Web Search。
- 不把 DeepSeek / Kimi / Qwen 扩进 allowlist。
- 不部署 GPT Researcher / Open Deep Research。
- 不把本评测写成新的 ST 号；质量收口仍挂在 ST-14 后面。
- 不把本评测和 Image Studio / Live / Notebook 绑成一条施工。
