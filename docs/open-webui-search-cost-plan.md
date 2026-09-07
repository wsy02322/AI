# 搜索长对话费用护栏（保证顶级质量）

> **状态**：**未确认**。只分析和 plan，**不改**实例 / Pipe / Filter / Banner。  
> **触发**：对话 `https://micropigeon.com/c/23d8488c-be6a-4b77-8d86-6e63c61f8b66`（西北自驾游规划）单轮 UI **`$19.40707`**。  
> **现网**：OWUI 0.11.3；Pipe `f797e92d6d3f`；ST-14 薄 Filter 9 模型 default-on；阀门 `max_uses=3` / Fetch `5` / 每页 `12k` / `step_count=8` / `$0.05`。  
> **证据**：`/tmp/chat_23d8488c.json` → `/opt/cursor/artifacts/search-cost-northwest-drive.json`。

关联：`docs/open-webui-text-web-search-plan.md` §4；`docs/SPEC.md` ST-14；`docs/open-webui-text-web-search-eval-b-results.md`（质量已收口）。

---

## 0. 结论先看

**不是账单 bug。** 贵的是 **Astra Pro 单价 × 工具整页在上游会话里连滚 9 轮 ×「你继续」无界**，不是 Search 单击，也不是 OWUI 把 495 万 token 写进了聊天 JSON。

可见回复约 **5500 字**。同一条消息的上游 `prompt_tokens=4,947,410`。把路线往下写，不需要把 132 页整页再读一遍。

质量不能靠「关搜索 / 换弱模型」冒充。要降费且仍是顶级档，必须动 **工具结果怎么进下一轮上下文**，或至少给 **单次用户消息** 一个跨轮预算。只拧现网 `$0.05` / `max_uses` **挡不住**「继续」，还会伤 Grok / Sol / Claude 已收口的 EVAL-B 形态。

| 档 | 做什么 | 质量 | 改动 | 对这一轮的估效 |
|----|--------|------|------|----------------|
| **顶级 T** | 压缩旧 Search/Fetch 整页 + 单次用户消息跨轮预算 | 当前轮仍可读整页；旧页留标题/URL/摘录 | Pipe（须先看清回放形态） | 这一轮从 ~`$19` 收到约 **`$2–5`** 量级 |
| **略降级 S** | **只** Astra / Astra Pro 仍挂 Search、**新对话默认关**；另外 7 个不动 | 要路况再开；写作仍是旗舰 | 只改两个 Astra 的 `defaultFilterIds` + Banner 一句 | 挡住 Astra「随手开着搜、说继续」；不修 Sol/Grok 同类滚上下文 |

两档都提案。**未确认不施工。** T 覆盖全部 9 个 ST-14；S1 **只**关 Astra 一对的默认搜索，另外 7 个不要同样默认关。见 §2.6。

---

## 1. 这一轮的账单（只读）

聊天 id `23d8488c-be6a-4b77-8d86-6e63c61f8b66`。贵的那条：

| 项 | 值 |
|----|-----|
| 用户原话 | `需要我做什么吗？需要请说 不需要就你继续` |
| 消息 id | `f762df80-4a15-48ff-9821-b6f22ac35a61` |
| 模型 | `openai.gpt-6-astra-pro`（不是 Sol Pro） |
| UI | `Time: 1599.03s \| Cost $19.40707 \| Total tokens: 5025395`（Input `4947410`，Output `77985`，Cached `3843175`，Reasoning `56845`） |
| 上游 | `$19.26`（input `$15.36` + output `$3.90`） |
| 内部轮 | `turn_count=9` |
| 工具 | Search **46**；Fetch 状态 **132**；`tool_calls_executed=178` |
| 可见正文 | **5551** 字 |
| OWUI `sources` | 29 条，约 **21k** 字（不是 495 万的来源） |

按 OpenRouter 标价 Astra Pro **`$10 / $50` per 1M**、缓存读 **`$1` per 1M**、Search 约 **`$0.01`/次** 拆开，与上游对齐：

| 块 | Token / 次数 | 估算 |
|----|--------------|------|
| 未缓存 input | `1,104,235` | **`$11.04`** |
| 缓存 input | `3,843,175` | **`$3.84`**（缓存仍计费） |
| output | `77,985` | **`$3.90`** |
| Search 单击 | 46 × `$0.01` | **`$0.46`** |
| 合计 | | **`$19.24`** ≈ 上游 `$19.26` |

OpenRouter 字段 `cost=$99.21` 是 **9 轮内部请求的 list 加总**（`input_tokens` 合计 2530 万），**不是**用户付的。UI 认 `upstream_inference_cost`。

同一可见分支上，更早的 Astra Pro 已经：`$0.25` → `$1.69`（prompt 15 万）→ `$2.04`（26 万）→ `$2.08`（**30.8 万**）。「你继续」之前上下文已经很大；这一轮把它滚到 **495 万**。

同线 Astra Pro 上游合计约 **`$25`**（含本轮 `$19`）。前面还有对比/换模型分枝（Grok / Flash / Sol），不是本轮主因。

OpenAI 文档：input **超过 272k** 整单可按 input/cache **2×**、output **1.5×**。本轮账单按短档单价就能对上，**没有**吃到 2×。上一轮 prompt 已是 30.8 万，下一次若走这条规则会更贵。护栏仍应把 prompt **压回 272k 以下**，质量以外也挡费率悬崖。

---

## 2. 根因

### 2.1 贵的是模型 token，不是 Search 单击

46 次搜索约 **`$0.46`**。`$15.36` 是把旧工具结果 + 旧推理 **再送进 Astra Pro**。

### 2.2 `$0.05` / `step_count=8` 只管「这一次上游请求」

薄 Filter 每次 inlet 重写 `stop_server_tools_when`。多轮 agent **每轮清零**。9 轮 × `$0.05` ≈ 45 次搜索，与 **46** 次对得上。

这两道门：

- **不管** 模型 input/output token；
- **不删** 上一轮已经抓下来的整页；
- **不管** 用户有没有说「继续」。

把 `$0.05` 抬高会让单轮搜得更凶，账单更大。**不要**把它当总账单上限去调高（SPEC Don't 已写）。

### 2.3 495 万不在聊天 JSON 里

OWUI 存下来的 `sources` 只有约 21k 字。4.9M 在 **Pipe 回放给 OpenRouter 的 Responses / server-tool 副本**（整页 Fetch、多次 Search blob、reasoning）。只压缩 OWUI `sources` **省不了钱**。

现成 `middle-out` / `context-compression` 走 `/chat/completions` 图像/超长文本，**替代不了**「132 页整页重放」。

### 2.4 阀门是 9 模型共用一套

`WEB_SEARCH_MAX_USES` / Fetch / `step_count` / `$0.05` 是 Filter **全局阀门**。拧紧会同时打到 Grok / Sol / Claude / Gemini。EVAL-B 收口的是那套形态，不是 Astra 专用档。

`defaultFilterIds` **可以按模型关**（`attach_models(..., default_on=False)` 已支持）。这是略降级档能做、且不伤 EVAL-B 的原因。

### 2.5 「继续」在现网等于续约无限调研

用户原话没有新约束。模型选择：再核路况/假期/街区改造 → 再 Search → 再 Fetch → 再想。旗舰 + 无界工具，这是 ChatGPT 类产品会用 **压缩 + 预算** 接住的场景，不是用户用错。

### 2.6 其他模型要不要同样处理

**机制是 9 个 ST-14 模型共用的，钱不是均摊的。** 薄 Filter、`$0.05` 每轮清零、Pipe 回放整页，Grok / Sol / Claude / Gemini / Astra 走同一条路。EVAL-B 单题 p90 约 `$0.11`、max `$0.18`，那种短问不贵。会炸的是「搜过几轮 → 你继续」叠整页。

同一条西北自驾对话里，**只有 Astra Pro 滚到 495 万 / 9 轮 / 46 次搜索**。同线其他模型没有：

| 模型（本对话） | 最大 prompt | 最大内部轮 | 最大搜索 | 上游合计 |
|----------------|-------------|------------|----------|----------|
| Astra Pro | **4,947,410** | **9** | **46** | **`$25.31`**（5 条，含 `$19`） |
| Sol | 75,606 | 3 | 4 | `$1.05`（4 条） |
| Grok 4.6 | 81,847 | 2 | 10 | `$0.19`（1 条） |
| Gemini 3.8 Flash | 5,709 | 1 | 0 | `$0.02` |
| Sol Pro | （下一条空，未完成） | — | — | — |

所以：**行为上 Astra Pro 是现网唯一炸过的**；**架构上另外 8 个也能炸**，只是单价更低、或它们更少在「继续」里再开 9 轮新抓页。

把本轮 **同一 token 配比**（未缓存 110 万 + 缓存 384 万 + 输出 7.8 万 + 46 次搜索）套到 OpenRouter 标价，只换单价（缓存按各家列出的 cache read；Sol 用本对话实测约 `$2/$10`，与部分目录 `$5/$30` 不一致，以账单为准）：

| 模型 | 标价 in/out per 1M | 同一 4.9M 配比估 | 要不要 T1/T2 | 要不要 S1 默认关搜 |
|------|-------------------|------------------|--------------|-------------------|
| Astra Pro | `$10/$50` | **`$19`（已发生）** | 要 | **可以**（略降级档） |
| Astra | 同家族，略低或同档 | 同量级或一半 | 要 | **可以**（与 Pro 一起） |
| Fable 5.1 | `$10/$50`（cache 读 `$0.25`） | ~`$16` | 要 | **不要** |
| Opus 5 | `$5/$25` | ~`$10` | 要 | **不要** |
| Sol / Sol Pro | 本对话约 `$2/$10` | ~`$4` | 要 | **不要** |
| Grok 4.6 | `$2/$6` | ~`$5` | 要 | **不要** |
| Gemini 3.1 Pro | `$2/$12` | ~`$4` | 要 | **不要** |
| Gemini 3.8 Flash | 远低于上表 | 通常 `<$1` | 跟着做（Pipe 一层） | **不要** |

读法：

1. **顶级 T 做一次、覆盖全部 ST-14。** 压缩和跨轮预算在 Pipe 出站，不是 Astra 专用补丁。为 Astra 单独写一套、让 Opus/Fable/Sol 继续能滚 495 万，是假顶级。
2. **略降级 S1 只动 Astra 一对。** 另外 7 个保持 default-on。对 Grok/Sol/Claude/Gemini 默认关搜索，等于拆掉已收口的 ChatGPT 形态，省不了多少（它们短问本来就在 `$0.2` 内），质量代价大。
3. **不要**为另外 7 个单独拧全局阀门，也不要给它们各做一套 Filter。
4. **不在 ST-14 上的模型不用本护栏。** DeepSeek / Kimi / Qwen 现在不能搜，没有这条失败模式。Sonar 是自己的搜索计价，不是整页回放。图像 / 视频无此路径。

Grok 还有「总 token 超 200k 加价」档（OpenRouter 页）。即使单价是 Astra 的 1/5，整页滚起来仍会到数美元。T1 把 prompt 压回十万以内，对这些模型同样值。

---

## 3. 质量约束（降费时不能破）

1. **当前用户消息的第一轮调研** 仍要能 Search + 读整页。EVAL-B：隐含时效会搜、误搜≈0、普通 HTML 能读。不能为了省钱把首轮收成摘要注入。
2. **可见答案的信息密度** 不低于现在：路线取舍、可点来源、关键事实（假期、路况、街区是否过度旅游化）仍要有据。
3. **不**把弱模型、关搜索、Sonar 冒充旗舰写作，当终态。
4. **不**重开 broad Web Tools；**不**把 `$0.05` 当总账单上限抬高；**不**把 Search Controller（Fetch 失败改走 HTML）和本费用护栏绑成一波。
5. Filter 全局拧阀门，若当主方案，必须先承认会伤另外 7 个已收口模型。

「顶级」= 同一条「你继续」仍能写出同等或更好的行程，只是 **不再把旧整页当新上下文**。

---

## 4. 杠杆（顶级与略降级并列）

### T — 顶级（保质量，改 Pipe）

| ID | 动作 | 为什么这是顶级 | 风险 |
|----|------|----------------|------|
| **T0** | 只读：一条短 Search 续聊，看 Pipe 出门的是 `messages[]` 里的 tool 项、`previous_response_id`、还是 reasoning item | 不知道回放形态就压缩，会切错或无效 | 几分钱的探针；看完不留 marker |
| **T1** | 出站前把 **上一轮及更早** 的 `web_search` / `web_fetch` 压成标题 + URL + 一两句摘录；**本轮** Fetch 仍是整页 | ChatGPT 类做法；当前轮质量不变；旧页只留索引 | 须 content-only，不碰 valves / `API_KEY`；压太狠会丢数字 |
| **T2** | **单次用户消息** 累计 Search / Fetch / 工具 `$` / 可选 input token；内轮不重置 | 「继续」不能再买 9 × `$0.05` | 接近 Controller，要自己记账；须确认 |
| **T3** | 出站前若 prompt 将超过 **~200k**（低于 272k 悬崖），先跑 T1 | 挡费率 2×，也挡下一次 `$19` | 阈值要按实测，不能拍脑袋 |

T1 是主杠杆。没有 T1，只做 T2，模型仍会把已经在手里的 30 万旧页再读一遍。没有 T2，只做 T1，「继续」仍可能再开 9 轮新抓页，但每轮上下文会小一个数量级。

**估效（这一轮，不是承诺）：** 上一轮 prompt 30.8 万里，可见正文 + 用户约束大约 2 万字量级。若旧工具页压成摘录，单轮 prompt 可回到 **数万～十余万**。9 轮若再被 T2 收成 1～2 轮新搜，账单从 `$19` 落到 **`$2–5`** 是合理目标；首轮调研（EVAL-B 那种）应仍在现网 p90（约 `$0.11`）附近。

### S — 略降级（简单稳定很多）

| ID | 动作 | 为什么简单 | 质量代价 |
|----|------|------------|----------|
| **S1** | Astra、Astra Pro **仍 attach**，`defaultFilterIds` **去掉** Search；Grok/Sol/Claude/Gemini **不动** | 现成 `attach_models`；不改 Pipe；不拧全局阀门 | 新对话默认不搜。要现查路况须用户打开 Web Search。写作仍是旗舰 |
| **S2** | 全局下调 `max_uses` / Fetch / `step_count` | 改 Filter valves | **伤 EVAL-B**；且挡不住历史整页重放。不当主方案 |
| **S3** | Filter 按模型写更紧的 `stop_server_tools_when` / `max_content_tokens`（只打 Astra） | 中等；仍是 Filter | 首轮 Astra 调研变薄；不修跨轮重放 |
| **S4** | 用户话像「继续」且上下文已大 → 本轮剥 `server_tools` | 启发式，几十行 | 「继续核路况」会漏新事实；用户可再开搜索或改口 |
| **S5** | 只改 Banner / 用法：架构用 Astra Pro，展开用 Sol，继续时关掉 Search | 零工程 | 忘了就会再来一轮 `$19` |

S2 **单独不做**。S3 只在「确认不改 Pipe、又要留 Astra 默认开搜」时才有意义。

### 用法（零施工，现在就能做）

- 骨架 / 取舍：Astra Pro，**关掉** Web Search（Integrations）。
- 要现查：打开 Search，问具体问题，不要「你继续」。
- 展开已经搜过的路线：切 **Sol / Sol Pro**，或关 Search 再继续。
- 长报告：Sonar Deep Research，不要用聊天模型无限续搜。

这不替代 T/S；只避免下一轮在施工前再烧同样的钱。

---

## 5. 请选一档（确认前不动手）

**顶级（建议作主线）：T0 → T1 → T2**，T3 随 T1 一起做。对 **全部 9 个 ST-14** 生效，不是 Astra 专用。Astra 搜索保持 default-on。质量目标：同一条「你继续」仍能写完行程，只是不再把旧整页当新上下文。

**略降级、当天能落地：S1 + Banner 一句**（例如 v7：Astra 可搜，新对话默认关，要查再开）。**只关 Astra 一对的默认搜索**；Grok/Sol/Claude/Gemini 仍是 ChatGPT 那种默认会搜。不要把 S1 扩到另外 7 个。

**可以叠：** 先 S1 挡 Astra 误伤，再排 T0/T1。S1 不修 Sol/Grok 的同类滚上下文。

**不要选：** 只拧全局阀门（S2）；把 `$0.05` 抬高；为省钱把 Astra 换成弱模型当终态；未看清回放形态就盲改 Pipe。

本波 **不是** Search Controller（Fetch 失败改走 HTML / GitHub API）。那是 SPEC Later 另一条。T2 的跨轮预算若确认，记新 ST 号，**不要**写成 ST-11 / ST-12 / 复用 ST-14 当「已收口质量」的同义改写。

---

## 6. 落地波次（确认后才执行）

### 若选顶级 T

| 步 | 动作 | 过门 |
|----|------|------|
| **T0** | 只读短链：Flash 或 Sol 一条 Search，再一条「根据刚才的来源补一句」。导出 Pipe 出门 body 里 tool / fetch / reasoning 的形状与体积。**不**留 debug marker | 写清「压缩该切哪一层」；现网 sha 仍 `f797e92d6d3f` 或仅增加 **新的** 压缩 marker |
| **T1** | Pipe **content-only**：出站压缩旧 Search/Fetch；本轮整页保留。不碰 valves。单测用假 messages / 假 tool item | 续聊 prompt 相对未压缩明显下降；可见答案仍有来源；Sol 对照 Search+Fetch 烟雾仍绿 |
| **T2** | 单次用户消息累计 Search/Fetch/工具 `$`（建议仍 `$0.05` 总量，或 Search 次数封顶）。内轮不重置 | 「继续」类不再出现 9 轮 × 40+ 次搜索 |
| **T3** | 与 T1 同补丁：将超 ~200k 的旧工具页先压再送 | 出站 prompt 稳定低于 272k |
| **验** | `verify_stack`；`verify_text_web_search --mode final`；一条复现「短搜 → 继续」的费用探针（记 token，不追求再烧 `$19`） | 契约 9 模型、Banner、三 Guard 不变 |

回滚：Pipe 去掉压缩 marker，回到 `f797e92d6d3f` 行为；Filter / 挂载不动。

### 若选略降级 S1

| 步 | 动作 | 过门 |
|----|------|------|
| **S1a** | `attach_models`：9 个仍在 `filterIds`；Astra / Astra Pro **不**进 `defaultFilterIds`；`GET /api/models?refresh=true` | 新对话 Astra 默认无 Search toggle；用户可开；另外 7 个仍 default-on |
| **S1b** | Banner → `usage-guide-v7`（第一句写清 Astra 默认可关） | `verify_stack` 绿 |
| **验** | `verify_text_web_search --mode final` 按「7 default-on + 2 attached」改断言，或新模式，**不要**假绿 | 契约写清，勿再写死「9 个全部 default-on」 |

回滚：两个 Astra 加回 `defaultFilterIds` + refresh；Banner 回 v6。

### 共用

- 更新模型必须带 `access_grants`。
- Pipe **只 merge** valves；禁止空 `models/sync`。
- 不改 `openai.api_configs` enable；不写新的非空 `WEBUI_SECRET_KEY`。
- 现网禁止留下 F1/P2 debug marker。

---

## 7. 明确不做（本 plan 范围）

- 未确认改实例 / Pipe / Filter / Banner。
- 为省钱上弱模型、关 ST-14、或用 Sonar 冒充旗舰写作终态。
- 全局拧 `max_uses` / Fetch / `step_count` 当唯一方案。
- 把 `$0.05` 抬高，或把它解释成「整段对话最多 5 美分」。
- 重开 `openrouter_web_tools` / OWUI native Web Search。
- 把本波做成 Search Controller、Image Studio、Live、Notebook 的绑车施工。
- 只压缩 OWUI `sources` 却宣称已省 token。
- 未看清 T0 回放形态就改 Pipe 业务门。

---

## 8. 纸面债（本波可顺手，须点头）

SPEC **UX-3** 仍写「指定 7 个文本」；现网 ST-14 已是 **9** 个。与费用无关，改契约时不要再写成 7。不在未确认的费用波里偷偷改 Banner / public。

---

## 9. 验收（确认并落地后）

说服人的标准：

1. **复现对照**：同类「搜过几轮 → 你继续」的 prompt，压缩后比压缩前 **少一个数量级**，或跨轮工具次数被封顶；可见答案仍有可点来源和关键事实。
2. **EVAL-B 形态不回退**：Grok/Sol/Claude/Gemini 隐含时效仍会搜、误搜仍≈0（S1 不碰这 7 个；T 须跑现有 Search+Fetch 烟雾）。
3. **272k**：出站 prompt 不再长期停在 30 万以上还继续叠整页。
4. **现网契约**：23 public、三 Guard、Pipe 无旧 debug marker、`verify_stack` 绿。
