# AGENTS.md — 本仓库怎么动 Open WebUI

先读 **`docs/SPEC.md`**，再读 **`docs/open-webui-optimized-plan.md`**。P0-D 读 **`docs/open-webui-notebook-youtube-plan.md`**。不要凭记忆重开 Web Tools，也不要同会话作图当主路径。

## 宪法（所有动作）

1. 媲美甚至超越 ChatGPT / Grok 等最顶级付费档。特别困难复杂：**先确认**是否改用略微降级、简单稳定特别多的方案。  
2. 务必简单和稳定，优先易维护。  
3. 重大改动：先 plan，确认后再执行。

**P0 四条并列**：图像生成、**语音聊天**、**屏幕共享**、Notebook/YouTube（各有独立 plan）。语音与屏享同级，不得写成「屏享 → 语音」；两者都受宪法复杂度确认门约束。视频生成与 slides 仍为 Later 必做，**不是** YouTube 知识理解。维持 **19 个 public**。

未确认 N2+ **不改** Notebook 入口形态、不装第二前端。N1（RAG 槽 + YouTube ingest）已允许执行。Live 顶级方案须单独 plan/确认：L1 不是语音终态；rbb L2 只补 S2S、不补持续屏享，也不能冒充两项都达标。无 OpenAI/Google Realtime 钥匙时 **不换** OWUI 镜像。

## 改实例前

1. 跑 `python3 scripts/verify_stack.py`（需要 `OPENWEBUI_URL` / `OPENWEBUI_USERNAME` / `OPENWEBUI_PASSWORD`）  
2. 更新 Pipe valves：**merge**，禁止全量覆盖（会丢 `API_KEY`）  
3. 更新模型：`POST /api/v1/models/model/update` 必须带 `access_grants`  
4. **禁止** `POST /api/v1/models/sync` 空列表：OWUI 0.11 会按 payload **删掉**不在列表里的全部模型行  
5. Pipe `API_KEY` 在 DB 里是 `encrypted:…`。`WEBUI_SECRET_KEY` 一变（换容器 / HTTPS 重建）catalog 会空。用仍明文的 OpenRouter 密钥（TTS/STT）**merge** 回 valves，再 `GET /api/models?refresh=true`，最后 `scripts/restore_public_grants.py`  

登录优先 `OPENWEBUI_USERNAME`，不一定等于 email。

## 常用脚本（加速器，不是 SPEC）

| 脚本 | 何时 |
|------|------|
| `scripts/verify_stack.py` | 任何改动后；Pipe 更新后 |
| `scripts/verify_compare_cross_model.py` | 对比 ST-10：Grok 密文回放给 Opus 不得 404；同模型续聊仍成功 |
| `scripts/patch_pipe_cross_model_reasoning.py` | S2′：扩 Pipe 重试门（content-only，不碰 valves） |
| `scripts/apply_wave0.py` | 重放 Wave 0：capabilities + Task 模型 |
| `scripts/apply_plan_a_hide_integrations.py` | Pipe 更新后 Integrations 又露出来 |
| `scripts/apply_ui_guidance_banners.py` | Banner / Description / chips / DEFAULT_MODELS |
| `scripts/restore_public_grants.py` | catalog 恢复后重建 19 public `access_grants`（不调用 sync） |
| `scripts/verify_live_baseline.py` | L1：TTS/STT 配置、短 TTS、Grok smoke、屏享 Banner |
| `scripts/apply_notebook_n1.py` | N1：RAG embedding → OpenRouter、YouTube loader 语言、Knowledge 集合 |
| `scripts/ingest_youtube_notebook.py` | N1：YouTube 字幕/ASR + 视觉时间线写入 Knowledge |
| `scripts/verify_notebook_youtube.py` | N1 验收：RAG 槽、集合、字幕+shown、Banner |
| `scripts/fix_sonar_tool_guard.py` | 误启用 web_tools 时的补丁参考 |

## Pipe 更新 Runbook

1. 在 Admin 更新 Pipe（或按上游安装）  
2. **Merge** valves：见 SPEC ST-4～ST-6（`apply_plan_a_hide_integrations.py` 会 merge）  
3. 确认 3 个 Guard 仍 global active：`image_tool_guard`、`image_context_guard`、`search_native_tool_guard`  
4. `python3 scripts/apply_plan_a_hide_integrations.py`  
5. `python3 scripts/apply_ui_guidance_banners.py`  
6. `python3 scripts/apply_wave0.py`  
7. `python3 scripts/verify_stack.py` 全绿  
8. 更新 `docs/VERSIONS.md` 的日期与 Pipe 指纹  

若 Images API / Seedream 路由丢失：按 `docs/open-webui-openrouter-image-continuity-plan.md` **模式**补，不要盲贴旧 `content`。

## 不要做

- 给 Sonar / 纯图像灌 tools  
- 打开 Sol Pro `image_generation` 来做同会话作图  
- 一次 public 全部视频模型  
- 关全局 Code Interpreter（只收 Sonar/图像的 capability）  
- 把 RAG / Knowledge 当加分项或与 Sonar 做成同一个按钮  
- 把 YouTube 字幕/转录当成 NotebookLM 级验收  
- 把视频生成（Wave 1）与 YouTube ingest（P0-D）混成一条施工
- 用 Call overlay / 现有 MiniMax Read Aloud 冒充 Audio Overview  
- 未确认就把 gpt-audio 或 Realtime 镜像当 Call S2S 落地  
- 把语音聊天排在屏享之后，或用 rbb L2 的语音收益掩盖持续屏享缺口

Filter inlet：**priority 数字越小越先执行**；剥 tools 的 Guard 要靠后。
