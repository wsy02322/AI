# AGENTS.md — 本仓库怎么动 Open WebUI

灾后 / 新会话重建先读 **`docs/open-webui-rebuild-archive.md`**。日常改实例：先读 **`docs/SPEC.md`**，再读 **`docs/open-webui-optimized-plan.md`**。P0-D 读 **`docs/open-webui-notebook-youtube-plan.md`**。文件录入（Later，T0 未确认）读 **`docs/open-webui-file-ingest-plan.md`**。运维密钥 **L0 轻量档**见 **`docs/open-webui-secret-key-persist-plan.md`**（**已确认**：接受重登、不持久化 JWT、Pipe key 明文）。不要凭记忆重开 Web Tools，也不要同会话作图当主路径。独立 Gemini Live 新产品在 `handoff/gemini-live-standalone/`，**不要并进 OWUI 文档**。

**ST 编号**：**ST-11** = Fable 同模型续聊（unsigned thinking）；**ST-12** = Follow-up 芯片关；**ST-13** = 生成图落盘为 file URL（`docs/open-webui-image-data-uri-persist-plan.md`，**已执行**）。不要复用号。

## 宪法（所有动作）

1. 媲美甚至超越 ChatGPT / Grok 等最顶级付费档。特别困难复杂：把**顶级方案**和**略降级、简单稳定特别多的方案**一并提案，**先确认再选**。禁止只提降级；禁止把顶级方案留到用户追问之后。  
2. 务必简单和稳定，优先易维护。  
3. 重大改动：先写成 plan 并**主动提案**，确认后再执行。写 plan、讨论、把能力缺口摆上台 **不是** 执行，未问也要提。禁止把本条理解成「未问就不提」；禁止未确认就改实例 / Pipe / 入口形态。

目标仍是顶级；降级必须是用户点头的权衡，不是执行者自行放弃。发现与顶级档的能力缺口、或明显更强的实现路径时，当场主动提案（含是否升主线、风险、和不做的代价）；未确认不得动手。

**P0 四条并列**：图像生成、**语音聊天**、**屏幕共享**、Notebook/YouTube（各有独立 plan）。语音与屏享同级，不得写成「屏享 → 语音」；两者都受宪法复杂度确认门约束。视频生成与 slides 仍为 Later 必做，**不是** YouTube 知识理解。维持 **19 个 public**。

未确认 N2+ **不改** Notebook 入口形态、不装第二前端。N1（RAG 槽 + YouTube ingest）已允许执行。Live 顶级方案须单独 plan/确认：L1 不是语音终态；rbb L2 只补 S2S、不补持续屏享，也不能冒充两项都达标。无 OpenAI/Google Realtime 钥匙时 **不换** OWUI 镜像。**运维 L0**：env `WEBUI_SECRET_KEY=""`；容器重建后用户重登可接受；**不做** JWT 持久化 / Pipe 加密（K1/K2 冻结）。

## 改实例前

1. 跑 `python3 scripts/verify_stack.py`（需要 `OPENWEBUI_URL` / `OPENWEBUI_USERNAME` / `OPENWEBUI_PASSWORD`）  
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

登录优先 `OPENWEBUI_USERNAME`，不一定等于 email。

## 常用脚本（加速器，不是 SPEC）

| 脚本 | 何时 |
|------|------|
| `scripts/verify_stack.py` | 任何改动后；Pipe 更新后 |
| `scripts/verify_compare_cross_model.py` | 对比 ST-10：Grok 密文回放给 Opus 不得 404；同模型续聊仍成功 |
| `scripts/verify_fable_thinking_replay.py` | ST-11：Fable 两轮续聊不得 `cannot be modified` |
| `scripts/patch_pipe_cross_model_reasoning.py` | S2′：扩 Pipe 重试门（content-only，不碰 valves） |
| `scripts/patch_pipe_fable_thinking_replay.py` | ST-11：Fable unsigned thinking（content-only，不碰 valves；S2′ 之后跑） |
| `scripts/patch_pipe_image_data_uri_persist.py` | **ST-13**：生成图 data URI 落盘（content-only；marker 已在则 no-op） |
| `scripts/patch_guard_image_context_data_uri.py` | **ST-13** 兜底：Guard 只剥画布里的 `data:image`，保留 file URL |
| `scripts/verify_image_data_uri_persist.py` | **ST-13** 验收：marker + 出图落盘 + Banana 续聊 200 + 2MB data URI 200 |
| `scripts/apply_wave0.py` | 重放 Wave 0：capabilities + Task 模型 + **Follow-up 关** |
| `scripts/apply_plan_a_hide_integrations.py` | Pipe 更新后 Integrations 又露出来 |
| `scripts/apply_model_catalog_visibility.py` | picker = 19 public + 两个 extra Gemini；其余 Pipe catalog 禁用 |
| `scripts/apply_ui_guidance_banners.py` | **一条** `usage-guide-v3` + Description + **空** chips + DEFAULT_MODELS |
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
5. `python3 scripts/apply_ui_guidance_banners.py`（现网契约 = **一条** `usage-guide-v3` + 空 chips；**不要**写回已废弃的双条 v2 Banner）  
6. `python3 scripts/apply_wave0.py`（含 Follow-up 关）  
7. `python3 scripts/patch_pipe_cross_model_reasoning.py`（S2′ marker 已在则 no-op）  
8. 若 Pipe 丢了 Fable marker：`python3 scripts/patch_pipe_fable_thinking_replay.py`（已有 `FABLE_UNSIGNED_SUMMARY_V1` 则 no-op） 
9. 若 Pipe 丢了 ST-13 marker：`python3 scripts/patch_pipe_image_data_uri_persist.py`（已有 `IMAGE_DATA_URI_PERSIST_V1` 则 no-op） 
10. `python3 scripts/verify_stack.py` 全绿；图像相关另跑 `python3 scripts/verify_image_data_uri_persist.py` 
11. 更新 `docs/VERSIONS.md` 的日期与 Pipe 指纹 

若 Images API / Seedream 路由丢失：按 `docs/open-webui-openrouter-image-continuity-plan.md` **模式**补，不要盲贴旧 `content`。

## VPS / 容器运维（勿与 Pipe 脚本混用）

| 项 | 当前值 / 约束 |
|----|----------------|
| 容器 | `open-webui`，`127.0.0.1:8080`，镜像 `e97bf9531916` |
| Entrypoint | `/custom/entrypoint.sh`（BetterUI patch + 官方 `start.sh`） |
| env 文件 | `/root/open-webui.env` — `WEBUI_SECRET_KEY=""`（**L0：故意不持久化**） |
| `openai.api_configs` | 5 条，**全部 `enable: false`** |
| 重建后 | 通知用户重登 + agent 跑 verify / 必要时 merge Pipe key（§2 SOP） |
| chrome overlay | `deploy/owui-ui/custom.css`（全宽 + 藏头像 + 助手左边 **单层 4px**） |

**`custom.css` 有两份**（容器里看得见 ≠ 浏览器加载到）：

| 角色 | 路径 |
|------|------|
| bind 源 | `/opt/open-webui/custom/custom.css` → `/app/build/static/custom.css` |
| 正在 serve | `/app/backend/open_webui/static/custom.css` |

启动时从 build 拷到 `STATIC_DIR`。热改 **两处一起写**，然后 `curl` 公网 `Last-Modified` / 文件尾巴；**不要为了 CSS 重启**（L0 会逼重登）。助手只改 `#messages-container .message-listitem:has(.chat-assistant)` 为 `4px`；`.flex-auto.pl-1` 保持 `0`（父子 padding 会相加）。OWUI 0.11 是 `.chat-assistant` / `.markdown-prose`，不是 `.prose`。操作说明见 `deploy/owui-ui/README.md`。

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
- 未确认装 Tika / 扩 Direct MIME（见 `docs/open-webui-file-ingest-plan.md`）
- 把 Follow-up 关（ST-12）和 Fable 续聊（ST-11）写成同一个 ST 号
- 新增第二份 Agent 入口（不要再写 `AGENT-ONBOARDING.md`；本文件即入口）
- 只改 bind 的 `custom.css` 就当页面已生效（必须 `curl` 公网 `Last-Modified`）
- 把助手左边距叠在 `message-listitem` **和** `.flex-auto.pl-1` 两层
- 用 `.prose` / `.message-assistant` 当 OWUI 0.11 选择器
- 把 4px 左边距写进 BetterUI patch（overlay 在 `deploy/owui-ui/`）
- 让生成图以 `data:image` 进助手消息（ST-13：必须落盘成 `/api/v1/files/`）
- 给 `openrouter_image_context_guard` 的 data URI 剥离加尺寸阈值（1MB base64 本身已超 131k）

Filter inlet：**priority 数字越小越先执行**；剥 tools 的 Guard 要靠后。
