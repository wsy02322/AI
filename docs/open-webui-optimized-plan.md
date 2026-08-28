# 优化计划：强能力 · 简单 · 稳定

> **状态**：Wave 0 **已应用到实例**。**P0 四条并列已写入契约**。P0-D **N1 已落地**（RAG + 视觉时间线；口播受 YouTube 风控）。Wave 1 视频生成 / Wave 2 slides 仍待单独开一轮。
> **日期**：2026-08-21  
> **宪法**：（1）顶级为目标；难则顶级与略降级一并提案、确认再选；（2）简单稳定易维护；（3）重大改动主动 plan/提案，确认后再执行（讨论≠执行）。  
> **用户约束**：维持 **19 个 public**；**P0-A 图像、P0-B 语音聊天、P0-C 屏享、P0-D Notebook/YouTube** 同为最高优先级；语音和屏享都受宪法复杂度确认门约束；**视频生成**与 **slides** 仍为后续必做（≠ YouTube 知识理解）。

---

## 0. 上一轮是不是「当前全部功能与状态」的全部处理？

**不是。** 上一轮 review 覆盖的是 **已定制主路径**（Pipe 四格、方案 A、Guard、图像、指引），**没有**把 OWUI 全部已开功能当成一张完整清单来处理。

| 已处理（主路径） | 未当作「要处理的功能」盘点 |
|------------------|----------------------------|
| Pipe + 466 模型 catalog | **原生 Images / Images Edit**（开着，模型 id 非 Pipe） |
| 方案 A、3 Guard | **Code Interpreter / Code Execution**（pyodide，开） |
| 19 public、4 置顶、DEFAULT_MODELS | **Audio STT/TTS**（OpenRouter whisper / tts，已配） |
| Banner / suggestions / Description | **RAG / Knowledge**（配置在，但 **未产品化**；embedding 槽仍 401 → 已升格 **P0-D**，见 notebook plan） |
| 关原生 Web Search、关 Direct Connections | **Memories / Notes / Automations / Calendar**（均 enable） |
| 明确不做：ComfyUI、inpainting、第二套 Pipe | **Task 模型**（标题/补全默认 `x-ai/grok-4.5`，非 Pipe） |
| | **视频**：catalog 约 24 个 + 20+ Filter，**均未 public** |
| | **Slides**：无定制，OWUI 侧能力未纳入契约 |
| | **OAuth / 社区分享 / Autocomplete / Follow-up** |
| | **gptsapi + 5 个禁用 OpenRouter slot**（运维噪音） |

因此：上一轮 = **聊天主路径体检**；本文件 = **全功能分层 + 优化后的路线**。

---

## 1. 全功能分层（Now / Later / Don't）

判定规则：能增强「最高档体验」且不显著伤害简单/稳定 → 做；伤害稳定或引入双路径 → 缓或关 UI；用户已声明后续必做 → **Later 必做**，不是 Don't。

### 1.1 Now（当前应对用户负责的表面）

| 能力 | 现状 | 对本阶段的处理 |
|------|------|----------------|
| 聊天 / 推理 | Sol Pro 默认；Opus 等 public | **维持**。Reasoning depth 已有 Banner |
| 快搜 / 深研 | 两档 Sonar public | **维持**。不重开 Web Tools / 原生 Web Search |
| 作图 | 9 个图像模型 public；切模型即作图 | **P0-A**：维持为主路径（见 §2） |
| 文件上传 | Direct Uploads | **维持** |
| 模型对比 | **19 public** | **维持 19**，不收到 6 |
| 稳定性护栏 | Guard + 方案 A + valves | **维持**；缺自动验收（§4 Wave 0） |
| 英文指引 | 2 Banner + 4 chips + Description | **维持**（Banner 数量不作为本阶段议题） |

### 1.2 Later（已承诺，单独一波，不塞进当前）

| 能力 | 现状 | 后续原则（预写，防走偏） |
|------|------|--------------------------|
| **视频生成**（Wave 1） | ~24 模型在 catalog；Filter 已装；**0 public** | **≠ YouTube ingest**。与作图同一契约：**换视频模型即生成**，不把 video tools 灌进 Sol/Sonar。先测 2～4 个旗舰再 public |
| **语音聊天**（P0-B） | L1 串联已落地（Whisper → 文本 → MiniMax），但不是 S2S | 与屏享同级最高。顶级标准 = 低延迟 + S2S + barge-in。rbb L2 是局部候选，重大改动须确认 |
| **屏幕共享**（P0-C） | L1 Call overlay 已有入口，但不是持续原生 Live 屏流 | 与语音同级最高。顶级标准 = 模型理解刚发生的画面变化。不能因上 rbb L2 而把静态 handoff 写成达标 |
| **Notebook / YouTube**（P0-D） | N1：RAG OpenRouter + Knowledge 视觉时间线 | 口播抓取受 YouTube 数据中心风控。N2+ 须再确认。详见 **`docs/open-webui-notebook-youtube-plan.md`** |
| **Slides** | 无产品契约 | 单独表面（Notes / 专用流程），**不要**给聊天模型再挂一套会 404 的 tool。可与 Notebook Studio 产物衔接，但 W2 仍单独确认 |
| 多轮图像连续性 | 有漂移 | P0-A 增强；仅当 verify 已稳定、且补丁能跟着 Pipe 更新走，才考虑轻量 preserve |
| 语音 STT/TTS | MiniMax + Whisper 已配 | Live L1 保留。Audio Overview **另测**，不默认够用 |

### 1.3 Don't（当前与后续都默认不做，除非三条要求改写）

| 项 | 原因 |
|----|------|
| ComfyUI / 蒙版 inpainting | 过复杂 |
| 第二套 Pipe / Workspace 包装 | 冲突 |
| 重开 OR Web Tools / 原生 Web Search | 已证不稳定 |
| 466 模型全部 public | 摧毁简单 |
| 同会话作图作为**第二条主路径** | 见 §2 |
| 锁死 OWUI/Pipe 版本当主策略 | 阻碍更新 |
| YouTube 转录+RAG 冒充 NotebookLM | 见 P0-D；NL-A ≠ 达标 |
| 视频生成与 YouTube ingest 混成一轮 | 两套产品 |

### 1.4 已开着、本阶段「不推广、不深挖、不随便关」

关全局开关容易误伤；这些不是当前用户契约的一部分：

- Memories、Calendar、Automations、Autocomplete、Follow-up、社区分享、OAuth  
- Notes / Knowledge：**P0-D 可能的宿主**；在 N2 入口拍板前仍不推广、不深挖、不随便关。不得当成已可用的 NotebookLM
- Code Interpreter（pyodide）：聊天模型可留；**Sonar / 纯图像 / 未来视频模型不应表现为可开的 tool**  
- 原生 Images：全局 enable=true，但 Sol Pro 的 `capabilities.image_generation=false`，用户主路径已不是「聊天里点 Image」

**处理方式**：Wave 0 只做 **按模型 capabilities 对齐契约**（防 404），不搞功能大扫除。

---

## 2. 同会话作图：如何抉择（对照三条要求）

### 2.1 两种产品

| | **路线 S（换模型）** | **路线 C（同会话）** |
|--|----------------------|----------------------|
| 用户怎么画 | 切到 Banana / GPT Image 2 / Seedream… 再下指令 | 留在 Sol Pro，像 ChatGPT 一样说 “draw…” |
| 实现 | Pipe 图像模型（已测通） | OWUI Native Images / `generate_image` tool |
| 当前线上 | **已是事实主路径**（Banner 也这么教） | 全局 Images 开着，但 Sol Pro **未**开 `image_generation` capability；引擎模型 id 还是非 Pipe 的 `google/gemini-3-pro-image` |

### 2.2 对照三条根本要求

**（1）强能力 — 路线 S 并不弱于 ChatGPT，在「对比模型」上更强。**

- ChatGPT 同会话作图：方便，但 **后端图像模型由产品代选**，用户很难对比 Banana vs GPT Image 2 vs Seedream。  
- 我们的用户 **会对比模型**（已决定维持 19 public）。同会话作图会把 9 个图像模型 **藏进一个开关**，反而削弱「超越官网」的那一点（可选最强图像模型）。  
- 单张质量：专用图像模型 ≥ ChatGPT 代选引擎。差距只在「少点一次模型切换」。  
- 该切换 **不够「极大复杂」**；复杂的是 tool 注入和第二条路径。

**（2）简单 — 一条路比两条路简单。**

- 已有 Banner：「Images → switch to Banana / GPT Image 2 first」。  
- 若再开同会话作图：用户会问「到底切模型还是点 Image？为什么 Sol 画出来和 Banana 不一样？」  
- 简单 = **一种能力一个入口**（与视频后续一致：切 Veo/Sora，而不是给聊天灌 video tool）。

**（3）稳定 — 同会话作图踩的是我们已爆过的坑。**

- 历史事故：`get_current_timestamp` / tool use 404。根因就是往 **不支持 tools 的模型** 灌 tools。  
- Native Images 依赖 tool calling；Sonar / 纯图像模型正是雷区。  
- 当前 Native 配置的模型 id **不是 Pipe id**，未实测，打开 capability 有回归风险。  
- Guard 能剥 tools，但不能让「聊天里出图」变得可靠；还多一条要维护的引擎路径。

### 2.3 决定（写入契约，后续 Agent 勿擅自改回）

**采用路线 S：作图 = 选图像模型。不同会话作图当主路径。**

- **不**把 Sol Pro / Opus 的 `image_generation` 打开来追 ChatGPT 交互。  
- Native Images 全局开关：Wave 0 **不强制关闭**（避免误伤后续实验）；**也不**写进用户指引。  
- 与后续视频同一模式：能力在模型上，不在聊天 tool 条上。

「少一次切换」换不来稳定，也换不来对比能力；对这批用户，**可点名最强图像模型**比 **ChatGPT 式一句话出图** 更接近原则 1。

---

## 3. 19 个 public：维持，并当产品资产

不缩名单。用法：

| 角色 | 模型 |
|------|------|
| 默认 / 对比锚 | Sol Pro；Opus、Sol、Grok 4.6、Kimi、DeepSeek、Qwen Max、Fable 等文本 |
| 搜索两档 | Sonar Pro Search / Deep Research |
| 作图对比 | Banana Pro/2、GPT Image 2、GPT-5.4 Image 2、Seedream Pro/Lite、MAI、Qwen Image、Grok Imagine |

指引继续以四格为 **入门捷径**（Banner），19 个为 **对比清单**。不要把 Banner 改成「只有四个能用」。

后续视频 public 时：**少量旗舰加入对比清单**，不要一次 24 个。

---

## 4. 优化后的实施波次（确认前仍不执行）

### Wave 0 — 护栏（小、稳，不改用户可见契约）

目标：现状可重复验收；防 Pipe 更新把 Sonar/图像打回 404。

| ID | 内容 |
|----|------|
| W0-1 | `scripts/verify_stack.py`：DEFAULT_MODELS、方案 A、Guard active、Sonar/图像无 tool 404、19 public、banners/suggestions |
| W0-2 | `docs/SPEC.md` + `AGENTS.md`：四格 + 19 public + 路线 S + **P0 四条** + 视频生成/slides = Later |
| W0-3 | 按模型 capabilities：**Sonar / 纯图像** 关闭会邀请用户开 tool 的项（`code_interpreter`；图像上多余的 `builtin_tools` / `terminal`）。**不**关 Sol Pro 的 code interpreter |
| W0-4 | `docs/VERSIONS.md` 记 OWUI / Pipe；Pipe 更新 Runbook：更新后跑 W0-1 + 现有 apply 脚本 |
| W0-5 | Task 默认模型：标题/补全若仍指向非 Pipe `x-ai/grok-4.5`，改为 Pipe 文本模型（避免后台任务走幽灵 id） |

**不做**：关全局 Image Gen、关 Code Interpreter、缩 public、改 Banner、连续性补丁、开视频 public。

### Wave 1 — 视频（必做，独立验收）

| ID | 内容 |
|----|------|
| W1-1 | 选 2～4 个视频旗舰实测（建议候选：Veo 3.1、Sora 2 Pro、Seedance / Kling 各一档） |
| W1-2 | 与图像相同：**Guard 剥 tools**；不挂 web_tools/image_gen；`filterIds` 仅 video native filter + 必要 uploads |
| W1-3 | 通过则 **少量 public** + 英文 Description（「Select this model first」）+ 可选 1 条 suggestion |
| W1-4 | Banner **不必**改成五格长文；Description 承担「视频要换模型」 |

失败则该模型不 public，不引入第二条「聊天里点 Video」路径。**禁止**与 P0-D YouTube 知识 ingest 混施工。

### Wave-N — Notebook / YouTube（P0-D，独立验收；**确认执行前不改实例**）

全文：`docs/open-webui-notebook-youtube-plan.md`。摘要：

| ID | 内容 |
|----|------|
| N0 | 契约与市场基准（**本轮已写入文档**） |
| N1 | 修 RAG 槽 + YouTube 字幕/ASR + **视觉时间线** + timestamp 验收 |
| N2 | 多源 Notebook + 源边界问答 + 与 Sonar 双入口 |
| N3 | Studio：Brief/FAQ/导图 + Audio Overview（TTS 另测） |
| N4 | 频道/播放列表、交互 Overview、Video Overview |

NL-A（转录+embedding）完成 **不得**标为 NotebookLM 达标。

### Wave 2 — Slides（必做，独立设计后再做）

| ID | 内容 |
|----|------|
| W2-1 | 先定表面：Notes / 导出 / 专用模型，**禁止**再给全模型灌 slides tool |
| W2-2 | 对照三条要求写一页方案，通过后再实施 |
| W2-3 | 与视频一样：可测、可关、不破坏四格+19 的聊天稳定性 |

### Wave 3 — 可选增强（非承诺；**不含** Notebook）

- 图像轻量连续性（canonical 上一张 + preserve 句）  
- Live STT/TTS 体验打磨（≠ Audio Overview）  
- Native Images 仅当有明确实验且 verify 全绿才碰  

---

## 5. 与旧计划的差异（避免再执行过时条目）

| 旧条目 | 新判定 |
|--------|--------|
| P0 关闭 `enable_image_generation` | **不做**。路线 S；全局开关先不动 |
| 全局关闭 code interpreter | **不做**。只收 Sonar/图像的 capability |
| 缩 public 到 6 | **撤销**。维持 19 |
| 清理 MODEL_ORDER_LIST 当 P1 | **降为顺便**。admin 列表已是 466 Pipe |
| 图像连续性 P2 马上做 | **推到 Wave 3**（不挡 P0-D） |
| 视频「不推广」 | **改为 Wave 1 必做**（生成 ≠ YouTube ingest） |
| RAG 是加分项 / Wave 3 | **撤销**。升格 **P0-D**；与 Sonar **双入口**，不抢同一按钮 |
| 同会话作图待拍板 | **已拍板：不做主路径**（§2.3） |
| 屏享优先、语音随后 | **撤销**。P0-B 语音与 P0-C 屏享同级；顶级统一方案与略降级方案都先 plan、再确认 |

---

## 6. 成功标准（分层）

**现在（Wave 0 后）**

- 新对话 = **仅 Grok 4.6**（不默认 compare）；四格置顶仍在；19 public 仍在；picker 仅 public 为 active  
- Sonar / 图像无 tool 404；Integrations 仍无 Web Tools / Image Gen / Web Search  
- `verify_stack` 可重复跑绿  

**Notebook / YouTube（N1–N2 后）**

- 无字幕 YouTube 能入库；引用可点到 `MM:SS`；「画面上有什么」能答 shown 而非只 transcript  
- 与 Sonar 入口分离；`verify_stack` / Live L1 不回归  

**视频生成（Wave 1 后）**

- 至少 1 个视频模型 public 且实测出片  
- 聊天模型不会因 video tool 404  

**Slides（Wave 2 后）**

- 有独立、可说明的入口；聊天主路径无新 tool 雷  

---

## 7. 文档地图

| 文件 | 角色 |
|------|------|
| **本文件** | 路线与波次 |
| `SPEC.md` | 体验与稳定性契约（含 P0） |
| `open-webui-notebook-youtube-plan.md` | **P0-D** Notebook / YouTube |
| `open-webui-live-voice-screen-plan.md` | **P0-B 语音 + P0-C 屏享** |
| `open-webui-delta-vs-stock.md` | 相对官方已落地差异 |
| `open-webui-disaster-recovery-rebuild-plan.md` | 重建/验收思路 |
| `open-webui-secret-key-persist-plan.md` | **运维 L0**（接受重登；JWT / Pipe 加密 K1+K2 冻结） |
| `open-webui-openrouter-image-continuity-plan.md` | 图像错误史；连续性仍属 Wave 3 |
| `open-webui-user-guidance-plan.md` | 英文指引意图 |

---

*Wave 0 已落地。P0-B/P0-C Live、P0-D Notebook、Wave 1、Wave 2 各按方案确认后再改实例；同为 P0 不代表绕过复杂度确认门。*
