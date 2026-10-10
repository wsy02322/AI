# 选择器换代时，薄搜索跟着公开文本走

> **状态**：已执行（2026-10-10）。公开文本三层已挂上，探针见 §6。未改 Pipe、未改过滤器代码、未改 Banner。  
> **日期**：2026-10-09 成稿，2026-10-10 执行  
> **原则来源**：ST-14 / C2 / W0–W6。见 `docs/open-webui-text-web-search-plan.md`、`docs/open-webui-search-quality-top-plan.md`。本文件不改那些决定。

---

## 0. 结论

Live picker 一更新，联网搜索会掉。挂载写在每一条模型行的 `filterIds` 上，新行不会从旧行把 Web Search 复制过来。

原则不变：公开文本挂薄过滤器 `openrouter_text_web_search`，新对话默认开；Sonar、图像、视频不挂。引擎仍按家族，不按冻住的版本号。

合适的处理是把「按当前公开文本重挂」收进选择器清理脚本本身，每次换代自动带上。过门要看到 Grok Latest 和 Sol Latest 真的搜到网址。

2026-10-09 曾把 `filter_ids` 写进请求去测三个 Latest，它们没有搜。这次测试不能说明别名坏了：可切换的过滤器只有先挂在模型行上，请求里的 `filter_ids` 才会生效。三条能搜的具体型号本来就挂着，三个 Latest 没挂，所以过滤器多半根本没跑。Pipe 改动只在「挂上之后仍不搜」时才考虑。

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

把过滤器写进请求后再测，三条具体型号仍会搜，三个 Latest 没有搜索事件。原因见 §0：Latest 行没挂过滤器，请求里的 `filter_ids` 不会让它生效。

宽的 `openrouter_web_tools` 与 Open WebUI 自带网页搜索仍关。

挂载有三层，换代时三层都会掉：

| 字段 | 作用 | Astra Pro / Qwen | GPT-6.1 Sol Pro | 各 Latest |
|------|------|------------------|-----------------|-----------|
| `filterIds` 含 `openrouter_text_web_search` | 模型可用搜索 | 有 | 有 | 无 |
| `defaultFilterIds` 含同一个 | 新对话默认开 | 有 | **无** | 无 |
| `toolIds` | 高德 / Google Routes / `x_recent_search` | 有 | **无** | 无 |

三样工具在 `/api/v1/tools/` 里都在（`amap_drive_route`、`google_drive_route`、`x_recent_search`），不是被删了，只是没挂到新行。GPT-6.1 Sol Pro 这一行是 2026-10-09 换代时只补了 `filterIds`，所以新对话里它的搜索默认是关的，路线和 X 工具也没有。

---

## 3. 两档

### 顶级（建议）

选择器脚本派生「当前公开文本」= KEEP 里去掉 Sonar 和图像，每次运行都对齐三层：`filterIds`、`defaultFilterIds` 加薄搜索，`toolIds` 加三样工具。保留每行已有的其他过滤器。Sonar 和图像若被带上则剥掉。以后型号换代不必另开一轮。

先挂一条 Grok Latest 做探针，过了再铺到其余公开文本。

引擎表不动：OpenAI / Google / xAI 仍是原厂；OpenAI 仍是 `max_tool_calls=3`；Anthropic 仍是 `auto`；DeepSeek、Kimi、Qwen 仍落到 Exa。Latest 的 id 里仍有 `openai.`、`google.`、`x-ai.`，分类对得上。

只有挂上之后 Latest 仍不发搜索，才看 Pipe：抓那条请求，判断是工具没注入，还是 400 后被 `SERVER_TOOL_FAIL_RETRY_V1` 剥掉工具重试，再做最小 content-only 改动。

### 更稳

只补搜索两层，不补工具。代价：Latest 和 Sol Pro 能搜网页，但中国路线、海外路线、X 帖子仍缺，和已过门的 W1 / W4 / W5 不一致。

---

## 4. 确认后的做法

1. 只给 Grok Latest 挂三层，用一条短问探针（过滤器已挂，请求带 `filter_ids`）。有搜索事件和 https 来源就继续；没有就停下，查 Pipe，不铺开。
2. 选择器脚本加「对齐公开文本挂载」一步，写三层，铺到 KEEP 的全部公开文本。改模型时带 `access_grants`；不删模型行，不做空的 `models/sync`，不全量覆盖 valves，不跑全量 catalog refresh。
3. 验收：
   - Grok Latest、Sol Latest 各一次短问，有搜索事件和一条 https 来源
   - GPT-6.1 Sol Pro 新对话默认开搜索（`defaultFilterIds` 含过滤器）且仍会搜
   - 一个图像模型（Nano Banana 2.1 或 Sunburst）没有搜索事件
   - Sonar Pro Search 仍能自己返回带来源的短答
   - 置顶、默认模型、Banner `usage-guide-v8`、Follow-up 关，都不改

---

## 5. 不做

- 重开 `openrouter_web_tools` 或 Open WebUI 自带网页搜索
- 把过滤器改成全局
- 改引擎（含把 OpenAI 改回 Exa）、抬 `$0.05`、做 W7 / Search Controller
- 用全量 catalog refresh 挂搜索
- 新建或改写高德、Google Routes、X 工具本身（只挂载，不动内容和钥匙）
- 未看到 Latest 的搜索事件就改首页文案

---

## 6. 执行记录（2026-10-10）

顶级档已落到实例。脚本是 `scripts/apply_confirmed_series_picker.py --align-text`：KEEP 里的公开文本写三层，Sonar 和图像只剥搜索与三样工具，图像过滤器原样保留。

`POST /api/v1/models/model/update` 只写数据库。聊天读内存里的模型表 `app.state.MODELS`。挂载之后用普通 `GET /api/models` 把数据库里的 `filterIds` 叠进这张表。`refresh=true` 仍不用，它会重新拉 Pipe 目录。选择器仍是 24，没有新 SKU 被打开。

Grok Latest 在缓存刷新前的短问没有搜索事件。刷新之后：

| 探针 | 结果 | 费用 |
|------|------|------|
| Grok Latest | 搜索事件，5 个站点，`https://finance.yahoo.com/quote/%5ESPX/`，收盘 7811.54 | $0.014 |
| Sol Latest | 搜索事件，收盘 7811.54，`https://www.wsj.com/market-data/quotes/index/SPX/historical-prices` | $0.067 |
| GPT-6.1 Sol Pro | `defaultFilterIds` 含过滤器，搜索事件，同一收盘 | $0.020 |
| Sunburst | 无搜索事件 | $0.018 |
| Sonar Pro Search | 自己的来源，`https://www.spglobal.com/spdji/en/indices/equity/sp-500/`，同一收盘 | $0.018 |

置顶仍是 Opus Latest、Sunburst、Sol Latest、Astra Latest。默认聊天和任务仍是 Grok Latest。Banner 仍是 `usage-guide-v8`。Follow-up 仍关。首页文案未改。
