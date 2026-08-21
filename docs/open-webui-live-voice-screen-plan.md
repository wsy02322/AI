# Live 语音 · 摄像头 · 屏幕共享 — 方案（Plan only）

> **状态**：计划 v1，**确认前不改实例**  
> **日期**：2026-08-21  
> **优先级**：**屏幕共享首要** → 实时语音 → 摄像头；对标 OpenAI GPT Live / Google Gemini Live / xAI Grok Voice **官网最高体验**  
> **三条根本要求**：媲美甚至超越 · 简单 · 稳定 · **冲最高性能若带来极大不稳须先确认**

---

## 0. 你要的「最顶级」到底是什么

官网 Live 不是「能说话」这么简单，而是 **四条同时成立**：

| 维度 | GPT Live / Gemini Live / Grok Voice 官网档 |
|------|---------------------------------------------|
| **延迟** | 亚秒级往返；可打断（barge-in） |
| **音频** | **Speech-to-Speech**（模型直接听/说），不是「先转文字再念」 |
| **屏幕** | 共享画面持续进模型（Gemini ~1fps；GPT 多模态会话内视频） |
| **摄像头** | 与麦克风同级，实时帧进会话 |

这和 **普通聊天 + Whisper + TTS** 是不同架构。

---

## 1. 我们现在的栈（micropigeon.com 探针 2026-08-21）

| 项 | 现状 |
|----|------|
| OWUI | **0.11.0** |
| 聊天主干 | OpenRouter **Pipe**（文本/推理/对比） |
| 语音链路 | **串联**：STT → 选中模型 → TTS（**不是** Realtime S2S） |
| STT | `openai` → OpenRouter，`openai/whisper-large-v3-turbo` |
| TTS | `openai` → OpenRouter，`openai/tts-1`，voice `alloy`，`SPLIT_ON=punctuation` |
| OWUI 内置 | Call overlay：**语音 / 视频 / 屏幕共享 / 多模态输入**（官方文档与 0.11 发行说明） |
| `enable_websocket` | **true** |
| 模型目录 | **当前异常：`/api/v1/models` len=0**（Pipe active 但 catalog 空）→ **Live 前置阻塞** |

结论：**屏幕共享 UI 能力在 OWUI 里已有**；但要想「像官网 Live」，要么把 L1 串联链路调到最好，要么上 **Realtime / Live API**（L2+），不能指望 Pipe 文本路径 alone。

---

## 2. 竞品能力对照（规划基准）

| 能力 | OpenAI GPT Live | Google Gemini Live | xAI Grok Voice | 我们 L1（OWUI 串联） | 我们 L2+（Realtime） |
|------|-----------------|--------------------|----------------|----------------------|---------------------|
| 实时 S2S | ✅ Realtime API WebRTC | ✅ Live API WSS | ✅ `wss://api.x.ai/v1/realtime` | ❌ STT→LLM→TTS | ✅ 需直连或兼容层 |
| 屏幕共享 | ✅ 会话内多模态 | ✅ **原生** ~1fps JPEG | ⚠️ **无原生**；需混合架构 | ⚠️ 帧进 **vision 聊天模型** | ✅ Gemini/OpenAI 原生；Grok 需混合 |
| 摄像头 | ✅ | ✅ | 语音为主 | ✅ OWUI overlay | ✅ |
| 打断 / barge-in | ✅ | ✅ | ✅ | ⚠️ 弱于官网 | ✅ |
| 走 OpenRouter Pipe | — | — | — | ✅ 文本模型可选 | ⚠️ Realtime **一般不经过** Pipe |
| 简单稳定 | 中（多密钥） | 中 | 中 | **高** | 低～中 |

**「媲美甚至超越」的现实拆解：**

- **L1** 可做到：**稳定可用的屏幕共享助教**（能看屏、能说话、能追问），但 **延迟与打断感** 通常仍弱于官网 Live。  
- **真·官网同级** 需要 **L2 或 L3**（Realtime/Live API），复杂度与运维明显上升 → **确认门**。

---

## 3. 架构选项（用三条要求筛）

| 路径 | 做什么 | 强 | 简单 | 稳定 | 判定 |
|------|--------|----|------|------|------|
| **L0** | 修 catalog、权限、STT/TTS 烟测 | 前提 | 高 | 高 | **必须先做** |
| **L1** | OWUI 原生 Voice/Video：屏享+摄像+串联 STT/TTS + **vision 模型** | 中（非 S2S 顶级） | **最高** | **高** | **默认第一站** |
| **L2** | **rbb-dev/open-webui-realtime** 容器（与 Pipe 同作者生态） | 高（OpenAI Realtime 形态） | 中 | 中 | **候选**；换镜像/双栈 → **须确认** |
| **L3a** | 旁路 **Gemini Live**（屏+音一体最好） | **屏享最强** | 低 | 中 | **须确认** Google 密钥 + 中继 |
| **L3b** | 旁路 **OpenAI Realtime** | GPT Live 最贴 | 低 | 中 | **须确认** OpenAI 密钥 |
| **L3c** | **Grok Voice S2S** + 屏享帧旁路喂 **Grok 4.6 vision** | 语音顶级；屏享为混合 | 低 | 中 | **须确认** 双通道工程 |
| **L4** | 自研全栈 relay（Gemini Lab 那类） | 可定制 | 很低 | 低 | **否**（除非坚持且确认） |

**不做（默认）：**

- 给 466 个 Pipe 文本模型全挂 Live  
- 重开 Web Tools / 全局 Image Gen 当 Live 路径  
- 未确认就上 L3 多提供商并行 Live 网格  

---

## 4. 推荐阶梯（由简到繁）

### L0 — 前置（阻塞项，0～1 天量级）

**目标**：Live 能在 micropigeon 上 **选到 vision 模型并出字**。

| 步 | 动作 | 通过判据 |
|----|------|----------|
| L0-1 | 修 **models catalog 空**（`apply_wave0`、Pipe 同步、public） | `verify_stack` catalog + smoke 全绿 |
| L0-2 | Admin：用户权限 `chat.stt` / `chat.tts` 开启 | 普通用户能开 Voice Mode |
| L0-3 | 手工：Voice Mode → **共享屏幕** + **Grok 4.6**（或 Gemini vision）→ 问「屏幕上有什么」 | 有可见回答 |
| L0-4 | 手工：摄像头切换、静音（0.11 已支持 remember camera / mute） | 无崩溃 |

**不确认也可做**（不牺牲稳定）。

---

### L1 — OWUI 原生 Live（**默认落地目标**）

**产品形态**：一个入口 — 聊天页 **Call / Voice** 按钮；屏享=overlay 里开共享；模型=选 **vision** Pipe 模型。

| 步 | 动作 | 类型 |
|----|------|------|
| L1-1 | TTS 升级 `tts-1-hd`；`TTS_SPLIT_ON=sentence`（首包更快） | 配置 |
| L1-2 | 英文 Banner/chip：**Screen share → pick Grok 4.6 or Gemini vision first** | 指引 |
| L1-3 | 默认 Live 推荐模型置顶/Description（**不换** 19 public 契约） | metadata |
| L1-4 | `scripts/verify_live_baseline.py`：STT 短音频、TTS 短句、vision 模型 smoke | 验收 |
| L1-5 | 成本护栏：屏享时提示帧率/费用；长静音可考虑客户端降帧（若 OWUI 已做则只写指引） | 体验 |

**质量预期（诚实）：**

- ✅ 屏幕共享 **能用**、能围绕画面问答、摄像头可开  
- ✅ 与现有 Pipe、对比、方案 A **不打架**  
- ⚠️ 往返延迟通常 **数秒级**（你 Opus 39s 是文本+重试；语音串联一般更快但仍非亚秒）  
- ❌ **不等于** ChatGPT Advanced Voice 的 S2S 打断感  

**通过判据**：L0 全过 + 屏享 3 分钟会话无 404 + 能描述屏幕主要内容。

---

### L2 — Realtime 容器（**须你点头**）

**背景**：Open WebUI **主线 0.11 尚未合入** OpenAI Realtime；社区 **rbb-dev**（同 OpenRouter Pipe 作者）提供 `ghcr.io/rbb-dev/open-webui-realtime:latest`，支持 WebRTC Realtime、通话中 tools、历史回写聊天。

| 项 | 说明 |
|----|------|
| 收益 | 更接近 GPT Live：**快、可打断、通话中 tool** |
| 代价 | 第二镜像或替换 OWUI；**Realtime 模型**（常需 **OpenAI 直连密钥**，OpenRouter Realtime 能力待 L0 实测） |
| 与 Pipe | 文本聊天仍可保留现有 Pipe；Live 为 **并行表面** |
| 确认门 | 是否接受 **非 stock OWUI**、是否新增 **OpenAI API Key**、是否双容器 |

**通过判据**：WebRTC 通话 &lt;1.5s 首响（主观）+ 屏享/工具至少一种路径可用。

---

### L3 — 提供商原生 Live（**须你点头 + 选一家**）

只选 **一条** 主 Live 栈，避免三密钥三中继：

| 选型 | 最适合 | 屏享 | 备注 |
|------|--------|------|------|
| **Gemini Live** | **屏幕共享首要** | 原生 1fps | 需 Google AI / Vertex；会话时长限制（音视频约 2min 档需扩展策略） |
| **OpenAI Realtime** | 最贴 ChatGPT Live | 支持 | 与 L2 重叠；密钥 OpenAI |
| **Grok Voice + Grok 4.6 vision** | 全栈 xAI 叙事 | 混合：Voice WSS + 屏帧走 Pipe/vision | 工程量大；**冲最高但最不稳** |

**实现形态（共性）**：浏览器 → **自有 HTTPS 中继**（micropigeon 或子域）→ 厂商 Live WSS；**不**经过 OpenRouter Pipe 文本重建。

**确认门**：密钥、月费（约 **$0.05–0.08/分钟** 量级）、是否接受 **自研中继**、是否放弃「全部只走 OpenRouter 账单」。

---

## 5. 与现有契约的关系

| 现有 | Live 计划 |
|------|-----------|
| UX-5 双模型对比 | Live **默认单栏**；对比仍走文本聊天 |
| 路线 S 作图 | 不变；Live 屏享 ≠ Image Gen |
| ST-1～ST-10 | 新增 **ST-Live**（见下）不破坏 Sonar/对比 |
| 19 public | Live 只 **推荐** 2～3 个 vision 模型，不扩 public 爆炸 |

**拟新增 SPEC（落地 L1 后写入）：**

| ID | 必须 |
|----|------|
| ST-Live-1 | Live/屏享/摄像走 **OWUI Call overlay**；禁止第二套未文档化前端 |
| ST-Live-2 | 屏享会话 **必须** vision-capable 模型；禁止对 Sonar/纯图像开 Live tool 幻觉 |
| ST-Live-3 | STT/TTS 继续 OpenRouter 时：**merge** 配置，不覆盖密钥 |
| ST-Live-4 | Realtime/Live API（L2+）**未确认前** 不上生产 |

---

## 6. 验收口径（分档）

### L1 验收（默认「够用」）

1. 新用户：Banner 看懂「先选 vision 模型再开屏享」  
2. 屏享 + 麦克风：能连续 5 轮问答  
3. 摄像头：可切换且 0.11 记住上次设备  
4. `verify_live_baseline.py` 全绿（待写）  
5. 不影响 `verify_stack` / 对比 ST-10  

### L2/L3 验收（「官网顶级」）

1. 首包音频 &lt;1.5s（同地区）  
2. 说话可打断模型播报  
3. 屏享时模型能引用 **刚发生** 的 UI 变化（非仅静态截图）  
4. 会话结束历史正确落回 OWUI chat  

---

## 7. 风险与「极大不稳」触发确认门

| 风险 | 等级 | 是否须先确认 |
|------|------|----------------|
| L1 仅串联，达不到官网 S2S | 预期内 | 否（先交付可用屏享） |
| 换 rbb-dev realtime 镜像 | 运维 | **是** |
| 第二/第三厂商 API 密钥 | 成本+密钥 | **是** |
| 自研 WebSocket 中继 | 安全+维护 | **是** |
| OWUI 核心大改 | 升级地狱 | **是** |
| 屏享 1fps 看不清快速 UI | 产品预期 | 否（写进指引） |

---

## 8. 建议你现在拍板的 4 个问题

1. **目标档位**：先 **L1 稳定屏享助教**，还是 **必须 L2/L3 官网 S2S**？  
2. **密钥**：是否接受 **OpenAI / Google / xAI 直连**（不只 OpenRouter）？  
3. **部署**：能否接受 **rbb-dev realtime 镜像** 或 **独立 Live 子服务**？  
4. **预算**：语音 Live 是否按 **$/分钟** 计费可接受（需用量上限）？

**默认推荐（符合简单·稳定）：**  
**L0 → L1 全做完并验收** → 你再体验屏享是否够用 → **不够再选 L2 或 L3a（Gemini Live）**，不并行开三家。

---

## 9. 执行顺序（给 Agent）

```
L0 修 catalog + 权限烟测
  → L1 配置/指引/verify_live_baseline
  → （你确认后）L2 或 L3 单选试点
  → 写入 SPEC ST-Live-* 与 VERSIONS
```

**禁止**：跳过 L0 直接追 Realtime；未确认同时上 Gemini+OpenAI+Grok Live。

---

## 10. 参考

- OWUI Voice & Video：https://open-webui-open-webui.mintlify.app/features/voice-video  
- OWUI 0.11：Call mute、remember camera（发行说明）  
- OpenAI Realtime：https://developers.openai.com/api/docs/guides/realtime  
- Gemini Live：https://ai.google.dev/gemini-api/docs/live-api  
- Grok Voice Agent：https://docs.x.ai/developers/model-capabilities/audio/voice-agent  
- rbb-dev Realtime 讨论：https://github.com/open-webui/open-webui/discussions/22622  
- 本仓库：`docs/SPEC.md`、`docs/open-webui-optimized-plan.md`

*确认本文件后执行：**L0 → L1**；L2/L3 等你 §8 四点回复后再动。*

---

## 11. 社区是否有现成方案？（能帮多少）

**结论：能帮很多，但分档——不能一个插件包办「屏享 + 三家 Live 官网同级」。**

### 11.1 已经在你栈里、直接能用（帮 **L1 大头**）

| 来源 | 是什么 | 帮你省什么 | 屏享 | 官网 Live 级语音 |
|------|--------|------------|------|------------------|
| **Open WebUI 0.11 主线** | Call overlay：语音 / 摄像 / **屏幕共享** / VAD / 静音 | 不用自研浏览器采集 UI | ✅ 内置 | ❌ 串联 STT→模型→TTS |
| **你已装的 rbb-dev Pipe** | OpenRouter 全目录 + whisper STT + tts-1（micropigeon 已配） | 账单统一 OpenRouter | ✅ 配 **vision 模型** 即可 | ❌ |
| OWUI 文档 | [Voice & Video](https://open-webui-open-webui.mintlify.app/features/voice-video) | 配置参考 | ✅ | ❌ |

→ **「屏幕共享首要」**：社区 **已经做了 80% UI**；你主要是 **L0 修 catalog + 选 vision 模型 + 调 STT/TTS**（计划 L1），不必从零写 `getDisplayMedia`。

### 11.2 同生态、最接近 GPT Live 语音（帮 **L2 大头**）

| 来源 | 是什么 | 帮你省什么 | 屏享 | 备注 |
|------|--------|------------|------|------|
| **rbb-dev/open-webui-realtime** | 独立镜像 `ghcr.io/rbb-dev/open-webui-realtime:latest` | **整包 Realtime WebRTC**：可打断、通话中 **OWUI tools**、历史回写聊天、打字接力进同一会话 | ⚠️ PR 写 **message/image handoff** 进 Realtime 会话，**不是** Gemini 式持续屏享 HUD | 与 **你用的 Pipe 同作者**；[讨论 #22622](https://github.com/open-webui/open-webui/discussions/22622)、[PR #23237](https://github.com/open-webui/open-webui/pull/23237)（**未合入主线**，维护者称 scope 太大） |
| rbb-dev 说明 | 兼容 OpenAI Realtime 规范；模型名须含 `realtime` | 可换 **支持 Realtime 的 base URL**（不只 OpenAI） | — | OpenRouter 是否完整支持 **ephemeral + WebRTC** 需 **实测**，不能假设 |

→ **「像 ChatGPT 语音对话」**：社区 **有成品 fork**，不必自研 WebRTC；代价是 **换/并行 OWUI 镜像** + 多半 **OpenAI 或 Realtime 兼容密钥**（确认门）。

### 11.3 OpenRouter / 其他 Pipe _fork（帮 **音频模型**，不帮 Live 会话）

| 来源 | 是什么 | 帮你省什么 | 屏享 | 备注 |
|------|--------|------------|------|------|
| **rbb-dev Pipe**（主） | `gpt-audio*`、`lyria` 等 via `/chat/completions` | 聊天里 **生成/理解音频** | 图像/视频路由已有 | **不是** 全双工 Realtime |
| sena-labs Pipe 分叉 | 类似 OpenRouter 全家桶 + 音频输出 valves | 可借鉴配置 | 同左 | 你已用 rbb-dev，**不必换** |
| OpenRouter 列表 | `gpt-4o-realtime` 等标价存在 | — | — | **标价 ≠** OWUI/Pipe 已接好 WebRTC 会话 |

### 11.4 官方 OWUI 主线（未来，**现在不能指望**）

| 项 | 状态 |
|----|------|
| OpenAI Realtime 合入 stock | PR #23237 **closed，未 merge**；维护者「open to discussion」 |
| Gemini Live 原生 | **无**；issue/讨论里多指向 **自研 relay / LiveKit / Pipecat** |
| Grok Voice | **无** OWUI 集成；要走 xAI `wss://api.x.ai/v1/realtime`（与 Pipe 无关） |

### 11.5 社区旁路（帮 **L3**，但要第二套产品）

| 来源 | 适合 | 屏享 | 简单 |
|------|------|------|------|
| **Google gemini-live-api-examples** + ADK | **Gemini Live**（屏+音一体最好） | ✅ ~1fps | 低 |
| **LiveKit / Pipecat / fastrtc** | 多厂商 Realtime 胶水 | 可接 | 低 |
| **Realtime HUD** 等独立 HUD | OpenAI Realtime + **屏快照** | ✅ 专做屏享 | 与 OWUI **分离** |
| **Unmute / Kyutai** | 本地 STT/TTS 端点喂 OWUI | 仅 L1 串联 | 中 |

### 11.6 对你目标的「帮助度」一张表

| 目标 | 社区现成能 cover 多少 | 仍须自己做 |
|------|----------------------|------------|
| **屏幕共享 + 语音问答（稳定）** | **~70%**（OWUI overlay + vision Pipe） | L0 catalog、指引、验收 |
| **GPT Live 级语音（打断、快）** | **~60%**（rbb-dev realtime 镜像） | 部署决策、密钥、与 Pipe 双栈 |
| **Gemini Live 级屏+音 S2S** | **~30%**（Google 示例 + 中继） | **L3 自研或旁路**，无 OWUI 一键 |
| **Grok Voice 官网级** | **~50%**（xAI Realtime API 现成） | 密钥 + 中继；**屏享要混合** Grok vision |
| **三家都满配在一个 OWUI 里** | **~0%** 现成 | 确认门：多密钥 + 多中继或接受「语音 Realtime + 文本 Pipe 屏享」混合 |

### 11.7 建议怎么用社区（更新 §8 默认推荐）

1. **先不造轮子**：L0 + L1 = **stock OWUI + 现有 Pipe**（社区已给 UI 与 OpenRouter 音频）。  
2. **若 L1 语音不够快**：优先试 **rbb-dev realtime 镜像**（与 Pipe **同作者**，社区口碑最好），而不是自研 WebRTC。  
3. **若屏享要 Gemini Live 那种 S2S**：社区 **没有** OWUI 内一键方案 → 只能 **L3 旁路**（Gemini Live API + 中继）或 **混合**：Realtime 管语音 + OWUI 屏享帧进 vision 模型。  
4. **暂不必看**：换 sena-labs Pipe、全仓 fork CSM/Sesame、等 OWUI 主线 merge（不确定）。

