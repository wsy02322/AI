# 多模型对比为一等公民 — 方案（Plan only）

> **状态**：S2′ **已落地（retry-only）**；S1 全局 `disabled` 不作终态；**S3（真并行分栏）未做，需另确认**  
> **日期**：2026-08-20  
> **产品定性**：对比是主干能力，不是单轮评测、也不是「选一个赢家继续」  
> **三条原则**：强能力（过复杂/极大不稳不强求）· 简单 · 稳定 · **不赶工期**

---

## 0. Review 修订（v1 → v2，只读取证后）

对 Pipe 源码做了 **只读** 检查（2623658 字符），v1 有三处判断需要更正：

| v1 说法 | 更正 |
|---------|------|
| 层 A 落点「**全局 Filter** 改 `body["messages"]`」 | **错位**。我们的请求经 **Pipe** 发出（截图报错卡片、`pinned_endpoint_slug`、`middle-out` 提示都是 Pipe 自己渲染的）。Pipe 走 `/responses` 时会 **自行重建** `body.input` 的 `type=="reasoning"` 项；改 `messages` 的 Filter 未必能决定最终载荷。**落点应在 Pipe** |
| 「OWUI 无条件回放，需要我们从零写剥离逻辑」 | Pipe **已有**机器：`_strip_replayed_reasoning()`（剥 `type=="reasoning"` 与 `reasoning_details`）+ `_sanitize_request_input()` + 失败重试钩子。**缺的是触发条件与跨模型规则**，不是缺能力 |
| 未提到「零代码开关」 | **漏了最简杠杆**：Pipe valve `PERSIST_REASONING_TOKENS`（admin Valves 与 UserValves 都有），默认 **`conversation`**；代码 `should_persist = valves.PERSIST_REASONING_TOKENS in {"next_reply","conversation"}`。设为 **`disabled`** 即不再回放 reasoning → 跨模型 404 从源头消失，**零代码** |

### 为什么这次 404 没有自动恢复

Pipe 的重试门 `_should_retry_dropping_signed_reasoning()` 只在错误里出现 **Anthropic 的 signature/thinking 字样** 时才触发；我们的报错是

> encrypted reasoning or compaction content that was produced under a **different model**

Pipe 源码里 `"produced under"` / `"compaction"` / `"encrypted payloads"` 命中数 **均为 0** → 门不开 → 不重试 → 永久失败（与截图「重试仍失败」一致）。

### 一个 v1 没看到的硬约束

Pipe 里 `msg.get("model")` / `item.get("model")` / `_source_model` 命中 **均为 0**：Pipe **没有** per-message「产生模型」信息。所以 **不能** 原样照搬 OWUI [#28245](https://github.com/open-webui/open-webui/pull/28245) 的「目标模型 ≠ 产生模型才剥」精确规则；在 Pipe 内只能做 **更粗** 的判断（例如：本次请求链之外的 encrypted 一律剥，或仅在会话含多模型时剥）。要做精确规则就得回到 OWUI 侧（层 B 同一处），复杂度上升。

### 仍然成立的部分

- 目标体验（§1）、OpenRouter 硬约束（§2.1）、对比语义缺口（§2.2 的 [#14531](https://github.com/open-webui/open-webui/issues/14531)）  
- **只剥加密 ≠ 一等公民**：404 会消失，但 Opus 可能接着 Grok 的结论 → 仍需层 B 判断  
- 不做清单（§7）、Step 0 先取证、回归口径（§4 Step 3）

**修订后的阶梯见 §4-v2。**

---

## 1. 目标体验（必须能做到）

同一对话、**同一组模型**（默认 Grok 4.6 + Opus 5）：

1. 第 1 轮：共享用户问题 + 图 1 → 两栏各自作答（已能）  
2. 第 2 轮：**不换模型、不新开 chat**，再附图 2 / 追问 → **两栏都成功**，且各自基于 **自己的上一轮回答** + 共享新用户消息  
3. Reasoning depth 可开（难题仍要 thought）  
4. 第 N 轮同样成立  

**正确载荷（发给模型 X）：**

```
U1（文+图1） → A1_X（仅 X 的回复 + 仅 X 的 encrypted reasoning）
U2（文+图2） → 请求 X
```

**禁止：** 把 Grok 的 `reasoning.encrypted` / compaction / `pinned_endpoint_slug` 发给 Opus（OpenRouter 404，正是截图错误）。

---

## 2. 根因（两层叠在一起）

### 2.1 OpenRouter 硬约束（不是我们配错）

加密 reasoning / compaction **绑定产生它的端点**。回放给另一模型 → 404：

> encrypted reasoning or compaction content that was produced under a different model

官方建议（与 Codex/OWUI 讨论一致）：**目标模型 ≠ 产生模型时，丢掉 `reasoning.encrypted` 和带 `signature` 的项，保留 `summary`/`text`。同模型必须原样回放**（Anthropic 第二轮缺 signature 会挂，见 OWUI #27467）。

### 2.2 OWUI 0.11.0 行为

| 点 | 事实 |
|----|------|
| 无条件回放 `reasoning_details` | `convert_output_to_messages(..., raw=True)`，**不管**目标模型是谁（[#28240](https://github.com/open-webui/open-webui/issues/28240)，**就在 v0.11.0**） |
| 上游修复 PR | [#28245](https://github.com/open-webui/open-webui/pull/28245)：**仍 open，未进发行版**。不要等合入当主路径 |
| 多模型「继续聊」官方语义 | [#14531](https://github.com/open-webui/open-webui/issues/14531) 维护者：**点选一栏，从该栏历史继续**。高亮极弱，用户以为是双线程并行 |

截图第二轮 Opus 失败，且 JSON 里 `pinned_endpoint_slug` 指向 **Grok**：符合「选中/混入了 Grok 栏历史 → 整包发给 Opus」。

因此：

- **只剥加密** → 404 可能消失，但 Opus 仍可能接着 **Grok 的结论** 往下聊 → **对比被污染**（不够「一等公民」）  
- **一等公民** = **按栏隔离 assistant 历史** + **跨模型剥加密**

---

## 3. 用三条原则筛方案

| 方案 | 强 | 简单 | 稳定 | 判定 |
|------|----|------|------|------|
| A. 劝用户单栏 / 新对话 / 对比只能一轮 | 弱 | 假简单 | 靠回避 | **否**。与「对比是一等公民」冲突 |
| B. 对比时关掉 Reasoning（UI 层劝导） | 弱 | 简单 | 中 | **否**。砍掉已主打的 depth |
| **V. valve `PERSIST_REASONING_TOKENS=disabled`** | 失去「模型看到自己上轮思考」；答案质量影响待测 | **最简，零代码，可秒回滚** | 从源头消灭跨模型加密回放 | **v2 首选先测** |
| C. 等 OWUI 合入 #28245 再升级 | 只修加密，不修并行语义 | 等别人 | 升级面大 | **否**作主路径；可作日后减补丁 |
| D′. **Pipe 补丁**：重试门加「different model / encrypted」短语 + `_sanitize_request_input` 加粗粒度剥离 | 保住 reasoning 与双栏多轮多图 | 改动集中在 Pipe 既有函数 | 复用 Pipe 已验证的 strip 路径 | **V 不可接受时的主方案** |
| ~~D. 全局 Filter 改 `messages`~~ | — | — | — | **撤销**（§0：Pipe 自行重建 `/responses input`） |
| E. OWUI 侧补丁（移植 #28245 精确规则 + 按栏组 messages） | 最贴内核、可做真并行 | 要维护补丁 | 与上游同思路 | **仅层 B 需要时** |
| F. 自研对比前端 / 第二套 Pipe | 过强 | 复杂 | 差 | **否** |

**不做：** 重开全局 Image Gen、Web Tools、为修对比换 Sol Pro 双默认。

**附加稳定项（可选）**：OpenRouter 侧 **同模型** 也可能因上游 provider 切换而失效（[ai-sdk-provider#491](https://github.com/OpenRouterTeam/ai-sdk-provider/issues/491)）。Pipe 已有 `allow_fallbacks` / `order`；多轮 reasoning 会话可考虑 **pin provider**。

---

## 4-v2. 最优路径（由简到繁，按证据升级）

**总原则**：先用 **valve** 试（零代码），再考虑 **Pipe 补丁**，最后才碰 **OWUI**。每步都能独立回滚。

| 步 | 动作 | 类型 | 通过判据 |
|----|------|------|----------|
| **S0** | 复现 + 取证（下方 Step 0） | 只读 | 看清 Opus 请求里到底带了什么 |
| **S1** | `PERSIST_REASONING_TOKENS` → `disabled`（**仅作临时验证**，证明根因） | **零代码** | 双栏两轮两图 **都 200**；单栏多轮仍正常 |
| **S2′** | `conversation` 保持 + **Pipe 补丁（retry-only）**：400/404 跨模型密文拒绝时剥密文内部重试 | 小补丁 | 双栏两轮两图都 200，且**单模型对话零影响** |
| **S3** | 若要求「Opus 只接自己的上轮」（真并行）→ 层 B，OWUI 侧 | 中补丁 | Opus 第二轮不复述 Grok 结论 |
| **S4** | 回归 + 写入 SPEC / VERSIONS | 文档 | `verify_stack` 全绿 + 对比回归 |

**S1 只是探针，不是终点**：`disabled` 是 **全局** 收税（连单模型长对话也失去自己上轮思考的复用），而 bug 只在对比场景。用它先证明根因，随后回到 `conversation` 并走 **S2′**（作用域收窄）。质量对照见 **§4b**。

### Step 0 — 一次取证（执行时先做，改代码前）

对 **Grok+Opus、两轮两图** 抓发给 OpenRouter 的 `messages`（可临时 Filter 打日志，验完删）：

要回答：

1. 发给 Opus 的历史里有没有 Grok 的 `reasoning.encrypted` / signature？  
2. 有没有 Grok 的 **正文** assistant？  
3. 用户第二张图是否在 user 消息里（应保留）？  
4. 每条 assistant 是否带 `model` 字段？

**分支：**

- 历史里已有两栏 assistant → **只做 D（Filter）**  
- 只有「当前选中栏」一条 assistant 链 → Filter 剥加密只能止 404 → **必须 E**，让「生成 Opus」时用 Opus 自己的树  

### Step 1 — 层 A（必做）：跨模型剥加密 reasoning

与 #28245 同一规则，**请求时过滤、不改 DB**：

- 若 `assistant.model` ≠ 当前请求 `model`：从 `reasoning_details` 去掉 `type == reasoning.encrypted` 及带 `signature` 的项；**保留** `reasoning.summary` / `reasoning.text`  
- 若相等：**整段回放**（Claude 第二轮需要）  
- 无 `model` 的旧消息：保守剥 encrypted（避免 404）；同模型续聊优先有 model 字段的新消息  

**落点（v2 更正）**：**Pipe 内**——扩 `_should_retry_dropping_signed_reasoning()` 的触发短语（加 `different model` / `encrypted reasoning` / `compaction`），复用既有 `_strip_replayed_reasoning()`；必要时在 `_sanitize_request_input()` 加粗粒度剥离。**不**新写全局 Filter 改 `messages`，**不** fork OWUI。

⚠️ 受 §0 限制：Pipe 无 per-message 产生模型，**做不到** #28245 的精确「≠ 才剥」；粗粒度剥离会让 **同模型** 也可能丢一部分回放（Anthropic 同模型续聊需 signature，须重点回归）。

### Step 2 — 层 B（一等公民）：按栏隔离 assistant

发给模型 X 时：

- **保留** 全部 user（含多图）  
- **只保留** `model == X` 的 assistant  
- 不把 Opus 的回答喂给 Grok，反之亦然  

若 Step 0 证明 inlet `body.messages` 已含分栏 → **仍在同一 Filter 做**。  
若只有选中枝 → **小补丁 OWUI**（组 messages 的那一处），体积对标 #28245（约几十行），用 volume / 启动补丁，**禁止**整仓 fork。

### Step 3 — 验收（对比回归进 `verify_stack` 或独立脚本）

手工 + 尽量 API：

1. 新对话默认双模型 Grok+Opus  
2. U1：图 1 + 真皮问题 → 两栏 200  
3. U2：图 2 + 追问 → **两栏 200**，无 encrypted 404  
4. 抽日志：Opus 请求 **无** Grok encrypted；Grok 请求 **无** Opus signature  
5. 抽内容：Opus 第二轮应接 **自己的** 第一轮谨慎结论，而不是复述 Grok「就是头层皮」  
6. 单栏 Sol Pro 多轮 reasoning **仍成功**（证明没误剥同模型加密）  
7. 现有 `verify_stack` 四格 / Sonar / 方案 A **仍全绿**

失败则回滚 Filter，不留半残补丁。

---

## 4b. 质量影响评估（对照「媲美甚至超越 ChatGPT」）

### 先分清三件不同的事

| 概念 | 谁控制 | 本方案是否触及 |
|------|--------|----------------|
| **本轮思考深度**（Reasoning depth / effort） | `REASONING_EFFORT` / UserValves | **完全不触及**。high/xhigh 仍是 high/xhigh |
| **跨轮复用自己上一轮的隐藏思考** | `PERSIST_REASONING_TOKENS` | S1 会关掉 |
| **把 A 模型的思考喂给 B 模型** | 剥离规则 | 这是 404 的来源，本就该切断 |

代码确认：`should_persist = valves.PERSIST_REASONING_TOKENS in {"next_reply","conversation"}` 位于 `response.output_item.done` 的 **持久化** 分支 —— 它决定「这轮思考是否留给以后回放」，**不改变本轮思考预算**。

### 两个选项的代价

| 选项 | 丢什么 | 何时才会感觉到 | 影响范围 |
|------|--------|----------------|----------|
| **剥 `reasoning.encrypted` + signature，保 summary/text（跨模型）** | 只丢**不可回放的密文**；对方仍能读到 **人类可读摘要** | 几乎无感；跨模型本来也不该共享密文 | **仅跨模型** |
| **`PERSIST_REASONING_TOKENS=disabled`** | 模型看不到**自己**上一轮的隐藏思考，需从可见对话重新推理 | 长链推理 / agentic 多步；思考 token 可能变多（略慢略贵） | **全局**：所有模型、所有对话，**含单模型** |

**关键不对称**：bug 只发生在 **对比（多模型）** 场景，而 `disabled` 是 **全局收税**。用它当终点，等于为修一个场景牺牲所有单模型长对话的复用 —— 与「媲美甚至超越」相悖。

### 唯一真正会伤质量/正确性的做法（必须避免）

**在同一轮内**（tool-call 循环中）剥掉 signature / thinking：Anthropic 要求整轮 reasoning 原样回放，Gemini 的 thought signature 在工具步之间必须保留（见 OWUI [#19328](https://github.com/open-webui/open-webui/issues/19328)、[#27467](https://github.com/open-webui/open-webui/issues/27467)）。

→ 剥离**只能**作用于 **跨轮 + 跨模型**，**绝不**在同轮工具链里动。这是 S2 的硬约束。

### 结论：推荐 S2′（作用域收窄），而非全局 disabled

| | 质量 | 简单 | 稳定 |
|--|------|------|------|
| S1 全局 `disabled` | 全局略降 | 最简 | 稳 |
| **S2′ 仅在「本对话含多个模型」时剥跨模型密文** | **单模型 0 损失**；对比场景仅丢密文 | 中 | 稳 |
| S3 OWUI 精确「≠ 才剥」 | 最优 | 最复杂 | 需维护补丁 |

Pipe 有 `__metadata__`（95 处命中），**若**其中能拿到本对话的模型列表 → S2′ 可行，即 **单模型对话完全不受影响**。这应作为落地目标；`disabled` 仅作 **S0/S1 阶段的临时验证开关**，不当终态。

---

## 5. 给执行 Agent（本仓库后续 / VPS）的约束

1. 顺序 **S0 → S1（valve）→ S2（Pipe）→ S3（OWUI）**，**禁止**跳过 valve 直接写补丁，**禁止**未看载荷就改 OWUI 核心。  
2. Valves **merge**；密钥不入库。  
3. 用户文案：对比多轮 **不要**写成「请新开对话」；最多英文一句 *Each column continues from its own replies.*  
4. 改完更新 `docs/SPEC.md`：对比 = 并行分栏历史 + ST 增加「跨模型不得发送 encrypted reasoning」。  
5. `docs/VERSIONS.md` 记补丁指纹；OWUI 以后升级时 **diff #28245**，上游已含层 A 则删我们重复 Filter，**层 B 另验**。

---

## 6. 成功标准（产品）

- 默认双栏、连续两张图、不换模型、Reasoning 可开 → **两栏都出回答**  
- 对比语义 = **双线程**，不是「选 Grok 当唯一上文」  
- 无新 tool 路径、无全局 Image Gen、19 public / 方案 A 不变  

---

## 7. 明确推迟

- 等官方合入再升级当唯一手段  
- 对比模式强制 Reasoning=none  
- Comfy / 第二套对比产品  
- 为对比去动图像连续性 Pipe 大补丁  

---

*确认本文件后，执行顺序：**S0 取证 → S1 valve（探针，已跳过现场）→ S2′ Pipe 补丁（已落地）→ （仅要求真并行时）S3 OWUI → S4 回归**。*

**已拍板**：S1 不作终态；S2′ 落地为 **retry-only**（见下）。**S3（OWUI 真并行）仍需另确认**，本步不做。

### S2′ 落地细化（相对「多模型就先剥」）

Pipe **没有** per-message 产生模型。若「本对话含多个模型就先剥」，对比里 **Grok 续聊也会丢掉自己的密文**（OpenRouter 本会接受）。这违反「强能力」。

因此落地是扩 `_should_retry_dropping_signed_reasoning()`：

- 状态 **400 或 404**（流式包装可能把 HTTP 404 报成 400）
- 错误文本含 `produced under a different model` / `encrypted reasoning` / `compaction content`
- 复用已有 `_strip_replayed_reasoning()`，内部再发一次；用户只应感到略慢，不应再看到永久 404 卡

同模型续聊：OpenRouter 接受密文 → 门不开 → persist 原样。标记：`COMPARE_CROSS_MODEL_REASONING_V1`。脚本：`scripts/patch_pipe_cross_model_reasoning.py`（content-only）。验收：`scripts/verify_compare_cross_model.py`。
