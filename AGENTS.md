# AGENTS.md — 本仓库怎么动 Open WebUI

**GitHub 几乎仅用于灾后重建**：规格、脚本、现网钉子。不是产品演示集，也不靠 PR 里的截屏/录屏证明现网。日常改实例仍动生产；入库是为了下次能按文档+脚本把站点救回来。

灾后 / 新会话重建先读 **`docs/open-webui-rebuild-archive.md`**，再读 **`docs/SPEC.md`**。指定文本模型联网见 **`docs/open-webui-text-web-search-plan.md`**（**ST-14 / WS-A 已确认**；用薄 `openrouter_text_web_search`，不要重开 broad Web Tools）。P0-D 读 **`docs/open-webui-notebook-youtube-plan.md`**。文件录入（Later，T0 未确认）读 **`docs/open-webui-file-ingest-plan.md`**。运维密钥 **L0**见 **`docs/open-webui-secret-key-persist-plan.md`**。官方 **0.11.3** 升级见 **`docs/open-webui-upgrade-0113-plan.md`**。独立画图 Studio 见 **`docs/open-webui-image-studio-plan.md`** 与 **`image-studio/`**（IS-A+ 施工中；独立容器，**不改** OWUI / Pipe / picker）。不要凭记忆重开 Web Tools，也不要同会话作图当主路径。独立 Gemini Live 在 `handoff/gemini-live-standalone/`，**不要并进 OWUI 文档**。

**ST 编号**：**ST-11** = Fable 同模型续聊（unsigned thinking）；**ST-12** = Follow-up 芯片关；**ST-14** = 指定文本模型薄 Web Search。不要把这三条写成同一个号。

## 宪法（所有动作）

1. 媲美甚至超越 ChatGPT / Grok 等最顶级付费档。特别困难复杂：把**顶级方案**和**略降级、简单稳定特别多的方案**一并提案，**先确认再选**。禁止只提降级；禁止把顶级方案留到用户追问之后。  
2. 务必简单和稳定，优先易维护。  
3. 重大改动：先写成 plan 并**主动提案**，确认后再执行。写 plan、讨论、把能力缺口摆上台 **不是** 执行，未问也要提。禁止把本条理解成「未问就不提」；禁止未确认就改实例 / Pipe / 入口形态。

目标仍是顶级；降级必须是用户点头的权衡，不是执行者自行放弃。发现与顶级档的能力缺口、或明显更强的实现路径时，当场主动提案（含是否升主线、风险、和不做的代价）；未确认不得动手。

**P0 四条并列**：图像生成、**语音聊天**、**屏幕共享**、Notebook/YouTube（各有独立 plan）。语音与屏享同级，不得写成「屏享 → 语音」；两者都受宪法复杂度确认门约束。视频生成与 slides 仍为 Later 必做，**不是** YouTube 知识理解。维持 **21 个 public**（留下的家族最新 id，含两条 Gemini）。

未确认 N2+ **不改** Notebook 入口形态、不装第二前端。N1（RAG 槽 + YouTube ingest）已允许执行。Live 顶级方案须单独 plan/确认：L1 不是语音终态；rbb L2 只补 S2S、不补持续屏享，也不能冒充两项都达标。无 OpenAI/Google Realtime 钥匙时 **不换 Realtime 镜像**。官方 **0.11.3** 已落地（钉 digest，不是 `:latest`），见 **`docs/open-webui-upgrade-0113-plan.md`**。**运维 L0**：env `WEBUI_SECRET_KEY=""`；容器重建后用户重登可接受；**不做** JWT 持久化 / Pipe 加密（K1/K2 冻结）。

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
| `scripts/patch_pipe_cross_model_reasoning.py` | S2′：扩 Pipe 重试门（content-only，不碰 valves） |
| `scripts/patch_pipe_fable_thinking_replay.py` | ST-11：Fable / Anthropic 同模型续聊剥 unsigned thinking（content-only） |
| `scripts/verify_fable_thinking_replay.py` | ST-11 验收 |
| `scripts/apply_wave0.py` | 重放 Wave 0：capabilities + Task 模型 + **Follow-up 关** |
| `scripts/apply_plan_a_hide_integrations.py` | Pipe 更新后 Integrations 又露出来 |
| `scripts/apply_model_catalog_visibility.py` | picker = 21 public（留下家族最新 id）；其余 Pipe catalog 禁用 |
| `scripts/apply_ui_guidance_banners.py` | **一条** `usage-guide-v4` + Description + **空** chips + DEFAULT_MODELS |
| `scripts/restore_public_grants.py` | catalog 恢复后重建 21 public `access_grants`，并剥掉契约外 `*` read（不调用 sync） |
| `scripts/verify_live_baseline.py` | L1：TTS/STT 配置、短 TTS、Grok smoke、屏享 Banner |
| `scripts/apply_notebook_n1.py` | N1：RAG embedding → OpenRouter、YouTube loader 语言、Knowledge 集合 |
| `scripts/ingest_youtube_notebook.py` | N1：YouTube 字幕/ASR + 视觉时间线写入 Knowledge |
| `scripts/verify_notebook_youtube.py` | N1 验收：RAG 槽、集合、字幕+shown、Banner |
| `scripts/apply_ops_l0.py` | **L0 执行**：Pipe key / api_configs / catalog / public grants（merge-only） |
| `scripts/verify_ops_l0.py` | **L0 验收**：ST-OPS 探针 |
| `scripts/probe_text_web_search_readiness.py` | WS-A 确认前只读：server tools / Guard 顺序 / 候选文本模型 |
| `scripts/apply_text_web_search.py` | ST-14：安装/挂载薄 Web Search Filter（`--mode install|canary|attach|final`） |
| `scripts/rollback_text_web_search.py` | ST-14：从模型卸下薄 Filter 并停用，不删 Function |
| `scripts/verify_text_web_search.py` | ST-14：按 mode 验收 attachment / default / 排除模型 |
| `scripts/run_text_web_search_canary.py` | ST-14 W2：Gemini Flash 真实工具事件 + 图像零回归 |
| `scripts/run_text_web_search_smoke.py` | ST-14 W3：7 个 allowlist 模型 Search + Fetch |
| `scripts/fix_sonar_tool_guard.py` | 误启用 web_tools 时的补丁参考 |
| `image-studio/scripts/verify_studio.py` | Image Studio：登录现网 OWUI、无钥匙 generate/edit 须 503 |
| `image-studio/scripts/probe_capabilities.py` | IS0：OpenRouter Images catalog（无需 Studio key） |

## Pipe 更新 Runbook

1. 在 Admin 更新 Pipe（或按上游安装）  
2. **Merge** valves：见 SPEC ST-4～ST-6（`apply_plan_a_hide_integrations.py` 会 merge）  
3. 确认 3 个 Guard 仍 global active：`image_tool_guard`、`image_context_guard`、`search_native_tool_guard`  
4. `python3 scripts/apply_plan_a_hide_integrations.py`  
5. `python3 scripts/apply_ui_guidance_banners.py`（现网契约 = **一条** `usage-guide-v4` + 空 chips；**不要**写回 v3 / 双条 v2）  
6. `python3 scripts/apply_wave0.py`（含 Follow-up 关）  
7. 若 Pipe 丢了 Fable marker：`python3 scripts/patch_pipe_fable_thinking_replay.py`（已有 `FABLE_UNSIGNED_SUMMARY_V1` 则 no-op）  
8. 若薄 Web Search 丢了：`python3 scripts/apply_text_web_search.py --mode final`（已有 `TEXT_WEB_SEARCH_FILTER_V1` 且 7 模型 default-on 则只校验）  
9. `python3 scripts/verify_stack.py` 全绿  
10. 更新 `docs/VERSIONS.md` 的日期与 Pipe 指纹  

若 Images API / Seedream 路由丢失：按 `docs/open-webui-openrouter-image-continuity-plan.md` **模式**补，不要盲贴旧 `content`。

## VPS / 容器运维（勿与 Pipe 脚本混用）

| 项 | 当前值 / 约束 |
|----|----------------|
| 容器 | `open-webui`，`127.0.0.1:8080`，官方 **v0.11.3** |
| 镜像钉子 | image id `129f4038ec70`；RepoDigest `ghcr.io/open-webui/open-webui@sha256:751b617714b91e4cfd0186a509c72480c858e012976103b09a30dad053c36175`。**不要**漂 `:latest` / `:main`。无 Realtime 钥匙时 **不换** Realtime 镜像。过程见 `docs/open-webui-upgrade-0113-plan.md` |
| Entrypoint | `/custom/entrypoint.sh`（BetterUI patch + 官方 `start.sh`） |
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
- 未确认装 Tika / 扩 Direct MIME（见 `docs/open-webui-file-ingest-plan.md`）
- 未确认就把 Studio 绑进 OWUI 镜像 / `/custom/entrypoint.sh`，或把 Studio 钥匙 merge 进 Pipe / `openai.api_configs`  
- 未确认关 OWUI 图像模型 / 改 `stack_contract`（Studio 先双轨）
- 把新家族塞进 picker / public；留下的家族升到 catalog 最新 id，且全部 public
- 把 Follow-up 关（ST-12）、Fable 续聊（ST-11）和文本联网（ST-14）写成同一个 ST 号
- 激活 broad `openrouter_web_tools` / OWUI native Web Search 来冒充 ST-14
- 把截屏 / 录屏当验收，或把演示媒体塞进 GitHub
- 新增第二份 Agent 入口（不要再写 `AGENT-ONBOARDING.md`；本文件即入口）

Filter inlet：**priority 数字越小越先执行**；剥 tools 的 Guard 要靠后。

## Cursor Cloud specific instructions

- 本仓库 **几乎仅用于灾后重建**。PR / commit 写规格与可重放脚本；不要为了「给 GitHub 看」去截屏、录屏、堆 walkthrough 媒体。
- **一般不要截屏或录屏**。现网验收以 `scripts/verify_stack.py` 等脚本 / API 探针为准。
- 仅在少数情况才截屏或录屏：脚本证明不了用户可见结果（例如纯 CSS/布局），或用户明确要求看画面。
