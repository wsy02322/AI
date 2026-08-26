# AGENT-ONBOARDING — 新 Agent / 新 session 开工包

**当前 session 不要打开本文件。** Cloud 已注入根目录 `AGENTS.md`（宪法）。本页只给 **新 session / 新 Agent** 补操作手册。

## 阅读顺序

1. `AGENTS.md`（宪法，若尚未注入则先读）
2. `docs/SPEC.md`（产品契约 UX-* / ST-* / P0）
3. `docs/open-webui-optimized-plan.md`（波次）
4. 按任务打开：P0-D `docs/open-webui-notebook-youtube-plan.md`；Live `docs/open-webui-live-voice-screen-plan.md`；L0 `docs/open-webui-secret-key-persist-plan.md`
5. 动手前对照下面 **改实例前** 与 **不要做**

不要凭记忆重开 Web Tools，也不要同会话作图当主路径。登录优先 `OPENWEBUI_USERNAME`，不一定等于 email。

未确认 N2+ **不改** Notebook 入口形态、不装第二前端。N1（RAG 槽 + YouTube ingest）已允许执行。Live 顶级方案须单独 plan/确认：L1 不是语音终态；rbb L2 只补 S2S、不补持续屏享，也不能冒充两项都达标。无 OpenAI/Google Realtime 钥匙时 **不换** OWUI 镜像。**运维 L0**：env `WEBUI_SECRET_KEY=""`；容器重建后用户重登可接受；**不做** JWT 持久化 / Pipe 加密（K1/K2 冻结）。视频生成与 slides 仍为 Later 必做，**不是** YouTube 知识理解。

## 改实例前

1. 改 Pipe / Guard / catalog / 模型能力前：跑 `python3 scripts/verify_stack.py`。Banner / Suggested / 文案小改 **跳过**（脚本自带校验即可）  
2. 更新 Pipe valves：**merge**，禁止全量覆盖（会丢 `API_KEY`）  
3. 更新模型：`POST /api/v1/models/model/update` 必须带 `access_grants`  
4. **禁止** `POST /api/v1/models/sync` 空列表：OWUI 0.11 会按 payload **删掉**不在列表里的全部模型行  
5. **运维 L0（ST-OPS，已确认）** — 详见 `docs/open-webui-secret-key-persist-plan.md` §2  
   - env：`WEBUI_SECRET_KEY=""`。**不**持久化 JWT；容器重建 → **用户重登录（可接受）**。  
   - Pipe `API_KEY`：**merge 明文**恢复；API 保存后常为 `encrypted:`（catalog 正常即可）。  
   - **禁止** VPS 写入**新的**随机非空 `WEBUI_SECRET_KEY`（与 `encrypted:` Pipe key 冲突 → catalog 空）。  
   - **禁止**改 `openai.api_configs` 为 `enable: true`。  
   - catalog 空：merge 明文 OpenRouter key（`api_keys[0]` / TTS）→ `GET /api/models?refresh=true` → `restore_public_grants.py` → plan A / wave0 / banners → verify。  
   - **禁止**空 `POST /api/v1/models/sync`。  

## 常用脚本（加速器，不是 SPEC）

| 脚本 | 何时 |
|------|------|
| `scripts/verify_stack.py` | Pipe / Guard / catalog / 模型能力改动后。**不要**为 Banner / Suggested 文案跑 |
| `scripts/verify_compare_cross_model.py` | 对比 ST-10：Grok 密文回放给 Opus 不得 404；同模型续聊仍成功 |
| `scripts/patch_pipe_cross_model_reasoning.py` | S2′：扩 Pipe 重试门（content-only，不碰 valves） |
| `scripts/apply_wave0.py` | 重放 Wave 0：capabilities + Task 模型 |
| `scripts/apply_plan_a_hide_integrations.py` | Pipe 更新后 Integrations 又露出来 |
| `scripts/apply_model_catalog_visibility.py` | 仅保留 19 public 为 `is_active`；其余 Pipe catalog 禁用 |
| `scripts/apply_ui_guidance_banners.py` | Banner / Description / **清空 Suggested** / DEFAULT_MODELS |
| `scripts/restore_public_grants.py` | catalog 恢复后重建 19 public `access_grants`（不调用 sync） |
| `scripts/verify_live_baseline.py` | L1：TTS/STT 配置、短 TTS、Grok smoke、屏享 Banner |
| `scripts/run_ga_a_trial.py` | GA-A：MiniMax TTS vs gpt-audio（不改 Call/public；写 `open-webui-gpt-audio-trial-plan.md` §5） |
| `scripts/apply_notebook_n1.py` | N1：RAG embedding → OpenRouter、YouTube loader 语言、Knowledge 集合 |
| `scripts/ingest_youtube_notebook.py` | N1：YouTube 字幕/ASR + 视觉时间线写入 Knowledge |
| `scripts/verify_notebook_youtube.py` | N1 验收：RAG 槽、集合、字幕+shown、Banner |
| `scripts/apply_ops_l0.py` | **L0 执行**：Pipe key / api_configs / catalog / public grants（merge-only） |
| `scripts/verify_ops_l0.py` | **L0 验收**：ST-OPS 探针 |
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

## VPS / 容器运维（勿与 Pipe 脚本混用）

| 项 | 当前值 / 约束 |
|----|----------------|
| 容器 | `open-webui`，`127.0.0.1:8080`，镜像 `e97bf9531916` |
| Entrypoint | `/custom/entrypoint.sh`（BetterUI patch + 官方 `start.sh`） |
| 界面 CSS | 仓库 `wsy02322/open-webui-betterui` → `deploy/hetzner-custom/custom.css`。生产验收：`curl -sS https://micropigeon.com/static/custom.css \| head -8` 须为最新版本头（现目标 **v14.5**，composer 模型选择器只留 chevron）。**只改 Git 不够**，须写入 `/opt/open-webui/custom/custom.css` 并 `docker cp` 进容器。不要用该仓 `install.sh` 的 `docker run …:main`（会打掉钉死镜像）。 |
| env 文件 | `/root/open-webui.env` — `WEBUI_SECRET_KEY=""`（**L0：故意不持久化**） |
| `openai.api_configs` | 5 条，**全部 `enable: false`** |
| 重建后 | 通知用户重登 + agent 跑 verify / 必要时 merge Pipe key（§2 SOP） |

升配 / 重建容器前：备份 `webui.db`（护聊天/Knowledge，不护 JWT）；重建后跑 `verify_stack.py`。

## 不要做

- 在 `/root/open-webui.env` 写入**新的**随机非空 `WEBUI_SECRET_KEY`  
- 主动把 Pipe `API_KEY` 加密成 `encrypted:`（K1/K2 已冻结；Admin 误保存则 merge 回明文）  
- 启用 `openai.api_configs`（OpenRouter 直连槽）  
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
