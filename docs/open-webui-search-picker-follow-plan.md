# 选择器换代时，薄搜索跟着公开文本走

> **状态**：计划。未确认不改实例、不改 Pipe、不改过滤器。  
> **日期**：2026-10-09  
> **原则来源**：ST-14 / C2 / W0–W6。见 `docs/open-webui-text-web-search-plan.md`、`docs/open-webui-search-quality-top-plan.md`。本文件不改那些决定。

---

## 0. 结论

Live picker 一更新，联网搜索会掉。挂载写在每一条模型行的 `filterIds` 上，新行不会从旧行把 Web Search 复制过来。

原则不变：公开文本挂薄过滤器 `openrouter_text_web_search`，新对话默认开；Sonar、图像、视频不挂。引擎仍按家族，不按冻住的版本号。

合适的处理是把「按当前公开文本重挂」收进同一次选择器清理。只把勾补上还不够：2026-10-09 把过滤器强行加到三个 Latest 上，它们没有发出搜索。过门要看到 Grok Latest 和 Sol Latest 真的搜到网址。

---

## 1. 为什么受 picker 影响

过滤器入口已是排除类（Sonar / `image_output` / `video_generation`），不再读一份冻住的 allowlist。谁能搜，由模型行是否挂着这个非全局过滤器决定。

目录刷新或换成 `~…-latest` 时，新行通常只有 `openrouter_direct_uploads`。旧快照上的 `openrouter_text_web_search` 留在已关掉的 id 上。

重放脚本如果仍用 `stack_contract.py` 里过期的 `PUBLIC_MODEL_IDS`，会把搜索挂回已经不公开的快照，并漏掉 Latest。

不跑 `GET /api/models?refresh=true` 来「顺便」挂搜索。那个入口会把刚关掉的新型号重新启用。

---

## 2. 现网（2026-10-09，选择器 24）

已挂上，且带过滤器的短问能搜到同一标普收盘 7765.36：

- `openai.gpt-6.1-sol-pro`
- `openai.gpt-6-astra-pro`
- `qwen.qwen3.8-max-0902`

公开文本但未挂：

- `~x-ai.grok-latest`（默认聊天和任务）
- `~openai.gpt-sol-latest`（置顶）
- `~openai.gpt-astra-latest`（置顶）
- `~anthropic.claude-opus-latest`（置顶）
- `~anthropic.claude-fable-latest`
- `~google.gemini-pro-latest`
- `~google.gemini-flash-latest`
- `~deepseek.deepseek-pro-latest`
- `~moonshotai.kimi-latest`

Sonar 两档和全部图像模型未挂。这是对的。Sonar Pro Search 自己返回了同一个收盘数字。

把过滤器写进请求后再测，三条具体型号仍会搜。三个 Latest 没有搜索事件：

- Grok Latest 只说要去查，没有数字
- Sol Latest 表示不能联网
- Gemini Pro Latest 没有搜索记录，并给出和 7765.36 对不上的数字

宽的 `openrouter_web_tools` 与 Open WebUI 自带网页搜索仍关。

现网 Function 列表里没有高德、Google Routes、`x_recent_search`。它们和搜索是同一挂载面，但本计划不把那三样一起施工。

---

## 3. 两档

### 顶级（建议）

选择器清理派生「当前公开文本」= 保持公开的行，去掉 Sonar 和图像。给这些行挂上薄搜索并默认开。已经挂对的三条不动引擎。

Latest 若仍发不出搜索，在 Pipe 里让 `~…-latest` 的 Search 与 Fetch 和同家族具体型号一样送到 OpenRouter。不改引擎表：OpenAI / Google / xAI 仍是原厂；OpenAI 仍是 `max_tool_calls=3`；Anthropic 仍是 `auto`；DeepSeek、Kimi、Qwen 仍落到 Exa。

不做完探针就当默认 Grok 已能搜。

### 更稳、先停住

只保证三条已经能搜的具体型号继续挂着。Latest 维持不搜，直到别名路径有一条带网址的成功记录。

代价：新对话默认的 Grok Latest，以及置顶的 Sol Latest，和首页「文本模型可以联网」不一致。这是临时状态，不是新的产品决定。

---

## 4. 确认后的做法

1. 用一条 Grok Latest 请求抓失败形态：工具有没有注入，OpenRouter 是否 400 后被 `SERVER_TOOL_FAIL_RETRY_V1` 剥掉工具再重试。先看这一条，再改 Pipe。
2. 在选择器脚本里用当前 KEEP 派生公开文本，写入 `filterIds`（保留该行已有的 Direct Uploads 等），`defaultFilterIds` 含 `openrouter_text_web_search`。Sonar 和图像若被带上则剥掉。不删模型行，不做空的 `models/sync`，不全量覆盖 valves。
3. 别名探针失败时，只做让 Latest 走通 Search+Fetch 的最小 Pipe 改动。content-only，不碰阀门。
4. 验收：
   - Grok Latest、Sol Latest 各一次短问，有搜索事件和一条 https 来源
   - GPT-6.1 Sol Pro 仍会搜
   - 一个图像模型（Nano Banana 2.1 或 Sunburst）没有搜索事件
   - Sonar Pro Search 仍能自己返回带来源的短答
   - 置顶、默认模型、Banner `usage-guide-v8`、Follow-up 关，都不改

---

## 5. 不做

- 重开 `openrouter_web_tools` 或 Open WebUI 自带网页搜索
- 把过滤器改成全局
- 改引擎（含把 OpenAI 改回 Exa）、抬 `$0.05`、做 W7 / Search Controller
- 用全量 catalog refresh 挂搜索
- 本轮顺手补高德、Google Routes、X 工具
- 未看到 Latest 的搜索事件就改首页文案
