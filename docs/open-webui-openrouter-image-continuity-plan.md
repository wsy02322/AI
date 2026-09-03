# Open WebUI + OpenRouter 图像能力记录与待办

> **状态**：已暂停执行，待用户确认后继续  
> **最后更新**：2026-08-18  
> **目的**：汇总已完成的修复、当前能力边界、连续性/锁定提升方案，以及社区方案与冲突分析

---

## 1. 背景与目标

- **平台**：Open WebUI（管理员可访问）
- **核心集成**：`OpenRouter for Open WebUI` Pipe（`open_webui_openrouter_integration`）
  - 来源：https://openwebui.com/posts/openrouter_integration_gpt_52_o3_o1_350_models_wit_9ac806c5
  - GitHub：https://github.com/rbb-dev/Open-WebUI-OpenRouter-pipe
- **用户目标**：获得等同或超越 ChatGPT / Gemini 官网最高订阅档的顶级图像生成与连续编辑能力
- **当前策略**：保留 OpenRouter Pipe 作为主集成，在其之上用 Filter 修补工具注入与端点路由问题

---

## 2. 已解决问题（已完成，勿重复执行除非回归）

### 2.1 `get_current_timestamp` / tool use 404

| 项目 | 说明 |
|------|------|
| **现象** | 除 Banana Pro 外多数 image models 报错：`No endpoints found that support tool use. Try disabling 'get_current_timestamp'.` |
| **根因** | `openrouter_web_tools` Filter 默认注入 Datetime；OWUI 内置 builtin tools 也会注入；纯图像模型不支持 chat/completions 上的 tool calling |
| **修复** | ① Pipe valves：`ENABLE_DATETIME=False`，`AUTO_DEFAULT_WEB_TOOLS_FILTER=False`；② 修补 `openrouter_web_tools`（`WEB_SEARCH` 默认 False，移除 DATETIME，inlet 对 image/video 模型早退）；③ 新建全局 Filter `openrouter_image_tool_guard`（priority=1，剥离 tools / builtin_tools / server_tools）；④ Pipe 层对 `image_output` / `video_generation` 模型禁止发送 tools |
| **注意** | 更新 Pipe valves 时必须 **merge** 而非全量覆盖，否则会清空 `API_KEY` |

### 2.2 GPT Image 2 端点错误

| 项目 | 说明 |
|------|------|
| **现象** | `openai/gpt-image-2 is an image generation model and cannot be used with the chat/completions endpoint. Use the /api/v1/images endpoint instead.` |
| **根因** | `gpt-image-*` 必须通过 OpenRouter `/api/v1/images`，不能走 chat/completions |
| **修复** | Pipe 补丁：`_is_openrouter_images_api_model`、`_chat_payload_to_images_payload`、`_stream_via_images_api`；streaming/non-streaming 路径优先走 images API，chat 失败时可 fallback |

### 2.3 当前验证状态（用户反馈）

| 模型 | 状态 |
|------|------|
| Google: Nano Banana 2 (Gemini 3.1 Flash Image) | ✅ 运行良好 |
| OpenAI: GPT Image 2 | ✅ 可出图；简单连续编辑可用（见 §4） |
| Google: Nano Banana 2 Lite | 曾在 tool guard 加强前仍报错，后续应已覆盖 |

---

## 3. 能力对比：当前方案 vs 官网最高档

| 维度 | ChatGPT / Gemini 官网 | 当前 Open WebUI + OpenRouter Pipe |
|------|----------------------|-----------------------------------|
| 出图质量 | 各模型原生上限 | 同源模型，质量可达同一档 |
| 多轮对话式编辑 | 产品层维护「当前画布」与上下文 | 依赖模型 + 请求里携带的参考图；全图 img2img 易有全局漂移（如夜空色调微变） |
| 局部编辑 / 蒙版 inpainting | 部分产品支持选区编辑 | 需 OpenAI Images Edit API + UI 蒙版；Pipe 默认未提供 |
| 参数连续性 | 隐式保持比例/风格 | 需显式继承 `aspect_ratio`、`size`、`quality` 等 |
| 工具链 | 内置 | 需 Native function calling + 正确 Filter 配置；image 模型需禁用 server/builtin tools |

**结论**：单张质量可对标；**连续性/锁定**是当前主要差距，属工程与产品层问题，不完全是模型能力问题。

---

## 4. 用户实测：GPT Image 2 连续编辑

**对话序列**（均成功，但有漂移）：

1. `a simple little frog drawing` → 青蛙简笔画
2. `add a little tiny girl` → 保留青蛙，加入小女孩
3. `make it night` → 夜景；用户观察到 **夜空颜色略有变化**（全图重绘典型现象）

**含义**：`input_references` + 上一轮 assistant 图作为参考已部分工作；若要「像素级锁定」需蒙版 inpainting 或更强 preserve 提示 + 参数继承。

---

## 5. 待实施方案（用户确认前 **不执行**）

### A. 请求载荷组装（Pipe 层，高优先级）

- **Prompt**：每轮只发 **最新用户指令**，不把整段历史拼进 images API 的 `prompt`（避免模型重解释全局）。
- **参考图**：`input_references` 仅使用 **上一轮 assistant 生成的图** 作为 canonical canvas（不用用户最初上传图或聊天里所有图）。
- **Preserve 句**：在 prompt 中自动附加简短保留说明（可配置开关），例如：`Keep the same composition, characters, and art style. Only apply: <user instruction>.`

### B. 图像存储（中优先级）

- 生成结果写入 OWUI `/api/v1/files/...`，避免巨大 `data:` URL 导致质量损失与引用断裂。
- 确保下一轮 `input_references` 使用稳定 file URL。

### C. 参数连续性（中优先级）

- 从上一轮生成继承：`aspect_ratio`、`size`、`output_format`、`quality`。
- `quality: high` 可作为选项，**不**强制默认（成本考虑）。

### D. 用户提示习惯（零代码）

- 用户可在指令中加：`keep the frog and the girl exactly the same, only change the sky to night`。
- 与 A 的自动 preserve 句互补。

### E. 产品级能力（长期 / 可选）

- **蒙版 inpainting**：OpenAI `images/edits` + OWUI 选区 UI（或 ComfyUI 工作流）。
- **双模型工作流**：聊天模型规划 + 专用图像模型执行（类似官网 Native `generate_image` / `edit_image`）。
- **ComfyUI**：最强可控性，运维成本高。

---

## 6. 社区已有方案与冲突分析

### 6.1 Open WebUI 原生（Admin > Experience > Images）

- **文档**：https://github.com/open-webui/docs/blob/main/docs/features/chat-conversations/image-generation-and-editing/usage.md
- **机制**：Native function calling 下，聊天模型调用 `generate_image` / `edit_image`，由 OWUI 配置的图像引擎执行。
- **与 Pipe 关系**：
  - **路径不同**：原生走 OWUI 图像引擎；Pipe 走 OpenRouter 直连（chat 或 images API）。
  - **可能冲突**：若 chat 模型同时启用 Image 集成 toggle 与 Pipe 图像模型，可能出现双路径或工具注入；image 专用模型应关闭 chat 侧 Image toggle，仅用 Pipe 模型。
- **连续性**：Native `edit_image` 由模型指定要编辑的 file URL，理论上比「纯模型自选历史图」更可控；Issue #19522 曾讨论 direct chat 与 native tools 差异。

### 6.2 Open WebUI GitHub Issues

| Issue | 要点 |
|-------|------|
| [#19522](https://github.com/open-webui/open-webui/issues/19522) feat: open router image create/edit | Direct chat 编辑有时不用上一轮生成图；Native tools + 配置引擎时由模型选 `edit_image` |
| [#23847](https://github.com/open-webui/open-webui/issues/23847) | Native mode 下 code interpreter 图不自动展示等（与图像 Pipe 路径无直接关系） |

### 6.3 OpenRouter 官方

- **Image Models 合集**：https://openrouter.ai/collections/image-models
- **Gemini Image**：支持 multi-turn、edits、`image_config`（aspect ratio 等）。
- **GPT Image 2**：专用 Images API；chat/completions 不支持。
- **Server Tools Image Gen**：Pipe 文档中的 legacy 路径；与当前「模型即 Pipe」路径重叠，且易与 tool guard 冲突 → **image 模型应禁用 server tools**。

### 6.4 rbb-dev Open-WebUI-OpenRouter-pipe（已安装）

- **不重复**：社区没有第二个同等规模的「350+ 模型 Pipe」；本方案是在此 Pipe **之上** 加 Filter 与补丁，而非替换。
- **Pipe 自带**：7 个 per-family image filters（Gemini Options、FLUX、Recraft 等）→ 管 **单次生成参数**，不管 **多轮 canonical canvas**。
- **拟新增 `openrouter_image_tool_guard`**：与 Pipe 自带 filters **互补**，不重复；注意全局 Filter 执行顺序（priority=1 尽早剥离 tools）。
- **拟新增连续性逻辑**：若实现在 Pipe 补丁内，属于 Pipe 未覆盖领域；若做成独立 Filter，需与 Pipe 的 images API 路由协调（最好在 Pipe 内改 `_chat_payload_to_images_payload`）。

### 6.5 其他社区

- **ComfyUI + OWUI**：最强局部控制，独立栈，不与 Pipe 冲突，运维重。
- **Direct Uploads filter**（Pipe 自带）：附件转 `input_file`，与 images API 的 `input_references` 不同用途。

---

## 7. 服务器侧资产清单（便于恢复上下文）

| 类型 | ID / 名称 | 作用 |
|------|-----------|------|
| Pipe | `open_webui_openrouter_integration` | OpenRouter 主集成 |
| Filter | `openrouter_web_tools` | Web Search / Fetch（Datetime 已弱化） |
| Filter | `openrouter_image_tool_guard` | 全局剥离 image/video 模型上的 tools |
| 动态 Filters | `openrouter_*_options` 等 | 单次生成参数（Gemini、Recraft…） |

**Valves 关键项（Pipe）**：

- `ENABLE_DATETIME=False`
- `AUTO_DEFAULT_WEB_TOOLS_FILTER=False`
- `API_KEY`：勿用全量 valves 更新覆盖

**临时编辑文件（若仍存在）**：`/tmp/pipe_live.py` — Pipe content 补丁用

---

## 8. 推荐实施顺序（下次继续时）

1. **确认路径**：继续「Pipe + images API 直连」还是叠加「Native edit_image + 单独引擎」双轨。
2. **A + C**：canonical canvas + 参数继承（改动集中在 Pipe 补丁，风险可控）。
3. **B**：file URL 持久化（若发现 reference 仍断链则优先）。
4. **实测**：同一青蛙三连编辑 + 检查夜空/肤色漂移。
5. **可选 E**：蒙版 inpainting 或 ComfyUI（仅当需要官网级局部锁定时）。

---

## 9. 决策检查清单（给用户确认）

- [ ] 是否继续在现有 Pipe 上补丁，还是 fork / 等上游合并？
- [ ] 是否启用 Native `edit_image` 双轨（需配置 OWUI 图像引擎与 OpenRouter）？
- [ ] 自动 preserve 提示词：默认开还是仅高级用户？
- [ ] `quality: high` 默认策略？
- [ ] 是否投入 ComfyUI / inpainting UI？

---

## 10. 图像模型测试与全员开放记录（2026-08-18）

### 测试结果

| 用户名称 | 实例模型 ID | 出图测试 | 全员可读 |
|----------|-------------|----------|----------|
| GPT Image 2 | `openai.gpt-image-2` | ✅ 约 14s | ✅ 已开放 |
| Nano Banana Pro | `google.gemini-3-pro-image` | ✅ 约 15s | ✅ 已开放 |
| Nano Banana 2 | `google.gemini-3.1-flash-image` | ✅ 约 23s | ✅ 已开放 |
| GPT-5.4 Image 2 | `openai.gpt-5.4-image-2` | ✅ 约 100s | ✅ 已开放 |
| Qwen Image 3.0 Pro | `qwen.qwen-image-3-pro` | ✅ 约 44s | ✅ 已开放 |
| MAI-Image-2.6 | `microsoft.mai-image-2.5-pro`（OpenRouter 无 2.6） | ✅ 约 29s | ✅ 已开放 |
| Grok Imagine 2.0 | `x-ai.grok-imagine-image-2.0` | ✅ 约 31s | ✅ 已开放 |
| Seedream 5.0 Pro | `bytedance-seed.seedream-5-0-pro` | ✅ 已修复（Images API 路由） | ✅ 已开放 |
| Seedream 5.0 Lite | `bytedance-seed.seedream-5-0-lite` | ✅ 同上 | ✅ 已开放 |
| Reve 2.1 | — | ❌ 实例中无此模型 | ❌ |

前缀均为 `open_webui_openrouter_integration.`。

### 开放方式

对通过测试的模型调用 `POST /api/v1/models/model/access/update`，设置：

```json
{
  "access_grants": [
    { "principal_type": "user", "principal_id": "*", "permission": "read" }
  ]
}
```

Pipe 默认将纯图像模型设为仅管理员可见；上述 7 个模型已显式设为所有用户可读。

### Seedream 5.0 修复（2026-08-18）

**现象**：`bytedance-seed/seedream-5-0-pro` 走 `chat/completions` 时 OpenRouter 返回 500 Internal Server Error；`seedream-4.5` 同路径正常。

**根因**：Seedream 5.x 在 OpenRouter 上应走专用 **Images API**（`/api/v1/images`），与 `gpt-image-*` 类似；Pipe 原先仅将 `gpt-image-*` 路由到 Images API。

**修复**（`open_webui_openrouter_integration` Pipe 补丁）：
1. `_is_openrouter_images_api_model` 增加 `seedream-5` 匹配。
2. `_chat_payload_to_images_payload` 将 `image_config.image_size` 映射为 Images API 的 `resolution`；对 Seedream 5.x 将非法 `4K` 降为 `2K`。

### 多轮对话 131072 token 溢出（2026-08-18 修复）

**现象**：多轮图像对话（尤其先由其他模型出大图再切到 Nano Banana 2 翻译/编辑）偶发：
`The input token count exceeds the maximum number of tokens allowed 131072.`

**根因**：历史消息中多张高分辨率图（`data:image` 或 `/api/v1/files/`）整段重复送入 Google；Pipe 的 `context-compression` 仅作用于 `/responses`，`/chat/completions` 回退路径原先无压缩。

**修复**：
1. 新建全局 Filter `openrouter_image_context_guard`（已启用）：仅保留「当前用户消息 + 紧邻上一轮 assistant 图」，其余历史图片替换为占位文本。
2. Pipe 补丁 `apply_chat_context_transforms`：在 `/chat/completions` 路径自动加 `transforms: ["middle-out"]` 与 `context-compression` 插件。

**2026-09-03 复发，上述两条挡不住**：`_materialize_image_entry` 的 dict-url 分支不落盘，Qwen Image 3 Pro 的生成图以 5.4MB `data:image` markdown 进了助手消息；Guard 按设计**保留**这张画布，middle-out 也保最近几轮 → 约 130 万文本 token → Nano Banana 2 报 400。

**已修（ST-13，2026-09-03 已执行）**：Pipe `IMAGE_DATA_URI_PERSIST_V1` 让 dict-url 的 `data:` 走落盘（失败则回退原 URI）；Guard `IMAGE_CONTEXT_DATA_URI_CAP_V1` 只剥画布里的 `data:image`、保留 file URL。验收 16 ok / 0 err：Qwen 出图回复 81 字符、Nano Banana 2 续聊 200、2MB 内联 data URI 200。详见 **`docs/open-webui-image-data-uri-persist-plan.md`**。

### 待处理
- **Reve 2.1**：当前 OpenRouter Pipe 目录中无此模型（Reve 主要在 fal.ai）；若需接入需单独集成。
- **MAI-Image-2.6**：OpenRouter 仅有 `mai-image-2.5` / `mai-image-2.5-pro`，已用 Pro 替代测试并开放。
- **Nano Banana Pro Preview**（`gemini-3-pro-image-preview`）：与正式版并列存在，未单独复测（API 限流）；正式版已测通并开放。

---

## 11. 方案 A：隐藏聊天 Integrations（2026-08-19）

**目标**：简约稳定。搜索用两档 Sonar，作图用专用图像模型；聊天栏不再露出 `OR Web Tools` / `OR Image Gen` / `Web Search`。

**已在实例应用**：

| 项 | 结果 |
|----|------|
| Pipe `AUTO_ATTACH_WEB_TOOLS_FILTER` / `AUTO_ATTACH_IMAGE_GEN_FILTER` | False |
| Pipe `AUTO_INSTALL_*` 对应两项 | False（防自动覆盖/重新启用） |
| Pipe `ENABLE_WEB_SEARCH` / `ENABLE_DATETIME` | False |
| Pipe `UPDATE_MODEL_CAPABILITIES` | False（防止 catalog 把 `web_search` 能力写回） |
| Filter `openrouter_web_tools` / `openrouter_image_gen` | 停用，未删除 |
| OWUI 原生 `ENABLE_WEB_SEARCH` | False |
| 全部 Pipe 模型 `filterIds` | 已剥离上述两 Filter；保留 `openrouter_direct_uploads` 与图像 native filter |

**可重复脚本**：`scripts/apply_plan_a_hide_integrations.py`（更新 valves 必须 merge，勿丢掉 `API_KEY`）。

**验证（API）**：Sonar Pro Search 与 Claude Opus 5 `POST /api/chat/completions` 均 200；样本模型 Integrations 仅 Direct Uploads（图像模型另有 generic/gemini image filter）。

**用户侧**：硬刷新或重新登录后，Sonar 聊天 Integrations 不应再出现 Web Tools / Image Gen / Web Search。

---

## 12. 参考链接

- OpenRouter Pipe 帖子：https://openwebui.com/posts/openrouter_integration_gpt_52_o3_o1_350_models_wit_9ac806c5
- Pipe GitHub：https://github.com/rbb-dev/Open-WebUI-OpenRouter-pipe
- OWUI 图像文档：https://github.com/open-webui/docs/blob/main/docs/features/chat-conversations/image-generation-and-editing/usage.md
- OpenRouter Image Models：https://openrouter.ai/collections/image-models
- OWUI Issue #19522：https://github.com/open-webui/open-webui/issues/19522
- **普通用户使用指引规划**：`docs/open-webui-user-guidance-plan.md`（2026-08-19）
- **灾备与从零重建规划**：`docs/open-webui-disaster-recovery-rebuild-plan.md`（2026-08-20）
