# SPEC — Open WebUI 体验与稳定性契约

> **真相源（产品）**。实现可换；验收以 `scripts/verify_stack.py` 为准。  
> **关联**：`docs/open-webui-optimized-plan.md`（波次）、`docs/open-webui-delta-vs-stock.md`（已落地差异）、`docs/open-webui-notebook-youtube-plan.md`（P0-C）、`docs/open-webui-live-voice-screen-plan.md`（P0-B Live）

---

## 宪法（以往与以后所有动作）

1. **强能力**：媲美甚至超越 ChatGPT / Grok 等 **最顶级付费档** 的功能。特别困难或复杂的实现，**必须先确认**：是否改用 **略微降级、但简单稳定特别多** 的方案。  
2. **务必简单和稳定**，优先 **易维护**（少镜像、少密钥、少与上游分叉）。  
3. **重大改动**：先出 plan，**你确认后再执行**。未确认不改实例。

旧「冲最高就默认砍掉」不再作默认：目标仍是顶级；降级必须是 **你点头的权衡**，不是执行者自行放弃。

## 全局最高优先级（P0，三条并列）

不是「做完一条再做下一条」。Live 文档里的「屏享首要」只作用于 **Live 子系统**（屏享 → 语音 → 摄像）。

| ID | 主线 | 现状 | 独立 plan |
|----|------|------|-----------|
| **P0-A** | **图像生成** | Now：路线 S 已落地 | `open-webui-openrouter-image-continuity-plan.md`（连续性仍增强） |
| **P0-B** | **屏幕共享** | L1 已落地；L2 S2S **暂缓、须再确认** | `open-webui-live-voice-screen-plan.md` |
| **P0-C** | **Notebook / YouTube** | **仅规划**；未改实例 | `open-webui-notebook-youtube-plan.md` |

P0-C 旗舰是 **YouTube 真理解**（ASR 回退 + 视觉时间线 + 可点击 timestamp），不是「转录丢进 RAG」。达标面见该 plan §1；**NL-A ≠ NL-B**。

---

## 用户契约（Now）

| ID | 必须 |
|----|------|
| UX-1 | **四格捷径**：Chat = Sol Pro / Opus；Quick search = Sonar Pro Search；Deep report = Sonar Deep Research；Images = 先切图像模型（Banana Pro / GPT Image 2 等） |
| UX-2 | 英文指引：两条 Banner + 关键 Description + 空对话 chips（「Select … first」） |
| UX-3 | Integrations **无** OR Web Tools / OR Image Gen / OWUI Web Search；保留 Direct Uploads；图像模型可有 native image filter |
| UX-4 | **19 个 public** 维持（对比用）；不缩到 6 |
| UX-5 | 新对话默认 **双模型**：`grok-4.6` + `claude-opus-5`（并排对比）；难题仍可调 Reasoning depth；Sol Pro 在置顶四格 |
| UX-6 | **路线 S**：作图 = 选图像模型。**全局原生 Image Gen 关闭**（`ENABLE_IMAGE_GENERATION=false`）；Sol/Opus 的 `image_generation` capability 保持 false |

## 稳定性（Now）

| ID | 必须 |
|----|------|
| ST-1 | Sonar / 纯图像模型：请求不得带 OpenRouter 不支持的 tools（含 `get_current_timestamp`） |
| ST-2 | 不依赖 Web Tools 做搜索；`openrouter_web_tools` / `openrouter_image_gen` **停用** |
| ST-3 | `gpt-image-*` / `seedream-5*` 走 Images API |
| ST-4 | Pipe valves **只 merge**，禁止空覆盖 `API_KEY` |
| ST-5 | `AUTO_INSTALL_*` / `AUTO_ATTACH_*` web_tools & image_gen = false |
| ST-6 | `UPDATE_MODEL_CAPABILITIES` = false |
| ST-7 | Sonar / 纯图像：`code_interpreter` 为 false；纯图像额外 `builtin_tools` / `terminal` 为 false。**不**关 Sol Pro 的 code interpreter |
| ST-8 | 后台 Task 模型 = **Grok 4.6**（与默认聊天同档，低成本） |
| ST-9 | **全局** `enable_image_generation` / `ENABLE_IMAGE_GENERATION` = false（路线 S；作图只走 Pipe 图像模型） |
| ST-10 | 对比多轮：跨模型 `encrypted reasoning` 不得让一栏永久 404。Pipe 在 400/404 且错误含 `produced under a different model` / `encrypted reasoning` / `compaction content` 时，剥回放密文并 **内部重试**。`PERSIST_REASONING_TOKENS` 保持 `conversation`（单模型零损失）。**不**把全局 `disabled` 当终态。 |
| ST-Live-1 | Live / 屏享 / 摄像走 **OWUI Call overlay**；禁止第二套未文档化前端 |
| ST-Live-2 | 屏享会话必须用 **vision-capable** 模型（Grok 4.6 或 Gemini vision）；禁止对 Sonar / 纯图像开 Live tool 幻觉 |
| ST-Live-3 | STT/TTS **merge** 配置，不覆盖密钥。TTS = OpenRouter `minimax/speech-2.8-turbo`（兼容 OWUI 默认 voice `alloy` + `response_format=mp3`）；STT = `openai/whisper-large-v3-turbo`。**不要**再用 `openai/tts-1` / `tts-1-hd`（OpenRouter `/audio/speech` 无此模型 → Read Aloud 400）。真正 S2S 仍走 L2（须确认） |
| ST-Live-4 | Realtime / 厂商 Live API（L2+）**未确认前** 不上生产 |

## P0-C 规划 ID（文档已确认；N1+ 未确认执行前不生效）

落地前只约束规划与 Agent，不把 Knowledge 写成已可用。条文全文见 `docs/open-webui-notebook-youtube-plan.md` §5。

| ID | 必须 |
|----|------|
| ST-NL-1 | YouTube = 转录 **加** 视觉时间线；无字幕走 ASR |
| ST-NL-2 | 关键结论可点击 timestamp；区分 spoken / shown / inferred |
| ST-NL-3 | Notebook 问答源边界内；不用 Sonar / web_tools 冒充知识库 |
| ST-NL-4 | Audio Overview ≠ Call overlay；不得为 Overview 覆盖 Live TTS |
| ST-NL-5 | Notebook 入口须文档化；不与四格搜索按钮混用 |
| ST-NL-6 | YouTube ingest ≠ Wave 1 视频生成 |
| ST-NL-7 | N1+ **未确认执行前** 不上生产（含不改 `rag.*`） |

## 明确 Later / Don't

- **已落地**：聊天四格 + 路线 S；Live **L1**（stock overlay + Whisper/TTS + vision 指引）  
- **P0 进行中**：图像增强；屏享保持 L1；**Notebook/YouTube（P0-C，下一执行候选须再确认）**  
- **Later（须单独确认）**：Live **L2** Realtime（暂缓）；Wave 1 **视频生成**；Wave 2 slides；Notebook N3/N4 Studio  
- **Don't**：ComfyUI / inpainting、第二套 Pipe、重开 Web Search 三件套、466 全 public、同会话作图主路径、L3 三家 Live 并行、stock+realtime 双容器、把 RAG 当加分项、把 YouTube 转录当成 NotebookLM 达标、用 gpt-audio 冒充已接好的 Call S2S 

---

## 固定 ID

Pipe 前缀：`open_webui_openrouter_integration.`

**置顶**：`perplexity.sonar-pro-search`、`perplexity.sonar-deep-research`、`anthropic.claude-opus-5`、`openai.gpt-5.6-sol-pro`

**19 public** 与 `scripts/stack_contract.py` 中 `PUBLIC_MODEL_IDS` 必须一致。
