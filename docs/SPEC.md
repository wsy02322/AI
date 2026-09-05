# SPEC — Open WebUI 体验与稳定性契约

> **真相源（产品）**。实现可换；验收以 `scripts/verify_stack.py` 为准。  
> **关联**：`docs/open-webui-rebuild-archive.md`（灾后入口 / 现网钉子）、`docs/open-webui-upgrade-0113-plan.md`（已落地：官方 0.11.3）、`docs/open-webui-image-studio-plan.md`（独立画图 Studio，**IS-A+ 施工中**；代码 `image-studio/`）、`docs/open-webui-notebook-youtube-plan.md`（P0-D）、`docs/open-webui-live-voice-screen-plan.md`（P0-B / P0-C）、`docs/open-webui-file-ingest-plan.md`（文件录入，T0 未确认）、`docs/open-webui-openrouter-image-continuity-plan.md`（图像错误模式）、`docs/open-webui-secret-key-persist-plan.md`（L0）

---

## 宪法（以往与以后所有动作）

1. **强能力**：媲美甚至超越 ChatGPT / Grok 等 **最顶级付费档**。特别困难复杂：把**顶级方案**和**略降级、简单稳定特别多的方案**一并提案，**先确认再选**。禁止只提降级；禁止把顶级方案留到用户追问之后。  
2. **务必简单和稳定**，优先 **易维护**（少镜像、少密钥、少与上游分叉）。  
3. **重大改动**：先写成 plan 并**主动提案**，确认后再执行。写 plan、讨论、把能力缺口摆上台 **不是** 执行。禁止把本条理解成「未问就不提」；禁止未确认就改实例 / Pipe / 入口形态。

目标仍是顶级；降级必须是 **你点头的权衡**，不是执行者自行放弃。发现与顶级档的能力缺口、或明显更强的实现路径时，当场主动提案（含是否升主线、风险、和不做的代价）；未确认不得动手。

## 全局最高优先级（P0，四条并列）

不是「做完一条再做下一条」。**语音聊天与屏幕共享同级**，不得再把语音写成屏享下面的次级项；两者都受宪法的复杂度确认门约束。

| ID | 主线 | 现状 | 独立 plan |
|----|------|------|-----------|
| **P0-A** | **图像生成** | Now：聊天路线 S；**独立 Studio IS-A+ 施工中**（`image-studio/`） | `open-webui-image-studio-plan.md` + 聊天连续性 `open-webui-openrouter-image-continuity-plan.md` |
| **P0-B** | **语音聊天** | L1 串联已落地但**未达顶级**；S2S / barge-in 待确认方案 | `open-webui-live-voice-screen-plan.md` |
| **P0-C** | **屏幕共享** | L1 入口已落地但**未达持续屏流顶级** | `open-webui-live-voice-screen-plan.md` |
| **P0-D** | **Notebook / YouTube** | N1 已落地（RAG OpenRouter + Knowledge + 视觉时间线）；字幕/ASR 受数据中心 YouTube 风控限制 | `open-webui-notebook-youtube-plan.md` |

P0-D 旗舰是 **YouTube 真理解**（ASR 回退 + 视觉时间线 + 可点击 timestamp），不是「转录丢进 RAG」。达标面见该 plan §1；**NL-A ≠ NL-B**。

---

## 用户契约（Now）

| ID | 必须 |
|----|------|
| UX-1 | **四格捷径**：Chat = Sol Pro / Opus（指定聊天模型也可自动联网）；Quick search = Sonar Pro Search；Deep report = Sonar Deep Research；Images = 先切图像模型（Banana Pro / GPT Image 2 等） |
| UX-2 | 英文指引：**一条** Banner `usage-guide-v5`（🌐 Grok/Sol/Claude/Gemini 可搜可读页；🔗 GitHub 用 github.com 不用 api.github.com；🖼️ 图像只走图像模型；🧠 Valves Reasoning depth；📝 System Prompt 会影响图像与 Perplexity sonar；同一段、句首图标、无粗体）+ 关键 Description；**无**空对话 chips（OWUI 点击即发送） |
| UX-3 | Integrations **无** OR Web Tools / OR Image Gen / OWUI native Web Search；指定 7 个文本模型可有薄 **Web Search**；保留 Direct Uploads；图像模型可有 native image filter |
| UX-4 | **21 个 public**（对比用）；不缩到 6、不扩新家族。**原则**：目前留下的家族只跟 catalog **最新 id**，且 **全部 public**。含 `claude-fable-5.1`（替换 `claude-fable-5`）、`gemini-3.1-pro-preview`、`gemini-3.8-flash`（替换已下线的 `gemini-3.7-flash`）、`qwen3.8-max-0902`（替换 `qwen3.8-max`）。`granite-4.2-8b`、`mercury-2.5-preview` 及新出现的家族（Ling / Muse / Hailuo / GLM Flash / GPT-6 Astra 等）**不** active。契约外模型不得带 `*` read |
| UX-5 | 新对话默认 **单模型**：`grok-4.6`；**不**默认双栏 compare（用户自行开对比）；难题仍可调 Reasoning depth；Sol Pro 在置顶四格 |
| UX-6 | **路线 S**：作图 = 选图像模型。**全局原生 Image Gen 关闭**（`ENABLE_IMAGE_GENERATION=false`）；Sol/Opus 的 `image_generation` capability 保持 false。同会话作图会把图像模型藏进一个开关、再灌 tools（已爆 404）；对比能力比「少点一次切换」更接近宪法 1。视频同一模式：能力在模型上，不在聊天 tool 条上 |
| UX-7 | 回复下方 **Follow-up 建议芯片关闭**（易误触）。空对话 `prompt_suggestions` 保持 **空**。不关 Autocomplete / Title |

## 稳定性（Now）

| ID | 必须 |
|----|------|
| ST-1 | Sonar / 纯图像模型：请求不得带 OpenRouter 不支持的 tools（含 `get_current_timestamp`） |
| ST-2 | 不启用 broad `openrouter_web_tools` / `openrouter_image_gen`；OWUI native Web Search **关**。指定文本模型搜索走 ST-14，不是这两条 |
| ST-3 | `gpt-image-*` / `seedream-5*` 走 Images API |
| ST-4 | Pipe valves **只 merge**，禁止空覆盖 `API_KEY` |
| ST-5 | `AUTO_INSTALL_*` / `AUTO_ATTACH_*` web_tools & image_gen = false |
| ST-6 | `UPDATE_MODEL_CAPABILITIES` = false |
| ST-7 | Sonar / 纯图像：`code_interpreter`、`builtin_tools` 为 false；纯图像额外 `terminal` 为 false。**不**关 Sol Pro 的 code interpreter |
| ST-8 | 后台 Task 模型 = **Grok 4.6**（与默认聊天同档，低成本） |
| ST-9 | **全局** `enable_image_generation` / `ENABLE_IMAGE_GENERATION` = false（路线 S；作图只走 Pipe 图像模型） |
| ST-10 | 对比多轮：跨模型 `encrypted reasoning` 不得让一栏永久 404。Pipe 在 400/404 且错误含 `produced under a different model` / `encrypted reasoning` / `compaction content` 时，剥回放密文并 **内部重试**。`PERSIST_REASONING_TOKENS` 保持 `conversation`（单模型零损失）。**不**把全局 `disabled` 当终态。 |
| ST-11 | 同模型 Anthropic / Fable 续聊：summary-only thinking 不得回放成假 thinking 导致 `cannot be modified` 400。Pipe 请求 `include: ["reasoning.encrypted_content"]`；emit/persist 原样带密文或签名；无密文则剥 unsigned reasoning；400 文案含 ``thinking` / `redacted_thinking` `` + `cannot be modified` 时内部剥回放并重试。`PERSIST_REASONING_TOKENS` 仍为 conversation。旧线程不保证复活。 |
| ST-12 | Task `ENABLE_FOLLOW_UP_GENERATION` = false（PersistentConfig `task.follow_up.enable`）。Wave 0 **merge** 钉死；**不**改 Autocomplete / Title。Admin 若重新打开，重跑 `apply_wave0.py` 关回。 |
| ST-14 | 指定文本模型（Grok 4.6、两条 Sol、Opus 5、Fable 5.1、Gemini 3.1 Pro Preview、Gemini 3.8 Flash）挂非 global 薄 Filter `openrouter_text_web_search`（显示名 Web Search）：写入 OpenRouter `server_tools` Search + Fetch，新对话 default-on，用户可关。Sonar / 纯图像 / 视频不得挂。循环停止 `step_count_is=8` 或 `$0.05`。**质量已收口**（EVAL-B v2）：隐含时效会搜、误搜≈0、普通 HTML 能读；Anthropic **读不了** `api.github.com` Releases JSON，薄 Filter 指引无效。**未确认**不上 Search Controller、不加 Filter 指引、不抬 `$0.05`。评测见 `docs/open-webui-text-web-search-eval-b-results.md`。**不要**把本条和 ST-11/ST-12 写成同一个号 |
| ST-Live-1 | Live / 屏享 / 摄像走 **OWUI Call overlay**；禁止第二套未文档化前端 |
| ST-Live-2 | 屏享会话必须用 **vision-capable** 模型（Grok 4.6 或 Gemini vision）；禁止对 Sonar / 纯图像开 Live tool 幻觉 |
| ST-Live-3 | STT/TTS **merge** 配置，不覆盖密钥。TTS = OpenRouter `minimax/speech-2.8-turbo`（兼容 OWUI 默认 voice `alloy` + `response_format=mp3`）；STT = `openai/whisper-large-v3-turbo`。**不要**再用 `openai/tts-1` / `tts-1-hd`（OpenRouter `/audio/speech` 无此模型 → Read Aloud 400）。真正 S2S 仍走 L2（须确认） |
| ST-Live-4 | Realtime / 厂商 Live API（L2+）**未确认前** 不上生产 |

## P0-D 规划 ID（文档已确认；N1+ 未确认执行前不生效）

落地前只约束规划与 Agent，不把 Knowledge 写成已可用。条文全文见 `docs/open-webui-notebook-youtube-plan.md` §5。

| ID | 必须 |
|----|------|
| ST-NL-1 | YouTube = 转录 **加** 视觉时间线；无字幕走 ASR |
| ST-NL-2 | 关键结论可点击 timestamp；区分 spoken / shown / inferred |
| ST-NL-3 | Notebook 问答源边界内；不用 Sonar / web_tools 冒充知识库 |
| ST-NL-4 | Audio Overview ≠ Call overlay；不得为 Overview 覆盖 Live TTS |
| ST-NL-5 | Notebook 入口须文档化；不与四格搜索按钮混用 |
| ST-NL-6 | YouTube ingest ≠ Wave 1 视频生成 |
| ST-NL-7 | N2+（独立入口 / Studio）**未确认前** 不上生产。N1 允许改 `rag.*` 为 OpenRouter embedding |

## 文件录入（Later；T0 **未确认** 不改实例）

条文全文见 `docs/open-webui-file-ingest-plan.md`。不是 P0 四条，也不是 P0-D。

| ID | 必须 |
|----|------|
| ST-FILE-1 | 不把 Direct 默认全开或扩 MIME 冒充官网录入 |
| ST-FILE-2 | T0 只用钉死的 Tika **3.x-full**；OWUI 0.11.x 不对 Tika 4 |
| ST-FILE-3 | Tika URL 为 `http://tika:9998`；不发布公网 9998 |
| ST-FILE-4 | 未确认不装 Tika、不改 `CONTENT_EXTRACTION_ENGINE`、不改 Pipe |
| ST-FILE-5 | T1/T2 / Docling / 换 OWUI 镜像 **另确认**；不得塞进 T0 |
| ST-FILE-6 | 本方案 ≠ P0-D YouTube ingest ≠ Wave 1 视频生成 |

## 运维密钥（L0 轻量档，**已确认**）

条文全文见 `docs/open-webui-secret-key-persist-plan.md`。**不执行** JWT 持久化 / Pipe Fernet 加密（K1/K2 冻结）。

| ID | 必须 |
|----|------|
| ST-OPS-1 | 容器重建可轮换 JWT（`WEBUI_SECRET_KEY=""`，`.webui_secret_key` 不持久化）；**接受**用户重新登录 |
| ST-OPS-2 | Pipe `API_KEY` 经 **merge 明文** 维护；catalog 空或 decrypt 失败时从 `openai.api_keys[0]` 恢复。**不**做 K1/K2 加密耦合；API 保存后可为 `encrypted:` |
| ST-OPS-3 | `openai.api_configs` 保持全 `enable: false`；任何密钥操作不得改这条 |
| ST-OPS-4 | VPS **禁止**向 env 写入**新的**随机 `WEBUI_SECRET_KEY`（15:09 根因）；若 Pipe key 已是 `encrypted:` 且 decrypt 失败 → env 改回空 + merge 明文 |
| ST-OPS-5 | 不可逆资产 = **DB / volume**（聊天、Knowledge）；JWT 不必备份 |

## 明确 Later / Don't

- **已落地**：聊天四格 + 路线 S；ST-14 薄 Web Search（质量**已收口**）；Live **L1**（stock overlay + Whisper/TTS + vision 指引）  
- **P0 进行中**：图像增强；**语音聊天（S2S / barge-in 未完成，无 Realtime 钥匙故未换镜像）**；**屏幕共享（持续屏流未完成）**；**Notebook/YouTube N1 已落地（视觉时间线可用；口播抓取受 YouTube 风控）**
- **复杂度确认门**：语音与屏享都不得自行降级；若顶级统一方案过重，先列「顶级」与「略降级但简单稳定」两档，由用户确认。rbb Realtime 只补语音、不补持续屏享，不能作为两项均达标的终态
- **Later（须单独确认）**：ST-14 **Search Controller**（Fetch 失败重试 / GitHub API→HTML，改 Pipe）；Wave 1 **视频生成**（至少 1 个旗舰 public 且实测出片；聊天模型不得因 video tool 404）；Wave 2 slides（独立入口，聊天主路径无新 tool）；对比 **S3 真并行分栏**（ST-10 重试已落地，S3 未做）；Notebook N3/N4 Studio；**文件上传对标官网最高档**（见 `open-webui-file-ingest-plan.md`，T0 未确认）；关 OWUI 图像模型 / Studio A4（多参考、流式）  
- **Don't**：ComfyUI、第二套 Pipe、重开 Web Search 三件套、466 全 public、同会话作图主路径、L3 三家 Live 并行、stock+realtime 双容器、把 RAG 当加分项、把 YouTube 转录当成 NotebookLM 达标、用 gpt-audio 冒充已接好的 Call S2S（GA-A：Pipe `/responses` 拒 `modalities.audio`）、未确认装 Tika / 扩 Direct MIME / 未确认改 Notebook 入口；**不要**把 Image Studio 绑进 OWUI 镜像或把 Studio 钥匙写入 Pipe / `api_configs`；**不要**用薄 Filter 指引冒充已补 Anthropic GitHub API；**不要**把 `$0.05` 工具门当最终账单上限去调高；**未确认不上** Search Controller 

---

## 固定 ID

Pipe 前缀：`open_webui_openrouter_integration.`

**置顶**：`perplexity.sonar-pro-search`、`perplexity.sonar-deep-research`、`anthropic.claude-opus-5`、`openai.gpt-5.6-sol-pro`

**21 public** 与 `scripts/stack_contract.py` 中 `PUBLIC_MODEL_IDS` 必须一致（picker = public）。
