# 多模型对比为一等公民 — 方案（Plan only）

> **状态**：计划，**确认前不改实例**  
> **日期**：2026-08-20  
> **产品定性**：对比是主干能力，不是单轮评测、也不是「选一个赢家继续」  
> **三条原则**：强能力（过复杂/极大不稳不强求）· 简单 · 稳定 · **不赶工期**

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
| B. 对比时关掉 Reasoning | 弱 | 简单 | 中 | **否**。砍掉你们已主打的 depth |
| C. 等 OWUI 合入 #28245 再升级 | 只修加密，不修并行语义 | 等别人 | 升级面大 | **否**作主路径；可作日后减补丁 |
| D. **请求时 Filter：按目标模型剥加密 + 丢掉他栏 assistant** | 保留 reasoning 与双栏多轮多图 | 一个 Filter，不 fork 全家桶 | 同模型不碰加密；可 verify | **主方案（先验证载荷形态）** |
| E. 补丁 OWUI `process_messages_with_output`（移植 #28245）+ 生成时按栏组 messages | 最贴内核 | 要维护补丁 | 与上游同思路 | **仅当 D 的 inlet 看不到完整分栏历史时升级** |
| F. 自研对比前端 / 第二套 Pipe | 过强 | 复杂 | 差 | **否** |

**不做：** 重开全局 Image Gen、Web Tools、为修对比换 Sol Pro 双默认。

---

## 4. 最优路径（不赶时间，按证据升级）

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

落点优先：**全局 Filter**（priority 靠后，在 Guard 剥 tools 之后或并列），不改 Pipe 全文、不 fork OWUI。

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

1. 先 Step 0 日志，再选 D 或 D+E，**禁止**未看载荷就改 OWUI 核心。  
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

*确认本文件后，执行顺序：Step 0 取证 → 层 A Filter →（仅必要时）层 B OWUI 小补丁 → 回归。*
