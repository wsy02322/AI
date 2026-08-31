# Live 语音 · 摄像头 · 屏幕共享 — 方案

> **状态**：v4 规划已对齐 P0 四条并列。v2 已执行 L0+L1。**N1 Notebook 已执行**。顶级语音/持续屏享仍未完成：环境无 OpenAI/Google Realtime 钥匙，且 rbb L2 不能让屏享达标，故未换镜像。
> **日期**：2026-08-21  
> **优先级**：**语音聊天 = P0-B，屏幕共享 = P0-C**，两者全局同级（与图像、Notebook 并列）；摄像头仍为 Live 辅助能力
> **宪法**：（1）媲美 ChatGPT / Grok 最顶级付费档；特别困难复杂须确认是否略降级换简单稳定；（2）务必简单稳定、易维护；（3）重大改动先 plan、确认后再执行  

---

## Review（v3 → v4：语音与屏享同级 P0）

v4 **不改实例**。用户纠正：语音聊天不能放在屏享下面，也不能因 Notebook P0 而默认暂缓。

| v3 / 口头建议 | 宪法下的更正 |
|---------------|--------------|
| gpt-audio 无额外镜像就能让 Call 变快 | Call 仍是 STT→文本→TTS。Pipe 无完整 `output_audio`。改 Call = OWUI 前端分叉，仍无 barge-in → **不推荐当捷径** |
| L2 overlay「丢失屏享」 | 准确说：Realtime overlay **无 `getDisplayMedia`**，**该 overlay 内**不能持续共享屏幕；不是站点所有屏享入口必然消失 |
| L2 是唯一 S2S 路径 | 是 **OWUI 生态最短社区成品**；Gemini Live / 自建 Realtime 也能做，但更重 |
| 屏享 → 语音 | **撤销**。语音 P0-B 与屏享 P0-C 同级，都以顶级付费档为目标 |
| L2 全局暂缓、带宽让给 Notebook | **撤销**。四条 P0 并列；各自执行仍须单独 plan/确认 |
| rbb L2 当 Live 终态 | **不成立**：它能补 P0-B 语音，却不能让 P0-C 持续屏享达标；只能是局部候选 |

**复杂度门仍有效：** 先比较「语音+屏享统一顶级方案」与「两条较简单稳定的局部方案」。若统一方案明显更重，必须问用户是否接受略降级，不能自行选择。

**与 P0-D 分轨：** Notebook Audio Overview 是异步播客（`open-webui-notebook-youtube-plan.md`），**不是** Call S2S，也不得覆盖 ST-Live-3 TTS。

---

## Review（v1 → v2，对照宪法）

v1 把 **L1 写成默认终点**，等于执行者先替你选了「降级」。宪法不允许这样：目标仍是顶级；降级必须你点头。

| v1 问题 | 宪法下的更正 |
|---------|--------------|
| 「L1 默认落地、L2 以后再说」 | L1 是 **略降级、简单稳定特别多** 的方案，须你确认是否先用；**不是**自动放弃顶级 |
| 「L0 不确认也可做」 | L0 修 catalog 是 **现网故障**，与 Live 产品分开。仍先 plan；你确认后可立刻修 |
| 把屏享与 S2S 绑成同一档 | **屏享**在 stock OWUI 已接近顶级入口；**语音打断**才必须 Realtime。不要为语音去换整仓而弄丢屏享 |
| L2 双容器（stock + realtime） | **更难维护**。若上 Realtime：优先 **替换同一套 OWUI 镜像**（rbb-dev 持续 rebase），不要长期两套 |
| L3 三家并列 | 违反简单。最多 **一家** Live 栈 |
| L4 自研中继 | **否**（除非你坚持且确认） |

**能力拆开（否则会选错栈）：**

| 你要的 | 顶级怎么实现 | 略降级（简单稳定很多） |
|--------|----------------|------------------------|
| **屏幕共享（P0-C）** | Gemini Live 持续 1fps S2S | **OWUI overlay + vision 模型**（社区已有 UI；延迟数秒、难打断） |
| **实时语音 / 打断（P0-B）** | OpenAI Realtime 或 Grok Voice 或 rbb-dev 镜像 | 现有 **Whisper → 文本模型 → TTS** |
| **摄像头** | 与屏享同一 overlay / Live 会话 | 同上，OWUI 已有 |

v1 的 L1 **在屏享上并不弱很多**（入口已有）；弱的是 **语音体感**。所以「略降级」主要牺牲的是 **ChatGPT Voice 那种语感**，不是「不能看屏」。

**易维护排序（宪法第 2 条）：**

1. stock OWUI 0.11 + 现有 Pipe（L1）  
2. **整机换成** `open-webui-realtime`（L2，仍是一套 OWUI + 同一 Pipe）  
3. 旁路 Gemini/OpenAI/xAI Live 中继（L3，第二套产品）  
4. 双容器并行 / 自研 HUD — **不推荐**

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
| TTS | `openai` → OpenRouter **`minimax/speech-2.8-turbo`**，voice `alloy`，`SPLIT_ON=sentence`。Read Aloud / Call overlay 经 `/audio/speech` 出 MP3（2026-08-21 实测 200）。`openai/tts-1[-hd]` 在 OpenRouter **不存在** |
| OWUI 内置 | Call overlay：**语音 / 视频 / 屏幕共享 / 多模态输入**（官方文档与 0.11 发行说明） |
| `enable_websocket` | **true** |
| 模型目录 | **已修**（2026-08-21）：运行时 ~472 Pipe 模型；19 public 已重建 |

结论：**屏幕共享 UI 在 OWUI 里已有**；L0 catalog 不再阻塞。真·官网语音仍需 L2 Realtime。

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

**「媲美甚至超越」拆开后：**

- **屏享**：L1 已接近「能看屏问答」；与 Gemini Live 的差距主要是 **帧率/打断/语感**，不是「没有共享按钮」。  
- **语音**：L1 **达不到** ChatGPT / Grok Voice 付费档；那是 L2/L3。  
- 宪法下不把 L1 写成终点；写成 **「你确认的略降级」** 或 **「通往 L2 的验收台阶」**。

---

## 3. 架构选项（用宪法筛）

| 路径 | 做什么 | 强 | 简单·易维护 | 判定 |
|------|--------|----|--------------|------|
| **L0** | 修 catalog、权限、STT/TTS 烟测 | 现网故障 | 高 | **独立**：确认后立刻做，不塞进 Live 大改 |
| **L1** | OWUI 原生 Voice/Video + vision | 屏享够用；语音非 S2S | **最高** | **略降级方案**；须确认是否先落地 |
| **L2** | **替换**为 rbb-dev `open-webui-realtime`（一套镜像，保留 Pipe） | 语音接近 GPT Live；**该 overlay 无持续 `getDisplayMedia`** | 中（跟 fork 升级） | **P0-B 局部候选**，不是 P0-B/P0-C 共同终态；重大，须单独确认 |
| **L3a** | 旁路 Gemini Live | **屏+音一体最强** | 低（第二产品） | **统一顶级候选**；密钥、中继、第二表面均触发复杂度确认门 |
| **L3b/c** | OpenAI / Grok 直连 Live | 语音顶级 | 低 | P0-B 候选；持续屏享能力须独立验证，不能假设 |
| **L4** | 自研中继 / 双容器长期并行 | 可定制 | 很低 | **否** |

**不做（默认）：** 466 全挂 Live；重开 Web Tools；未确认上 L3 三家并行；长期 stock+realtime 双容器。  

---

## 4. 实现档位（由简到繁，不代表优先级）

### L0 — 前置（阻塞项，0～1 天量级）

**目标**：Live 能在 micropigeon 上 **选到 vision 模型并出字**。

| 步 | 动作 | 通过判据 |
|----|------|----------|
| L0-1 | 修 **models catalog 空**（`apply_wave0`、Pipe 同步、public） | `verify_stack` catalog + smoke 全绿 |
| L0-2 | Admin：用户权限 `chat.stt` / `chat.tts` 开启 | 普通用户能开 Voice Mode |
| L0-3 | 手工：Voice Mode → **共享屏幕** + **Grok 4.6**（或 Gemini vision）→ 问「屏幕上有什么」 | 有可见回答 |
| L0-4 | 手工：摄像头切换、静音（0.11 已支持 remember camera / mute） | 无崩溃 |

**重大？** 否（修故障）。仍按宪法第 3 条：**你确认后执行**。

---

### L1 — OWUI 原生 Live（**略降级、简单稳定特别多**）

**产品形态**：一个入口 — 聊天页 **Call / Voice** 按钮；屏享=overlay 里开共享；模型=选 **vision** Pipe 模型。

| 步 | 动作 | 类型 |
|----|------|------|
| L1-1 | TTS = OpenRouter `minimax/speech-2.8-turbo`（兼容 `alloy`）；`TTS_SPLIT_ON=sentence` | 配置 |
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

### L2 — Realtime 容器（**须你点头；P0-B 局部候选**）

**背景**：Open WebUI **主线 0.11 尚未合入** OpenAI Realtime；社区 **rbb-dev** 提供 `ghcr.io/rbb-dev/open-webui-realtime`。若执行：**钉死版本标签**（建议 `:v0.11.0`），**禁止 `:latest`**（会跟 `mtech-dev`，含未声明 Microsoft Graph OAuth）。

| 项 | 说明 |
|----|------|
| 收益 | 更接近 GPT Live：**快、可打断、通话中 tool** |
| 代价 | **替换** OWUI 镜像；常需 **OpenAI 或 Realtime 兼容密钥**；**该 overlay 无 `getDisplayMedia`**（持续屏享会退化成静态图/handoff） |
| 与 Pipe | **保留同一套 Pipe**；不要再开第二套 stock 容器 |
| 确认门 | 非 stock OWUI、新钥匙、跟 fork、**接受该 overlay 只提升语音、不让持续屏享达标** |

**通过判据**：WebRTC 通话 &lt;1.5s 首响（主观）+ **明确记录**屏享是 handoff 还是持续帧（不得把静态图写成 Gemini Live 级屏享）。

---

### L3 — 提供商原生 Live（**须你点头 + 选一家**）

只选 **一条** 主 Live 栈，避免三密钥三中继：

| 选型 | 最适合 | 屏享 | 备注 |
|------|--------|------|------|
| **Gemini Live** | **语音 + 屏享统一** | 原生 1fps | 需 Google AI / Vertex；会话时长限制与接入复杂度须实测 |
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
| ST-1～ST-11 | 新增 **ST-Live**（见下）不破坏 Sonar/对比 / Follow-up 关 |
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

### L1 验收（略降级档）

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
| L1 语音达不到官网 S2S | 预期内 | **是**（确认是否接受略降级） |
| 换成 rbb-dev realtime **一套**镜像 | 运维 | **是**（重大） |
| 第二/第三厂商 API 密钥 | 成本+密钥 | **是** |
| 自研 WebSocket 中继 | 安全+维护 | **是** |
| OWUI 核心大改 | 升级地狱 | **是** |
| 屏享 1fps 看不清快速 UI | 产品预期 | 否（写进指引） |

---

## 8. 拍板记录（v4）

| 项 | 状态 |
|----|------|
| A L0 catalog | **已做** |
| B1 L1 overlay | **已做**（稳定过渡；语音与持续屏享均未达顶级） |
| P0-B 顶级语音 | **最高优先级、未完成**。目标：S2S、barge-in、低延迟 |
| P0-C 顶级屏享 | **最高优先级、未完成**。目标：持续帧、理解刚发生的变化 |
| B2 rbb L2 | **未确认**。只提升 P0-B；新钥匙 + fork；该 overlay 无持续屏享 |
| L3a 统一 Live | **未确认**。用户计划 **另建新 GitHub 仓库** 独立部署（交接包 `handoff/gemini-live-standalone/`） |
| gpt-audio 改 Call | **不做捷径** |
| gpt-audio 体验对照 | **GA-A 已执行** — Pipe **`/responses`** 拒 `modalities.audio` → 聊天 API 无 `output_audio`（听感/延迟/usage 未测）；维持 L1，见 `open-webui-gpt-audio-trial-plan.md` §5 |
| P0-D Notebook | 与 Live 两项同级；独立 plan/确认，不要求 Live 让出优先级 |

**现在不做：** 未选档就改实例、L3 三家并行、stock+realtime 双容器、为 Overview 改 Live TTS。

---

## 9. 执行确认门（给 Agent）

```
（已确认）L0 + L1（稳定过渡）
  ├─ 顶级统一：L3a（语音 + 持续屏享；复杂度高）
  ├─ 局部提升：L2（顶级语音；持续屏享仍走 L1）
  └─ 维持 L1（略降级但最简单稳定）
```

Agent 必须先给出三档的模型能力、密钥、镜像/中继、屏享、升级维护和成本实测，再由用户选。**不得**因两项同为 P0 就绕过确认，也不得自行选择 L1 降级或 L2 局部提升。

**禁止**：未确认改实例；把 L2 写成语音+屏享均达标；跳过确认上 Realtime；长期双容器。

---

## 10. 参考

- OWUI Voice & Video：https://open-webui-open-webui.mintlify.app/features/voice-video  
- OWUI 0.11：Call mute、remember camera（发行说明）  
- OpenAI Realtime：https://developers.openai.com/api/docs/guides/realtime  
- Gemini Live：https://ai.google.dev/gemini-api/docs/live-api  
- Grok Voice Agent：https://docs.x.ai/developers/model-capabilities/audio/voice-agent  
- rbb-dev Realtime 讨论：https://github.com/open-webui/open-webui/discussions/22622  
- 本仓库：`docs/SPEC.md`、`docs/open-webui-optimized-plan.md`、`docs/open-webui-notebook-youtube-plan.md`

*L1 已落地但不是顶级终态。P0-B/P0-C 后续档位未确认前不改实例。*

---

## 11. 社区是否有现成方案？（能帮多少）

**结论：能帮很多，但分档——不能一个插件包办「屏享 + 三家 Live 官网同级」。**

### 11.1 已经在你栈里、直接能用（帮 **L1 大头**）

| 来源 | 是什么 | 帮你省什么 | 屏享 | 官网 Live 级语音 |
|------|--------|------------|------|------------------|
| **Open WebUI 0.11 主线** | Call overlay：语音 / 摄像 / **屏幕共享** / VAD / 静音 | 不用自研浏览器采集 UI | ✅ 内置 | ❌ 串联 STT→模型→TTS |
| **你已装的 rbb-dev Pipe** | OpenRouter 全目录 + whisper STT + tts-1（micropigeon 已配） | 账单统一 OpenRouter | ✅ 配 **vision 模型** 即可 | ❌ |
| OWUI 文档 | [Voice & Video](https://open-webui-open-webui.mintlify.app/features/voice-video) | 配置参考 | ✅ | ❌ |

→ **「稳定过渡」**：社区已完成大部分采集 UI；L1 不必从零写 `getDisplayMedia`，但它不等于顶级持续屏流，也不降低 P0-B 语音的优先级。

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

### 11.7 社区怎么用（宪法）

1. **屏享（本子系统）**：用 stock overlay，不造 `getDisplayMedia`。L2 overlay **不能**替代持续屏享。  
2. **语音要顶级**：社区最短路仍是 rbb-dev realtime；它是 P0-B 局部候选，须确认，不能掩盖 P0-C 缺口。
3. **Gemini Live 级持续屏流**：社区无 OWUI 一键 → 另开 plan（L3），现在不执行。  
4. **Notebook / YouTube（P0-D）**：见 `open-webui-notebook-youtube-plan.md`，不是本文件的 Call 栈。
5. **不必看**：换 sena-labs Pipe、等主线 merge、CSM/Sesame、gpt-audio 当 Call 捷径。

