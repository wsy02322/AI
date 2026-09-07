# 可计数检索：答案接近官网顶级，且 `$19` 不得再发

> **状态**：**仅 plan**（2026-09-07）。未确认不改实例 / Pipe / Filter / Banner。  
> **两句硬约束**：① 同类 `$19`（一次点发送、原厂内循环连搜、几十万～几百万 token）**务必不能再发生**。② 用户看到的 **回答** 里，搜索带来的事实/来源/时效，要 **接近或超过** ChatGPT / Grok.com / Gemini 官网顶级档。  
> **白话**：生产上 **不再用** OpenAI / Google / xAI 原厂搜（刹不住）。检索只走 **能计数** 的引擎；写作仍用现网旗舰。用「读整页 + 更好的可计数检索」去追官网答案，而不是把账单门拆掉。  
> **现网已有**：T1 压旧页；OpenAI / Google / xAI → Exa；Anthropic 原厂（认 `max_uses`）；12 个 public 文本默认搜；`$0.05` / `step_count=8`。  
> **现网没有**：T2 跨轮预算；T3 272k 悬崖；引擎烘焙；回归锁（有人把 `engine` 改回 `auto` 时 `verify_stack` 必须红）。

关联：`docs/open-webui-search-cost-plan.md`（`$19` 根因与 T1）；`docs/open-webui-text-web-search-plan.md` ST-14；`docs/open-webui-text-web-search-eval-b-results.md`（**改 Exa 前** 的短问质量）；`docs/SPEC.md` ST-14 / Later。

---

## 0. 结论先看

OpenRouter 文档写死：原厂搜的 `max_uses` **只转发给 Anthropic**。OpenAI / Google / xAI 原厂搜 **忽略** 次数门。Astra Pro 已用一次「你继续」打出 **46 次搜 / 495 万 input / ~`$19`**。同一阀门改走 Exa 后，同类探针是 **1 次搜 / 2.8 万 input / `$0.23`**。

因此：

| 想要 | 能不能和生产硬约束同时成立 |
|------|------------------------------|
| ChatGPT.com / Gemini 官网 / Grok.com **同栈检索** | **不能。** 那就是各家原厂搜；OpenAI/Google/xAI 在本管道里 **刹不住** |
| OpenRouter `engine=native` / `auto`（这三家） | **生产禁止。** 与「`$19` 不得再发」直接冲突 |
| 写作仍是 Astra / Sol / Grok / Gemini / Claude / 中国旗舰 | **能。** 不换弱模型、不关默认搜、不把 Sonar 当旗舰写作 |
| 答案里的搜索质量接近或超过官网 | **能试。** 可计数引擎（Exa / Perplexity Search / Parallel / Exa `deep`）+ **Fetch 整页**；官网不少场景只喂摘要 |
| Claude 原厂搜 | **能留。** Anthropic 认 `max_uses` |

「接近官网」验收的是 **正文**：关键事实、日期、可点来源、该搜的时候搜了。不是「检索后端 logo 和官网一样」。

| 档 | 做什么 | `$19` | 答案质量 | 复杂度 |
|----|--------|-------|----------|--------|
| **顶级 Q** | **Q-lock** 写进契约 + 回归锁 → **Q0** 可计数引擎烘焙（含中文/本地/时效）→ 赢家进生产 **Q1** → **Q2** T2+T3。烘焙若可计数全面输给「Google 类索引」，再单开 **Q3** Search Controller（自管循环 + 可计数搜索 API） | 硬保证 | 先量再换引擎；Fetch 仍读整页 | 中；Q3 才重 |
| **略简 Q−** | **Q-lock** + **Q2**（T2+T3+回归锁）。检索引擎维持现网 Exa `auto`，不烘焙 | 硬保证 | 赌「现网 Exa + Fetch 已经够接近」；**没有对照数据** | 低 |

S1 关默认搜、S2 拧全局阀门伤 EVAL-B、把 OpenAI/Google/xAI 改回原厂、用 Sonar 冒充旗舰写作：**不进主线**（会降质量或再炸账单）。

**最推荐先锁：Q-lock + Q0。** 用户要的是官网级 **答案**，不是「先省事维持 Exa」。不烘焙就换引擎或宣称已接近官网，都是猜。Q2 与 Q0 不抢同一把锁：Q0 只读、有费用上限；Q2 改 Pipe 记账，须另点头。

---

## 1. `$19` 事件：已经堵住什么，还缺什么

一次点发送 ≈ `$19` 的三层：

1. **原厂内循环**（主因）：Astra/OpenAI 在一次 HTTP 里搜 46 次，`$0.05` / `max_uses` 数不到。  
2. **旧整页回放**：T1 已压最后一条 user 之前的大 `function_call_output`。  
3. **「继续」换新额度**：每条用户消息阀门清零。T2 **未做**。连点 20 次「继续」仍可能数美元，但形态不是「一发 `$19`」。

**Q-lock（生产不变量，建议写入 SPEC Don't / `verify_stack`）：**

1. OpenAI / Google / xAI **类** 的 Search **和** Fetch：`engine` 必须是可计数集合 `{exa, perplexity, parallel, firecrawl}`，**禁止** `auto` / `native`。  
2. Anthropic 可 `auto`（原厂 + `max_uses`）。中国三只无原厂搜，保持 `auto`→Exa 或跟 Q1 赢家。  
3. T1 marker `SEARCH_PAGE_COMPACT_V1` 必须在；Pipe 更新 Runbook 必重放。  
4. `stop_server_tools_when`：`step_count_is=8` 与 `$0.05` **不抬**（SPEC 已 Don't）。  
5. 禁止为「更像官网」把这三家改回原厂，除非 Q3 Controller 已能在 **我们的循环** 里计数（不是厂商内循环）。

**一发 `$19` 的复现门（落地后必须绿）：** Astra Pro「搜过一轮 → 你继续」：`web_search_requests` ≤ 8，input 远低于 272k，上游 `$` 与 T1 烟雾同量级（现网对照 `$0.23`），不得再出现几十次搜 / 上百万 token。

**Q2 要补的洞：** 同一对话连续「继续」的 **累计** 工具 `$` + 新搜次数。没有 Q2，「务必不能再发生」对 **单发** 成立，对 **连点** 只是变慢变小，不是硬顶。

---

## 2. 「接近或超过官网」指什么

### 2.1 三层不要混

| 层 | 是什么 | 本站 |
|----|--------|------|
| 官网产品 | chatgpt.com / grok.com / gemini.google.com：检索 + 浏览代理 + 引用 UI + 记忆/应用 | **从来不是。** 本 plan 不装第二前端、不登录官网爬结果（ToS） |
| API 原厂搜 | OpenRouter `native`：Gemini≈Google grounding；Grok≈网页+X；OpenAI≈Responses web_search；Claude≈Claude.ai | OpenAI/Google/xAI **生产禁用**；Claude **可留** |
| 可计数检索 + 旗舰写作 | Exa / Perplexity Search / Parallel 出链接与摘录，模型 **Fetch 整页** 再写 | **本 plan 主路径** |

超过官网的真实来源：官网即时搜经常是 **摘要**。本站默认 **Fetch 整页（约 12k tokens/页）**。文档题、发布说明、长篇政策，读整页可以 **比官网摘要更准**。本地生活、地图、极强时效、必须 Google 索引或必须刷 X 的题，可计数引擎可能 **输**。

### 2.2 不拿官网 UI 当评测机

禁止：自动化登录 ChatGPT / Gemini / Grok.com 抓答案。  
允许：

- 公开 oracle（GitHub release 时间戳、官方文档固定句、EVAL-B 形态）。  
- **隔离、有硬顶** 的 Gemini **API 原厂搜** 只当 Q0 对照天花板（Flash、短题、总预算上限，**写进生产 Filter 则红**）。  
- 人工看：来源是否可点、日期/数字是否对、该搜的搜了、不该搜的没搜。

EVAL-B v2（隐含 42/42、误搜 0）是 **engine=auto 时代**。**不能**拿来证明现网 Exa 已接近官网。

### 2.3 Q0 题库（建议）

每引擎 × 少量模型，控制账单（目标 **≤ `$15`**，超则停）。

| 族 | 为何 |
|----|------|
| 隐含时效（本周产品新闻） | 官网强项；现网 Exa 烟雾已能搜到，要比 **来源质量** |
| 中文时政/站点 | Exa/Perplexity 相对 Google 的常见弱项 |
| 本地（天气、店铺、路线） | Gemini 官网 / Google 索引优势最大 |
| 精确 Fetch（官方 HTML / GitHub **HTML** 发布页） | 本站可超过摘要档；API JSON 仍是 Anthropic 已知限制，不本波修 |
| 误搜（算术） | 升引擎不得换来乱搜 |
| Astra Pro「你继续」 | **费用回归**，不是质量题 |

模型：Gemini Flash（便宜）、Grok、Astra（`$19` 那只）、Kimi（中文）。**不**对 12 只全跑 EVAL-B。

引擎候选（全部可 `max_uses` / `stop_server_tools_when`）：

| 引擎 | 现网 | 备注 |
|------|------|------|
| Exa `auto`（现网） | 是 | 基线 |
| Exa `deep` / `search_context_size=high` | 否 | 更贵、摘录更长；仍不是 Google |
| Perplexity Search（工具引擎，**不是**改用 Sonar 模型写作） | 否 | 排序网页结果；旗舰仍写答案 |
| Parallel | 否 | 抽取强；语言/价格另看 |

Firecrawl 要 BYOK：**不进 Q0**。Google CSE / SerpAPI：**Q3**，本波不申请钥匙。

**Q0 怎么判「接近或超过」：** 不以「和 ChatGPT 逐字相同」为门。门是：时效/中文/文档题的 **可引用正确率** 不低于现网 Exa，且对照 Gemini API 原厂（若跑了）差距 **可接受**（人工；计划里不先拍 90% 这种假精度）。本地题若可计数全面惨败，记为 Q3 触发条件，**不**因此改回生产原厂搜。

---

## 3. 顶级 Q vs 略简 Q−

### 3.1 顶级 Q（建议终态）

| 步 | 动作 | 过门 |
|----|------|------|
| **Q-lock** | SPEC / `verify_stack` / Filter 单测：三家不可 `auto`/`native`；T1 marker；不抬 `$0.05` | 有人改回原厂则 verify 红 |
| **Q0** | 只读烘焙；可临时改请求里的 `engine`，**不写回**生产 Filter。总预算封顶 | 写出赢家或「维持 Exa」；列出输给 Google 类索引的题型 |
| **Q1** | 仅当 Q0 赢家 ≠ 现网：Filter 对不可计数类改 `engine`（及可选 `mode` / `search_context_size`）。Anthropic 不动。merge valves，不覆盖 `API_KEY` | Search+Fetch 烟雾 + 误搜不升 + `$19` 复现门仍绿 |
| **Q2** | T2：单次用户消息内轮累计工具 `$`/次数不重置；T3：出站将超 ~200k 的旧工具页先压，避开 272k 2× | 连点「继续」不得再滚成数美元～`$19`；首轮调研仍够用 |
| **Q3** | **仅 Q0 证明可计数检索在中文/本地上不可接受** 才开独立 plan：Search Controller + 可计数网页 API（Brave / CSE 等）。循环在我们这边，才能既像 Google 又硬刹 | 另确认、另钥匙；**不是**把 Gemini 原厂搜写回 Filter |

Q3 是「检索要 Google 索引」的真顶级，也是唯一能同时满足两句硬约束的 Google 路径。比改 Filter 引擎重，**禁止**未烘焙就开工。

### 3.2 略简 Q−

Q-lock + Q2（回归锁 + T2 + T3）。引擎保持 Exa `auto`。

代价：没有数据就声称「接近官网」；中文/本地可能长期弱于 Gemini 官网。稳定、快、账单洞先补上。

### 3.3 停用（本 plan 不选）

| 不做 | 原因 |
|------|------|
| 生产恢复 OpenAI/Google/xAI `auto`/`native` | 直接再开 `$19` 类事件 |
| 关 ST-14 默认搜 / 只 Astra default-off | 答案质量下降 |
| 全局拧 `max_uses` / Fetch / `step_count` 当唯一方案 | 伤短问；挡不住原厂内循环 |
| 抬 `$0.05` | Don't；单轮会搜得更凶 |
| 用 Sonar 模型替换旗舰写作 | 身份错了 |
| 重开 `openrouter_web_tools` / OWUI native Web Search | 双搜、宽工具面 |
| Filter `is_global` | 图像条出现 Web Search |
| 未确认 Q3 就接 CSE/SerpAPI | 新供应商 + 新循环 |
| 为评测爬官网 | ToS |

---

## 4. 建议 ST 号

- **ST-14** 仍是薄 Search + Fetch、deny 类、default-on。不把本 plan 改写成「ST-14 质量未收口」。  
- **ST-15**（新）：**可计数检索硬约束** — 不可计数类禁止原厂搜；T1 必在；`$19` 复现门；T2/T3 属 ST-15 不是 ST-11/12。  
- Search Controller / GitHub API JSON 仍是 Later 的 Controller，与 Q3 相关但 **不是** Q0–Q2。

---

## 5. 分轮确认（一轮一个头）

未确认不施工。Q0 的隔离原厂对照 **不是** 批准生产原厂搜。

| 轮 | 只问 | 点头之后 | 不点头 |
|----|------|----------|--------|
| **Q-lock** | 生产：OpenAI/Google/xAI **永不** `auto`/`native`；`$19` 复现门进 verify | 改契约 + 单测/verify（Filter 已是 Exa 则行为不变） | 不写死；以后仍可能有人改回原厂 |
| **Q0** | 是否跑可计数烘焙（预算封顶，默认 ≤ `$15`） | 才发评测请求 | 不评测；质量主张保持「未量」 |
| **Q1** | 是否把 Q0 赢家写入生产 Filter | 才改 `engine`/`mode` | 维持 Exa `auto` |
| **Q2** | T2+T3 是否做；预算用 `$` 还是次数（数字 Q2 开工前定） | 才改 Pipe 记账/压 272k | 单发仍有刹；连点「继续」无累计顶 |
| **Q3** | 仅 Q0 记下「可计数不够」之后：是否做 Controller + 网页 API | 另 plan | 接受本地/中文弱于 Google |

建议下一句只回其中一句，例如：`Q-lock + Q0：同意` 或 `Q−：只 lock+T2，不烘焙`。

**我最推荐：`Q-lock + Q0`。** 两句硬约束里，「不得 `$19`」现在靠 Exa+T1 已经能挡住 **一发**；「答案接近官网」没有对照就无法执行 Q1。Q2 建议 Q0 看完再点，避免同一周又改引擎又改记账。

---

## 6. 落地时怎么动（确认后才执行）

共用：更新模型带 `access_grants`；Pipe **只 merge** valves；禁止空 `models/sync`；不改 `openai.api_configs` enable；不写新的非空 `WEBUI_SECRET_KEY`；现网禁止 F1/P2 debug marker。

### Q-lock

- `scripts/verify_text_web_search.py` / `verify_stack.py`：三家 `web_search.engine` 与 `web_fetch.engine` ∈ 可计数集合。  
- Filter 单测已有 Exa 断言，补 `auto`/`native` 为失败样例。  
- 文档：SPEC Don't + ST-15。

### Q0

- 新脚本（名待定）：对候选引擎发同一题库；写 `/opt/cursor/artifacts/search-metered-quality-q0.json`。  
- **禁止** 把烘焙配置 apply 进生产 Filter。  
- Gemini API 原厂对照若做：独立请求、Flash、短超时、总 `$` 计入 Q0 预算；跑完不留生产配置。

### Q1

- 只改薄 Filter 对不可计数类的 `engine`（及 mode/context）。content-only 或 Filter 更新 + 已有 apply 路径。  
- `verify_text_web_search --mode final`；中国三只若跟赢家则补烟雾。  
- 不改 Banner，除非文案仍暗示「原厂搜」（现网 v7 已是类描述，预计不动）。

### Q2

- Pipe content-only 记账：键为「当前用户消息」，内轮累加 Search/Fetch/`server_tool` `$`，超则停新工具。  
- T3：出站 prompt 将超阈值的旧工具页先走 T1 同类压缩。  
- 回滚：去掉 marker，回到 `9c4836ace251` 行为；Filter 引擎不动。

---

## 7. 明确不做

- 未确认改实例。  
- 生产原厂搜（三家）换「更像官网」。  
- 评测爬官网。  
- 用死 id 名单实现 Q-lock（按 **类**，与 C 档一致）。  
- 一次 Q0+Q1+Q2+Q3 绑死施工。  
- 把 Ling / Muse / GLM 顺便 public。  
- 把本波做成 Live / 图像 Studio / Notebook。

---

## 8. 验收（相应轮落地后）

1. **`$19` 复现门**：Astra Pro「你继续」不得再出现几十次搜 / 上百万 input。  
2. **回归锁**：人为把引擎改回 `native` 时 verify 红。  
3. **Q0 有数据**：至少 Exa 基线 vs 一个挑战者；中文 + 时效 + 误搜。  
4. **Q1 后**：默认搜仍开；误搜不升；Fetch HTML 仍能读。  
5. **Q2 后**：连点「继续」有累计顶，首轮调研不被掐死。  
6. **诚实口径**：生产检索 **不是** ChatGPT/Gemini/Grok **官网同栈**；接近的是 **答案**。未跑 Q0 不得写「已超过官网」。
