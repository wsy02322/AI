# Notebook · YouTube — 方案

> **状态**：v1 **N1 已执行**（2026-08-21）；N2+ 未做  
> **日期**：2026-08-21  
> **全局优先级**：**P0-D**，与 **图像生成（P0-A）**、**语音聊天（P0-B）**、**屏幕共享（P0-C）** 并列最高
> **旗舰源**：YouTube（转录不够；须视觉时间线 + 可点击 timestamp）  
> **宪法**：（1）媲美甚至超越市面最顶级（NotebookLM / Gemini Notebook 及视频向竞品）；（2）务必简单稳定、易维护；（3）重大改动先 plan、确认后再执行  

关联：`docs/SPEC.md`、`docs/open-webui-optimized-plan.md`、`docs/open-webui-live-voice-screen-plan.md`

---

## 0. 这不是什么

| 易混项 | 本方案 |
|--------|--------|
| Wave 1 **视频生成**（Veo / Sora） | 创作新视频。本方案是 **理解已有视频** |
| Live **Call overlay / S2S** | 实时说话。本方案的 Audio Overview 是 **异步播客** |
| Sonar **公网搜索** | 网上找新材料。本方案是 **用户选定源内 grounded 问答** |
| 粘贴 URL → Whisper → 丢进 Knowledge | **NL-A 地基**。单独完成 **不算** NotebookLM 达标 |
| Live Read Aloud（MiniMax + `alloy`） | 短句朗读。**不**等于双主持长音频 Overview |

---

## 1. 市面最顶级（验收基准，2026-08）

对标 **Gemini Notebook（原 NotebookLM）** 的产品面，并在 **YouTube** 上超过它官方明确的短板。

### 1.1 NotebookLM 已有（我们必须达到）

官方帮助中心（[添加源](https://support.google.com/notebooklm/answer/16215270)、[产品说明](https://support.google.com/notebooklm/answer/16164461)）：

| 能力 | 官方现状 |
|------|----------|
| 源类型 | PDF / 网页 / 音频 / Docs / Slides / **公开 YouTube URL** 等 |
| YouTube 导入 | **仅公开视频**；**必须已有字幕**（人工或自动）；**只导入文字 transcript**；无对白不支持；上传未满 72h 可能失败；字幕 &gt;50 万词失败 |
| 问答 | 只根据用户源作答；行内 citation |
| 播放 | 笔记本内嵌 YouTube 播放器（仍按 transcript 理解，不看画面） |
| Studio | Audio Overview（双主持、80+ 语言、可交互 Join）、Video Overview、Mind map、Reports（FAQ / study guide / briefing）、Flashcards / Quiz 等 |

### 1.2 NotebookLM 的 YouTube 短板（我们必须超过）

Google 原文：**Only the text transcript of the video is imported as a source.**  
无字幕则失败；不看幻灯片、演示、屏幕代码、图表。

市面视频向工具（Google AI Studio 抽帧、BibiGPT / NoteGPT 等）在「真的看视频」上往往强于 NotebookLM。宪法第 1 条要求 **达到 Studio 产品面，并在 YouTube 理解上超过 transcript-only**。

### 1.3 本栈 YouTube 旗舰必须同时成立

1. **可靠导入**：字幕优先；无字幕 **自动 ASR**；视频 / 播放列表 / 频道增量；去重与再同步。  
2. **真正看视频**：转录 + 说话人/章节；场景关键帧；幻灯片/代码/图表 **OCR**；视觉模型描述「画面有、口播没有」的内容。  
3. **可核查引用**：每条关键结论 → 具体视频 + `MM:SS`；区分 **说过 / 画面展示 / 模型推断**；点击跳到嵌入播放器；源中无则明确说无。  
4. **多源 Notebook**：YouTube + PDF + 网页 + 音频 + Office；可选源子集；跨视频共识/冲突。与 Sonar **两个入口**（My notebook vs Web search）。  
5. **Studio 产物**：Brief / Study guide / FAQ / 时间线；思维导图 / 闪卡 / 测验 / 报告；双主持多语言 Audio Overview。Video Overview 与交互主持放 N4。

---

## 2. 对照宪法的实现约束

| 原则 | 对本方案 |
|------|----------|
| 强能力 | 不得把 NL-A（转录+RAG）验收成 NL-B。YouTube 无视觉时间线 = 未达 P0 |
| 简单稳定 | **一套 OWUI**；ingest 用现有 OpenRouter 密钥优先；少新镜像。Knowledge / Notes 能承载就不要第二套前端 |
| 确认后再执行 | N1 已确认执行。**N2+ 未确认前** 不改入口形态、不装第二前端、不装新容器 |

**默认不做：** 为 Notebook 再开 LiveKit/Pipecat；第二套 OWUI；用 `web_tools` 抓 YouTube；空 `models/sync`；把 Notebook 聊天挂到 Sonar/图像模型上灌 tools；用 Call overlay 冒充 Audio Overview。

**难而复杂时先问（宪法第 1 条）：**

| 想冲的顶级 | 略降级但简单很多 | 须你点头才能降 |
|------------|------------------|----------------|
| 自建视觉抽帧 + OCR + 多模态索引 | 仅字幕/ASR + 时间戳 citation（仍强于 NotebookLM 的「无字幕即失败」） | YouTube **视觉**是否第一期就做 |
| 自研双主持长音频 | 单声线长摘要（现 MiniMax 未必够） | Audio Overview 是否 N3 首发 |
| 独立 Notebook HUD | OWUI Knowledge + 文档化入口 | 是否允许第二表面（须写入 SPEC） |

---

## 3. 与现有栈的关系

| 已有 | 可复用 | 不可假装已经够 |
|------|--------|----------------|
| OpenRouter Whisper turbo（Live STT） | 短音频烟测；**长视频须切片/时间戳/重试作业** | `verify_live_baseline.py` ≠ YouTube 批处理 |
| MiniMax `speech-2.8-turbo` + `alloy` | Read Aloud | 双主持、长一致性、多语言 Overview **须另选/实测** |
| Sonar citations | 公网搜叙事 | **不是**源内 timestamp |
| OWUI Knowledge / Notes（enable 但未产品化） | 可能的宿主 | 无契约、无 YouTube ingest、embedding 槽 **401** |
| `openrouter_direct_uploads` | 文件进聊天 | **不是** YouTube URL 一键入库 |
| 路线 S 作图 / Live L1 屏享 | 并行 P0，互不替代 | Notebook 内不要求聊天作图；Audio Overview 不走 Call |

**N1 落地（2026-08-21）：** RAG embedding 已改 OpenRouter `openai/text-embedding-3-small`（`process/web` 200）。Knowledge 集合 **YouTube Notebook**。烟测视频 `jNQXAC9IVRw` 写入 **shown** 时间线（YouTube storyboard 缩略图 + Gemini 描述：象、围栏、人物）。  

**未完成：** 本执行环境与 OWUI 主机均为数据中心 IP，YouTube 拦截 transcript / yt-dlp（bot-check）。口播 ASR 回退脚本已写好，需非封禁 IP 或 cookies 才能出 spoken。此限制写入验收，不把「无字幕失败」当产品终态。

---

## 4. 波次

### N0 — 契约与阻塞清单（已做）

| ID | 内容 | 通过 |
|----|------|------|
| N0-1 | SPEC / AGENTS / 总路线图写入 P0-D | 文档与本文一致 |
| N0-2 | 市场基准：NotebookLM transcript-only + Studio 产物 | §1 |
| N0-3 | 记录 RAG 槽、Live TTS ≠ Overview、视频生成 ≠ ingest | §0 §3 |
| N0-4 | 入口原则：Notebook ≠ Sonar；禁止第二套未文档化前端 | ST-NL-5 |

### N1 — YouTube 旗舰 ingest（**已执行，口播抓取受风控**）

| ID | 内容 |
|----|------|
| N1-1 | 修 RAG/embedding 指向 **可用** OpenRouter | **已做** |
| N1-2 | 公开 YouTube URL：字幕优先；无字幕 **ASR** | 脚本已写；数据中心 IP 被 YouTube bot-check，spoken 未写入烟测 |
| N1-3 | 视觉时间线 | **已做**：storyboard 缩略图 + Gemini 描述 + `youtu.be/?t=` |
| N1-4 | 问答引用：`MM:SS` + spoken / shown / inferred | shown 已有；spoken 待非封禁 IP |
| N1-5 | `scripts/verify_notebook_youtube.py` | **12 ok / 0 err** |

**降级门：** 若视觉链路「极大复杂」，先问是否 N1 只做字幕+ASR+timestamp，视觉放到 N1b。默认目标仍是视觉（用户把 YouTube 标成旗舰）。

### N2 — 多源 Notebook + grounded chat

| ID | 内容 |
|----|------|
| N2-1 | 集合：YouTube + PDF + 网页 + 音频 + Office；源子集选择 |
| N2-2 | 只根据选中源作答；越界拒答或「源中无」 |
| N2-3 | 与四格并列的 **文档化入口**（英文）。不把 RAG 塞进 Sonar 按钮 |
| N2-4 | 不破坏 `verify_stack` / ST-1～ST-10 / L1 Live |

### N3 — Studio 产物

| ID | 内容 |
|----|------|
| N3-1 | Brief / Study guide / FAQ / 时间线（结构化导出） |
| N3-2 | Audio Overview：≥2 声线、可下载；TTS **另测**，不默认 MiniMax+alloy 已够 |
| N3-3 | 思维导图 / 闪卡 / 测验 / 报告（可分批 public） |

### N4 — 超出 NotebookLM 的 YouTube 广度

| ID | 内容 |
|----|------|
| N4-1 | 播放列表 / 频道增量索引 |
| N4-2 | 交互式 Audio Overview（收听中提问） |
| N4-3 | Video Overview（可与 Wave 1 视频生成模型衔接，但是 **Studio 产物**，不是「换模型生成空视频」） |

---

## 5. 拟写入 SPEC 的 ID（落地时再生效）

| ID | 必须 |
|----|------|
| ST-NL-1 | YouTube 源 = 转录 **加** 视觉时间线；无字幕走 ASR，不以「无 caption 失败」为终态 |
| ST-NL-2 | 关键结论必须可点击 timestamp；区分 spoken / shown / inferred |
| ST-NL-3 | Notebook 问答 **源边界内**；不把 Sonar / web_tools 当知识库 |
| ST-NL-4 | Audio Overview ≠ Call overlay；Live TTS 配置 **不得**为 Overview 被覆盖 |
| ST-NL-5 | Notebook 入口 **文档化**；禁止未写入 SPEC 的第二前端；不与四格搜索按钮混用 |
| ST-NL-6 | YouTube **知识 ingest** ≠ Wave 1 **视频生成**；两套 public / Filter 不得混用 |
| ST-NL-7 | N2+ **未确认执行前** 不上生产；N1 允许改 `rag.*` |

---

## 6. 与 P0-A / P0-B / P0-C 的关系

四条最高优先级 **并列**，不是让 Live 给 Notebook 让出带宽；每次改实例仍按宪法单独 plan/确认：

| 轨 | 现在 | 下一步（均须确认才改实例） |
|----|------|----------------------------|
| **P0-A 图像** | 路线 S 已落地 | 连续性等仍属增强，不挡 Notebook |
| **P0-B 语音聊天** | L1 串联可用，未达 S2S / barge-in | 与屏享同级；顶级统一或局部方案见 Live plan，复杂度须确认 |
| **P0-C 屏享** | L1 入口可用，未达持续原生屏流 | 与语音同级；不能用 rbb L2 的语音收益冒充达标 |
| **P0-D Notebook** | N1 已落地 | 下一确认：N2 入口 / 非封禁 IP 补 spoken |

不把 gpt-audio 改 Call、不把 Realtime 镜像、不把 Notebook 塞进同一轮施工。

---

## 7. 请你拍板（执行轮）

规划本轮 **已按你的确认写入仓库**。要动实例时请再选：

| | 选项 |
|--|------|
| **E0** | 只保持文档；实例不动（当前） |
| **E1** | 执行 N1（修 RAG 槽 + YouTube 字幕/ASR + **视觉时间线** + timestamp 验收） |
| **E1′** | 执行 N1 但视觉放到 N1b（须你明确接受这条略降级） |
| **E2** | N1 之后立刻排 N2 入口（Knowledge/Notes vs 文档化新表面） |

**现在不做：** N3/N4 施工、L2 Realtime、为 Overview 改全局 TTS、YouTube 生成模型 public。

---

## 8. 参考

- Gemini Notebook 添加源：https://support.google.com/notebooklm/answer/16215270  
- Audio Overview：https://support.google.com/notebooklm/answer/16212820  
- Video Overview：https://support.google.com/notebooklm/answer/16454555  
- YouTube + Audio 源发布：https://blog.google/innovation-and-ai/products/notebooklm-audio-video-sources/  
- 本仓库：`docs/SPEC.md`、`docs/open-webui-optimized-plan.md`、`docs/open-webui-live-voice-screen-plan.md`

*未确认执行步之前不改实例。*
