# 多模型对比为一等公民 — 方案（Plan only）

> **状态**：计划 **v2（已 review 修订）**，**确认前不改实例**  
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
| **S1** | `PERSIST_REASONING_TOKENS` → `disabled`（先 admin Valves，merge 写入） | **零代码** | 双栏两轮两图 **都 200**；单栏多轮仍正常 |
| **S2** | 若 S1 通过但不接受「丢掉自己上轮思考」：改回 `conversation` + **Pipe 补丁 D′** | 小补丁 | 同上，且 reasoning 仍回放给同模型 |
| **S3** | 若要求「Opus 只接自己的上轮」（真并行）→ 层 B，OWUI 侧 | 中补丁 | Opus 第二轮不复述 Grok 结论 |
| **S4** | 回归 + 写入 SPEC / VERSIONS | 文档 | `verify_stack` 全绿 + 对比回归 |

**S1 的代价要如实评估**：`disabled` 后模型看不到自己上一轮的思考链，长链推理可能略降；但 Sonar/图像本就不受影响，且对比场景收益（永不 404）很可能大于损失。**S1 用一次真实对话验完再决定去不去 S2。**

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

*确认本文件后，执行顺序：**S0 取证 → S1 valve → （必要时）S2 Pipe 补丁 → （仅要求真并行时）S3 OWUI → S4 回归**。*

**待你拍板的一点**：`PERSIST_REASONING_TOKENS=disabled` 会让模型看不到自己上一轮的 thought。若你认为这个代价可接受，S1 很可能就是终点（最简最稳）；若不可接受，则走 S2。
