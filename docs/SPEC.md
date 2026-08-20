# SPEC — Open WebUI 体验与稳定性契约

> **真相源（产品）**。实现可换；验收以 `scripts/verify_stack.py` 为准。  
> **关联**：`docs/open-webui-optimized-plan.md`（波次）、`docs/open-webui-delta-vs-stock.md`（已落地差异）

---

## 根本要求

1. **强能力**：对标 ChatGPT 最高档主干；过复杂或不稳定则不强求。  
2. **简单**：一种能力一个入口（换模型即换能力）。  
3. **稳定**：Sonar / 纯图像不得 tool calling 404；Pipe 更新后可重验。

---

## 用户契约（Now）

| ID | 必须 |
|----|------|
| UX-1 | **四格捷径**：Chat = Sol Pro / Opus；Quick search = Sonar Pro Search；Deep report = Sonar Deep Research；Images = 先切图像模型（Banana Pro / GPT Image 2 等） |
| UX-2 | 英文指引：两条 Banner + 关键 Description + 空对话 chips（「Select … first」） |
| UX-3 | Integrations **无** OR Web Tools / OR Image Gen / OWUI Web Search；保留 Direct Uploads；图像模型可有 native image filter |
| UX-4 | **19 个 public** 维持（对比用）；不缩到 6 |
| UX-5 | 新对话默认 = `open_webui_openrouter_integration.openai.gpt-5.6-sol-pro` |
| UX-6 | **路线 S**：作图 = 选图像模型。**不同会话作图当主路径**（不把 Sol/Opus 的 `image_generation` 打开来追 ChatGPT） |

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
| ST-8 | 后台 Task 模型（标题/补全）使用 Pipe 文本模型，不用幽灵直连 id |

## 明确 Later / Don't

- **Later 必做**：视频生成（换视频模型，少量 public）；slides（独立表面，不灌全模型 tools）  
- **Don't**：ComfyUI / inpainting、第二套 Pipe、重开 Web Search 三件套、466 全 public、同会话作图主路径  

---

## 固定 ID

Pipe 前缀：`open_webui_openrouter_integration.`

**置顶**：`perplexity.sonar-pro-search`、`perplexity.sonar-deep-research`、`anthropic.claude-opus-5`、`openai.gpt-5.6-sol-pro`

**19 public** 与 `scripts/stack_contract.py` 中 `PUBLIC_MODEL_IDS` 必须一致。
