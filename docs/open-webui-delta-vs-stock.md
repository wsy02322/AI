# 相对纯官方 Open WebUI 的全部改动记录

> **基准（Stock）**：Open WebUI **0.11.0**，无第三方 Pipe、无自定义 Function、无本仓库脚本与文档所描述的配置。  
> **对比对象（本实例）**：`https://micropigeon.com`（探针日期 **2026-08-21**）  
> **本文件地位**：相对官方的 **单一真相源**；灾备规格见 `open-webui-disaster-recovery-rebuild-plan.md`。

---

## 1. 基准与范围说明

### 1.1 什么算「纯官方」

| 层面 | Stock 默认 |
|------|------------|
| OWUI 核心 | 官方镜像/发行版 0.11.0，未改源码 |
| 模型连接 | 可选 OpenAI 兼容端点；无 OpenRouter Pipe |
| Functions | 无 `openrouter_*`、无 `open_webui_openrouter_integration` |
| 全局 Filter | 无自定义 `openrouter_image_tool_guard` 等 |
| 聊天 Integrations | 若安装 Pipe 默认会出现 OR Web Tools / Image Gen 等 |
| 界面指引 | 无本实例定制 Banner / Description / Chips |
| Git 仓库 | 无 `scripts/` 运维脚本与 `docs/` 定制文档 |

### 1.2 什么算「我们的改动」

凡下列任一情况均记入本文：

1. **Admin / DB 配置**与 stock 不同  
2. **安装的第三方 Pipe**及其 Valves  
3. **新增或修改的 Filter Function**（含 Guard 与 Pipe 自带 Filter 的补丁）  
4. **Pipe `content` 内联补丁**（非上游 Pipe 默认）  
5. **模型 metadata**（public、置顶、description、`filterIds`）  
6. **UI 配置**（Banners、suggestions、默认 metadata）  
7. **本 Git 仓库**中的文档与可重复脚本  

**不在本文范围**：OWUI 官方仓库内的代码 diff（我们未 fork OWUI 核心）；密钥/API Key **只记「已配置」**，不记值。

---

## 2. 平台与 Admin 配置（相对 Stock）

### 2.1 版本与连接

| 项 | Stock 典型值 | 本实例 |
|----|-------------|--------|
| OWUI 版本 | 0.11.0 | **0.11.0**（`GET /api/version`） |
| `ENABLE_OPENAI_API` | 视安装 | **true** |
| OpenAI 兼容端点 | 0–1 个 | **6 个 slot**；仅 **slot 0** `enable=true` |
| Slot 0 `base_url` | — | `https://api.gptsapi.net/v1`（密钥已配置） |
| Slot 1–5 `base_url` | — | `https://openrouter.ai/api/v1`（重复条目；**均 `enable=false`**；密钥已配置） |
| `ENABLE_DIRECT_CONNECTIONS` | 常为 true | **false**（`GET /api/v1/configs/connections`） |
| Pipe 模型目录规模 | 无 | **466** 个 `open_webui_openrouter_integration.*` 模型 |

**含义**：日常流量经 **gptsapi.net 代理槽** 进入；OpenRouter 直连槽保留但未启用。Pipe 仍通过自身 `API_KEY` 调 OpenRouter（与 Admin OpenAI 连接独立）。

### 2.2 原生 Web Search / Retrieval

| 项 | Stock | 本实例 |
|----|-------|--------|
| `features.enable_web_search`（`/api/config`） | 可能 true | **false** |
| `retrieval.web.ENABLE_WEB_SEARCH` | 可能 true | **false** |

**产品意图**：搜索由 **Sonar Pro Search / Deep Research** 承担，不在聊天栏暴露 OWUI 原生 Web Search（方案 A）。

### 2.3 默认模型与排序（未完全 Pipe 化）

| 项 | Stock | 本实例 |
|----|-------|--------|
| `DEFAULT_PINNED_MODELS` | 空或自选 | **4 个 Pipe 模型**：Sonar Pro Search、Sonar Deep Research、Claude Opus 5、GPT-5.6 Sol Pro |
| `DEFAULT_MODELS` | 自选 | **`grok-4.6` + `claude-opus-5`**（双默认，便于对比；逗号分隔 Pipe id） |
| `MODEL_ORDER_LIST` | — | **10 项**；置顶 Pipe 四格 + 若干直连模型 |

**说明**：新对话默认 Grok 4.6 + Opus 5 双模型（2026-08-20）。后台 Task 仍只用 Grok 4.6。

### 2.4 原生 Image Generation（Admin > Images）

本实例主路径为 **Pipe 图像模型 + Images API**，非 OWUI 原生图像引擎。原生 Images 设置未作为主力能力文档化；若启用会与 Pipe 路径重叠（见 `open-webui-openrouter-image-continuity-plan.md` §6.1）。

---

## 3. 第三方集成：OpenRouter Pipe

### 3.1 安装来源

| 项 | 值 |
|----|-----|
| Function id | `open_webui_openrouter_integration` |
| 类型 | **Pipe** |
| 状态 | **active** |
| 社区来源 | [Open WebUI 帖子](https://openwebui.com/posts/openrouter_integration_gpt_52_o3_o1_350_models_wit_9ac806c5) |
| 上游仓库 | https://github.com/rbb-dev/Open-WebUI-OpenRouter-pipe |
| 模型 id 前缀 | `open_webui_openrouter_integration.` |

**相对 Stock**：整包 Pipe + 约 **466** 个虚拟模型为 **新增**；Stock 无此集成。

### 3.2 Pipe Valves（非默认 / 运维关键）

以下相对 Pipe **上游默认** 已显式设置（探针 2026-08-20）：

| Valve | 本实例 | 目的 |
|-------|--------|------|
| `API_KEY` | **已配置** | OpenRouter 调用 |
| `AUTO_ATTACH_WEB_TOOLS_FILTER` | **false** | 不自动挂 Web Tools |
| `AUTO_ATTACH_IMAGE_GEN_FILTER` | **false** | 不自动挂 Image Gen |
| `AUTO_INSTALL_WEB_TOOLS_FILTER` | **false** | Pipe 更新时不重装 Web Tools |
| `AUTO_INSTALL_IMAGE_GEN_FILTER` | **false** | 同上 Image Gen |
| `AUTO_DEFAULT_WEB_TOOLS_FILTER` | **false** | 不把 Web Tools 设为模型默认 |
| `ENABLE_DATETIME` | **false** | 避免 `get_current_timestamp` tool |
| `ENABLE_WEB_SEARCH` | **false** | Pipe 层不启 Web Search server tools |
| `UPDATE_MODEL_CAPABILITIES` | **false** | 防止 catalog 把 `web_search` 写回模型 |

**运维约束**：更新 Valves 必须 **merge** 字段，禁止全量覆盖（否则可能清空 `API_KEY`）。

### 3.3 Pipe `content` 内联补丁（相对上游 Pipe）

探针确认 Pipe 源码 **包含** 下列逻辑（上游默认未必有）：

| 补丁域 | 说明 |
|--------|------|
| `_is_openrouter_images_api_model` | 识别须走 Images API 的模型（含 `gpt-image-*`、`seedream-5*`） |
| `_stream_via_images_api` / images 路由 | `gpt-image-*`、`seedream-5*` **不走** `chat/completions` |
| Seedream 5.x | `image_config.image_size` → `resolution`；非法 `4K` 降为 `2K` |
| `apply_chat_context_transforms` | chat 路径增加 `middle-out`、`context-compression` |
| 图像/视频模型 | Pipe 层对 `image_output` / `video_generation` 禁止发送 tools |
| `COMPARE_CROSS_MODEL_REASONING_V1` | 扩 `_should_retry_dropping_signed_reasoning`：400/404 跨模型加密 reasoning 拒绝时剥密文内部重试（对比 ST-10；不关 `PERSIST_REASONING_TOKENS`） |

详细错误历史见 `open-webui-openrouter-image-continuity-plan.md` §2、§10。

---

## 4. Functions / Filters 全清单

### 4.1 相对 Stock 的新增规模

| 类别 | 数量（2026-08-20） |
|------|-------------------|
| `openrouter_*` + Pipe | **38** 个 Function |
| 其中 **active=false** | `openrouter_web_tools`、`openrouter_image_gen` |
| 自定义 Guard（非 Pipe 自带） | **3** 个（见 §4.3） |

### 4.2 Pipe 自带 Filter（安装 Pipe 时带入）

| id | 类型 | active | 作用摘要 |
|----|------|--------|----------|
| `openrouter_direct_uploads` | filter | **true** | 附件 → `input_file` |
| `openrouter_web_tools` | filter | **false** | OR Web Search / Fetch（方案 A 停用） |
| `openrouter_image_gen` | filter | **false** | OR Image Gen server tools（方案 A 停用） |
| `openrouter_fusion` | filter | true | Pipe 自带融合逻辑 |
| `openrouter_image_filter_generic` | filter | true | 通用图像参数 |
| `openrouter_image_filter_gemini` | filter | true | Gemini 图像选项 |
| `openrouter_image_filter_grok` | filter | true | Grok 图像选项 |
| `openrouter_image_filter_recraft` / `recraft_v3` | filter | true | Recraft 系列 |
| `openrouter_image_filter_sourceful` / `v25` | filter | true | Sourceful 系列 |
| `openrouter_video_*`（20+） | filter | true | 各视频模型参数 Filter |

图像模型通常挂 **family 对应** 的 `openrouter_image_filter_*`；文本/Sonar 模型 **不** 挂图像 Filter。

### 4.3 自定义 Guard Filter（我们新增 / 改写）

| id | active | priority（代码默认 / valves） | 作用 |
|----|--------|-------------------------------|------|
| `openrouter_image_tool_guard` | **true** | **1** | 对 image/video 模型 **剥离** `tools`、`builtin_tools`、`server_tools` |
| `openrouter_image_context_guard` | **true** | **2** | 多轮图像：仅保留当前用户消息 + 上一轮 assistant 图；其余历史图替换占位 |
| `openrouter_search_native_tool_guard` | **true** | **99**（valves **100**） | 对 Sonar/Perplexity 等 **最后** 再剥 tools，防其他 Filter 晚注入 |

**相对 Stock**：不存在；为修复 `No endpoints found that support tool use` 与 131072 token 溢出。

**执行顺序要点**：Filter inlet **priority 数字越小越先执行**；Guard 须在 **剥离** 侧靠后，否则 per-model Filter 会在 Guard 之后再次注入 server tools。

### 4.4 `openrouter_web_tools` / `openrouter_image_gen` 补丁状态

仓库脚本 `scripts/fix_sonar_tool_guard.py` 设计为在二者 `inlet` 对 Sonar 模型 **早退**（`_is_search_native_model`）。

**探针 2026-08-20**：二者 `content` 中 **未见** `_is_search_native_model`（补丁可能未写入或被 Pipe 更新覆盖）。当前二者 **已停用**，风险由全局 Guard + 方案 A 承担；若重新启用须先重跑补丁或等价逻辑。

---

## 5. 方案 A：Integrations 简约化

**目标**：聊天栏 **不出现** OR Web Tools、OR Image Gen、OWUI Web Search；**换模型即换能力**。

| 动作 | 状态 |
|------|------|
| Pipe Valves 关闭 auto-attach / auto-install（§3.2） | ✅ |
| `openrouter_web_tools`、`openrouter_image_gen` **停用**（未删除） | ✅ |
| OWUI 原生 `ENABLE_WEB_SEARCH` | ✅ false |
| 全库 Pipe 模型 `filterIds` 去掉上述两 Filter | ✅ |
| 模型 `capabilities.web_search` | ✅ false |
| 保留 `openrouter_direct_uploads` | ✅ |
| 图像模型保留 native image filter | ✅ |

**用户可见 Integrations**：典型文本/Sonar 模型仅 **OR Direct Uploads**；图像模型另有对应 `openrouter_image_filter_*`。

**可重复脚本**：`scripts/apply_plan_a_hide_integrations.py`

---

## 6. 模型层改动

### 6.1 产品四格（置顶 + 指引）

| 能力格 | 模型（UI 名） | Pipe model id |
|--------|---------------|---------------|
| Quick search | Perplexity: Sonar Pro Search | `…perplexity.sonar-pro-search` |
| Deep report | Perplexity: Sonar Deep Research | `…perplexity.sonar-deep-research` |
| Chat / 推理 | GPT-5.6 Sol Pro、Claude Opus 5 | `…openai.gpt-5.6-sol-pro`、`…anthropic.claude-opus-5` |
| Images | Nano Banana Pro、GPT Image 2 等 | 见 §6.2 |

### 6.2 全员可读（public）模型 — 19 个

Pipe 默认多将纯图像模型设为仅管理员；下列已设 `access_grants: principal_id=* read`（2026-08-20）：

| 模型 id 后缀 | 备注 |
|-------------|------|
| `anthropic.claude-fable-5` | 文本 |
| `anthropic.claude-opus-5` | 文本旗舰 |
| `deepseek.deepseek-v4-pro-0813` | 文本 |
| `moonshotai.kimi-k3` | 文本 |
| `openai.gpt-5.6-sol` | 文本 |
| `openai.gpt-5.6-sol-pro` | 文本旗舰 |
| `perplexity.sonar-pro-search` | 快搜 |
| `perplexity.sonar-deep-research` | 深度 |
| `qwen.qwen3.8-max` | 文本 |
| `x-ai.grok-4.6` | 文本 |
| `google.gemini-3-pro-image` | Nano Banana Pro |
| `google.gemini-3.1-flash-image` | Nano Banana 2 |
| `openai.gpt-image-2` | 图像 |
| `openai.gpt-5.4-image-2` | 图像 |
| `bytedance-seed.seedream-5-0-pro` / `lite` | Seedream 5 |
| `microsoft.mai-image-2.5-pro` | 图像（无 2.6） |
| `qwen.qwen-image-3-pro` | 图像 |
| `x-ai.grok-imagine-image-2.0` | 图像 |

其余 **~447** 个 Pipe 模型仍为管理员或未 public。

### 6.3 `filterIds` 模式（相对 Stock + 相对 Pipe 默认）

| 模型类型 | 典型 `filterIds` | 不含 |
|----------|------------------|------|
| Sonar / 文本旗舰 | `["openrouter_direct_uploads"]` | `openrouter_web_tools`、`openrouter_image_gen` |
| 图像模型 | `openrouter_direct_uploads` + `openrouter_image_filter_*` | 同上 |
| `capabilities.web_search` | **false** | — |

### 6.4 模型英文 Description（用户可见）

脚本 `scripts/apply_ui_guidance_banners.py` 中 `DESCRIPTIONS` 已写入下列模型（探针 2026-08-20 与脚本一致）：

- Sonar Pro Search — QUICK SEARCH 说明 + 勿用于日常聊天  
- Sonar Deep Research — DEEP REPORT + 2–10 分钟等待  
- GPT-5.6 Sol Pro — DEFAULT CHAT + Reasoning depth  
- Claude Opus 5 — 推理/长文 + 非 live web  
- Nano Banana Pro / Nano Banana 2 / GPT Image 2 — PRIMARY/ALTERNATE IMAGE + 先切模型  

### 6.5 研究档产品决策（已执行，非 Stock）

- **快搜**：`perplexity.sonar-pro-search`（非 Workspace 包装、非第二套 Pipe）  
- **深度**：`perplexity.sonar-deep-research`  
- **Sonar 不挂** `openrouter_web_tools`（Perplexity 不支持 chat completions tool calling）  
- **不装** 第二套 Pipe / admirito 包装  

---

## 7. 界面与体验（UI）

### 7.1 General UI Banners（相对 Stock：无）

两条 **不可 dismiss**（`dismissible: false`）英文 Banner（`POST /api/v1/configs/banners`）：

| id | type | 作用 |
|----|------|------|
| `usage-pick-model-v2` | info | 四格选模型：Chat / Quick search / Deep report / Images |
| `usage-reasoning-depth-v2` | warning | Valves → Reasoning depth → high/xhigh |

已替换早期拼写错误 banner（`resoning`）。

### 7.2 Prompt suggestions（空对话 chips）

**设计**（`apply_ui_guidance_banners.py`）：4 条英文 chip；第 1 条为 WeChat 反馈（`@dalapi`），其余 3 条含 “Select … first”。

**存储**：`POST /api/v1/configs/suggestions`；导出键 **`ui.prompt_suggestions`**（flat，非 `export.ui` 嵌套）。`GET /api/config` 的嵌套 `ui.prompt_suggestions` 可能为空，以 export 为准。

**状态（2026-08-20）**：**4 条**已写入；重跑 `scripts/apply_ui_guidance_banners.py` 可恢复。

### 7.3 用户面向语言

- 所有指引文案：**英文**（Banner、Description、Chips 设计）  
- Agent/运维文档：**中文**（本仓库 `docs/`）

### 7.4 Reasoning depth

沿用 Pipe **UserValves** 标签 **Reasoning depth**（`none` … `xhigh`）；Banner 引导难题用 **high/xhigh**。

---

## 8. 本 Git 仓库（相对 Stock 空仓库）

### 8.1 文档

| 文件 | 内容 |
|------|------|
| `docs/open-webui-delta-vs-stock.md` | **本文件** — 相对官方全量差异 |
| `docs/open-webui-openrouter-image-continuity-plan.md` | 图像修复、public 列表、方案 A、错误史 |
| `docs/open-webui-user-guidance-plan.md` | 界面英文指引设计与决策 |
| `docs/open-webui-disaster-recovery-rebuild-plan.md` | 灾备 v2：规格 + verify 思路 |

### 8.2 可重复脚本

| 脚本 | 作用 |
|------|------|
| `scripts/fix_sonar_tool_guard.py` | Sonar 防 tool 注入：Guard priority、web_tools/image_gen 早退、Sonar filterIds |
| `scripts/apply_plan_a_hide_integrations.py` | 方案 A 一键：Valves merge、停用 Filter、剥模型 filterIds、关原生 Web Search |
| `scripts/apply_ui_guidance_banners.py` | **DEFAULT_MODELS** + Banners + Description + Prompt chips + 校验 |

**环境变量**：`OPENWEBUI_URL`、`OPENWEBUI_PASSWORD`、`OPENWEBUI_USERNAME`（优先于 email 登录）。

### 8.3 尚未入库（讨论中，非当前差异）

- `SPEC.md`、`AGENTS.md`、`scripts/verify_stack.py`、`docs/VERSIONS.md`（见灾备规划 P0）

---

## 9. 已修复问题 ↔ 改动映射（相对 Stock 会踩的坑）

| 现象 | 我们的改动 |
|------|------------|
| `No endpoints found that support tool use` + `get_current_timestamp` | Guard 剥 tools；Valves 关 DATETIME/Web Search；方案 A 停用 web_tools/image_gen |
| `gpt-image-*` chat endpoint 错误 | Pipe Images API 路由 |
| `seedream-5` OpenRouter 500 | 同上 + resolution 映射 |
| 多轮图像 131072 token | `openrouter_image_context_guard` + chat `middle-out` / context-compression |
| Pipe 更新后 Sonar 再坏 | `AUTO_INSTALL_*=false` + 重跑 guard / 方案 A |
| `model/update` 500 | 请求带完整 `access_grants` 等字段 |

---

## 10. 已知未改 / 技术债（仍与「理想 Stock+定制」有差距）

| 项 | 状态 |
|----|------|
| `DEFAULT_MODELS` 指向 Pipe Sol Pro | **已修**（2026-08-20） |
| Prompt suggestions | **4 条**（export `ui.prompt_suggestions`） |
| Task 模型（标题/补全） | **Grok 4.6** Pipe（Wave 0 后自 Sol Pro 下调成本） |
| Sonar / 纯图像 `code_interpreter` 等 | **已关**（Wave 0）；Sol Pro / Opus 的 code interpreter **保留** |
| `web_tools`/`image_gen` Sonar 早退补丁 | **探针未见**；当前靠停用 + Guard |
| 图像画布连续性（canonical canvas） | **未实现** — 见 continuity plan §5 |
| 蒙版 inpainting / ComfyUI | **未实现** |
| Reve 2.1 | OpenRouter 无模型 |
| 全局原生 Image Gen | **已关**（`ENABLE_IMAGE_GENERATION=false`；路线 S） |
| OWUI 核心 fork | **无** |

---

## 11. 相对官方的一页摘要

```
Stock OWUI 0.11.0
    │
    ├─ + OpenRouter Pipe（466 模型）+ API_KEY
    ├─ + 3 个自定义 Guard Filter
    ├─ + Pipe content 补丁（Images API、Seedream 5、上下文压缩）
    ├─ − 停用 web_tools / image_gen（方案 A）
    ├─ − 原生 Web Search OFF
    ├─ − Direct Connections OFF
    ├─ Admin：6 OpenAI slots（仅 gptsapi slot0 启用）
    ├─ 19 public 模型 + 4 置顶 + 英文 Description
    ├─ 2 条常驻英文 Banner
    ├─ filterIds：仅 direct_uploads（+ 图像 native filter）
    └─ Git：docs + 3 个 apply/fix 脚本
```

**体验契约**：用户通过 **选模型** 切换聊天 / 快搜 / 深度 / 作图；难题调 **Reasoning depth**；Integrations **简约**（无 Web Tools 三件套）。

---

## 12. 验证与复现探针

```bash
export OPENWEBUI_URL=...
export OPENWEBUI_USERNAME=...
export OPENWEBUI_PASSWORD=...

# 方案 A
python3 scripts/apply_plan_a_hide_integrations.py

# UI 指引
python3 scripts/apply_ui_guidance_banners.py

# Sonar guard（若重新启用 web_tools）
python3 scripts/fix_sonar_tool_guard.py
```

手动抽检：

- `GET /api/version` → 0.11.0  
- `GET /api/config` → `enable_web_search=false`  
- `GET /api/v1/configs/banners` → 两条 `usage-*-v2`  
- Sonar / 图像模型聊天 → 无 tool use 404  
- 样本模型 Integrations → 无 OR Web Tools / Image Gen  

---

## 13. 文档交叉引用

| 主题 | 文档 |
|------|------|
| 图像细节与测试列表 | `open-webui-openrouter-image-continuity-plan.md` |
| 界面文案设计意图 | `open-webui-user-guidance-plan.md` |
| 灾备与重建流程 | `open-webui-disaster-recovery-rebuild-plan.md` |

---

*本文随实例变更应更新；重大改动后请 bump 文首探针日期并提交 git。*
