# Open WebUI 灾后重建存档（给 Agent）

> **用途**：站点没了、容器重建、或新 Agent 接手时，先读这一份，再动实例。  
> **GitHub**：几乎仅用于灾后重建（本文件 + SPEC + 脚本）。不是演示库；重建成功不靠截屏。  
> **探针**：2026-09-01T11:16Z，`https://micropigeon.com`，OWUI **0.11.0**。  
> **策略**：规格 + 脚本验收 + DB 备份。不锁死某一版 Function 全文；不靠全量配置快照。  
> **密钥不入库**。OpenRouter / TTS / RAG 的 key 由运维注入；本文件只记「已配置」与形状。

重建成功 ≠ 字节级复刻 2026-09-01。重建成功 = **`docs/SPEC.md` 契约** + 本文件 **§2 钉子** + **`scripts/verify_stack.py` 全绿**。§3 是当天现场；与 git 脚本不一致处见 §4，不要盲目用旧 apply 覆盖用户后来改过的 Banner。

---

## 0. 新 Agent 先读（顺序）

1. 本文件  
2. `AGENTS.md`（禁令、Pipe merge、空 `models/sync`、L0）  
3. `docs/SPEC.md`（UX / ST / P0 / Later / Don't）  
4. `docs/VERSIONS.md`（指纹）  
5. `docs/open-webui-secret-key-persist-plan.md` §2（容器重建 SOP）  
6. 按任务再读：图像 continuity、Live、Notebook、文件录入  

独立 Gemini Live 新产品在 `handoff/gemini-live-standalone/`，**与本 OWUI 重建无关**。

---

## 1. 不可逆 vs 可再填

| 资产 | 灾后 |
|------|------|
| `webui.db` / data volume（聊天、Knowledge 文件、用户） | **必须从备份还原**。脚本重建不出聊天记录 |
| OpenRouter API key | 控制台重开，**merge** 进 Pipe `API_KEY`（明文输入；保存后 DB 常为 `encrypted:`） |
| JWT / 登录态 | **不必备份**。L0：`WEBUI_SECRET_KEY=""`，重建后 **用户重登** |
| Pipe / Guard / 21 public / Banner / Task | 本仓库脚本可重放 |
| 某一版 Pipe `content` 全文 | 一般不还原旧 blob；装**当时**上游 Pipe，再按 §5 打补丁与 merge valves |

备份口令（运维，不进 git）：升配 / 换镜像 / 大改前复制 `webui.db`。例：`/root/backups/webui-valves-fix-20260821-154729.db`。

---

## 2. 平台钉子（VPS / 容器）

| 项 | 值 / 约束 |
|----|-----------|
| 站点 | `https://micropigeon.com`（`WEBUI_URL` 同此）；Caddy → `127.0.0.1:8080` |
| VPS | Hetzner `78.47.152.85` |
| 容器名 | `open-webui` |
| 镜像 | **钉死 digest** `e97bf9531916`（OWUI 0.11.0）。**不要**漂 `:main`。无 OpenAI/Google Realtime 钥匙时 **不换** Realtime 镜像 |
| Entrypoint | `/custom/entrypoint.sh`（BetterUI patch + 官方 `start.sh`）。新镜像上补丁可能失效，须再验 |
| env 文件 | `/root/open-webui.env` |
| `WEBUI_SECRET_KEY` | **必须 `""`**。禁止写入新的随机非空值（与 `encrypted:` Pipe key 冲突 → catalog 空） |
| 运行时 JWT 文件 | `/app/backend/.webui_secret_key`（容器内，**不在 volume**） |
| `openai.api_configs` | **全部 `enable: false`**。聊天只走 Pipe |
| 登录 | 环境变量 `OPENWEBUI_URL` / `OPENWEBUI_USERNAME`（优先于 email）/ `OPENWEBUI_PASSWORD` |

---

## 3. 现网快照（2026-09-01）

### 3.1 产品主路径（已落地）

| 面 | 现状 |
|----|------|
| 新对话默认 | 单模型 `open_webui_openrouter_integration.x-ai.grok-4.6`（不默认双栏 compare） |
| 置顶四格 | Sonar Pro Search、Sonar Deep Research、Claude Opus 5、GPT-5.6 Sol Pro |
| 作图 | **路线 S**：切图像模型即作图。全局 `ENABLE_IMAGE_GENERATION=false` |
| 搜索 | 只用两档 Sonar。原生 Web Search **关**。OR Web Tools **停用** |
| 语音 / 屏享 | Live **L1**：stock Call overlay + Whisper + MiniMax TTS。**不是** S2S |
| Notebook | **N1**：Knowledge「YouTube Notebook」+ OpenRouter embedding。N2+ Studio **未做** |
| Follow-up 芯片 | **关**（`ENABLE_FOLLOW_UP_GENERATION=false`）。Autocomplete / Title **仍开** |
| 对比 | Pipe 补丁 `COMPARE_CROSS_MODEL_REASONING_V1`；`PERSIST_REASONING_TOKENS` 保持 conversation（Valve 列表未覆盖时即上游默认） |

### 3.2 Admin / PersistentConfig（非密钥）

| 键 | 现网值 |
|----|--------|
| `ui.default_models` | `open_webui_openrouter_integration.x-ai.grok-4.6` |
| `ui.default_pinned_models` | 上述四格 Pipe id（逗号拼接） |
| `direct.enable` / `ENABLE_DIRECT_CONNECTIONS` | `false` |
| `features.enable_web_search` / `retrieval.web.ENABLE_WEB_SEARCH` | `false` |
| `image_generation.enable` / `ENABLE_IMAGE_GENERATION` | `false` |
| `images.edit.enable` | `true`（原生 Edit 开着但主路径不走它） |
| `task.follow_up.enable` | `false` |
| `task.autocomplete.enable` | `true` |
| `task.title.enable` | `true` |
| `task.model.default` / `external` | Grok 4.6 Pipe id |
| `audio.tts` | engine `openai`，model `minimax/speech-2.8-turbo`，voice `alloy`，`split_on=sentence`，`response_format=mp3`，base `https://openrouter.ai/api/v1` |
| `audio.stt` | engine `openai`，model `openai/whisper-large-v3-turbo`，同一 OpenRouter base |
| `rag.embedding_engine` | `openai` |
| `rag.embedding_model` | `openai/text-embedding-3-small` |
| `rag.openai.api_base_url` | `https://openrouter.ai/api/v1` |
| `rag.content_extraction_engine` | **空**（Tika **未开**；`TIKA_SERVER_URL` 占位 `http://tika:9998`） |
| `rag.youtube_loader_language` | `en`, `zh`, `zh-Hans`, `zh-Hant`, `ja`, `ko` |
| `code_interpreter.enable` | `true`（pyodide）。Sonar/纯图像 capability 须 false，**不要**关全局 |
| `ui.enable_signup` | `false` |
| `oauth.enable` | `true`（client 空，未当登录主路径） |
| `automations.enable` / `calendar.enable` / `notes.enable` / memories | 开着，**不推广、不深挖、不随便关** |
| `openai.enable` | `true`（槽位在，但 configs **全 disable**） |
| `openai.api_base_urls` | 5 条，均为 `https://openrouter.ai/api/v1` |
| `openai.api_configs` | 5 条，**全部 `enable: false`**（槽 0–4；已无旧 gptsapi 槽） |
| `webui.url` | `https://micropigeon.com` |
| `auth.jwt_expiry` | `-1` |

`openai.api_configs` 现网槽（全 disable）：0 `gpt-5.5`；1 `x-ai/grok-4.3` + `grok-4.5`；2 Sol / Sol Pro；3 Fable + Opus；4 `google/gemini-3.1-pro-preview`。**不要**复活已删的 gptsapi 槽。

`www.micropigeon.com` **无 DNS**。`http://78.47.152.85` 是另一套中文页（`/api/version` 404），不是本 OWUI。`http://micropigeon.com` Caddy **308** → https。

### 3.3 Banner / 空对话 chips

现网 **一条** Banner：

| id | 内容（HTML） |
|----|----------------|
| `usage-guide-v3` | `<b>Web search only on Perplexity Sonar. Images only on an image model.</b> <b>Reasoning depth</b>: Input box → <b>Valves</b>. <b>Settings → General → System Prompt</b> may also affect image models and Perplexity sonar.` ；`dismissible: false` |

现网 `ui.prompt_suggestions` = **`[]`**。OWUI Suggested 点击即发送，空 chips 不是缺功能。Follow-up 是另一开关（ST-12）。

**指引规则**：英文；一条全局 Banner，型号事实放 Description；不要教用户打开已隐藏的 Integrations；Banner 只吃 HTML（换行会变 `<br>`）；改 Banner `id` 会让已看过的人再看到。历史双条 v2 / 4 chips **不要重放**。

`POST /api/v1/configs/banners` body 是 `{"banners":[...]}`，不是裸数组。`POST /api/v1/configs/suggestions` 同理 `{"suggestions":[...]}`。

仓库 `scripts/apply_ui_guidance_banners.py` **已对齐** v3 + 空 chips。重跑会写回现网这份指引。若用户后来又改了 Banner，先对照本表再决定是否覆盖。

### 3.4 Pipe / Filter

| 项 | 现网 |
|----|------|
| Pipe id | `open_webui_openrouter_integration`，active |
| `content` SHA256 前 12 | 以 `verify_stack` INFO / `VERSIONS.md` 为准（2026-09-01 探针 `7415c2e4347a`；现网若已 ST-13 则为 `f797e92d6d3f`） |
| 补丁探针 | `_is_openrouter_images_api_model`、`seedream-5`、`middle-out`、`apply_chat_context_transforms`、`COMPARE_CROSS_MODEL_REASONING_V1`、`FABLE_UNSIGNED_SUMMARY_V1` **均应在** |
| `API_KEY` | 已配置；API 读出为 `encrypted:`（catalog 正常即可） |
| valves（API 返回的覆盖项） | 下列 **全 false**：`AUTO_ATTACH_WEB_TOOLS_FILTER`、`AUTO_ATTACH_IMAGE_GEN_FILTER`、`AUTO_INSTALL_WEB_TOOLS_FILTER`、`AUTO_INSTALL_IMAGE_GEN_FILTER`、`AUTO_DEFAULT_WEB_TOOLS_FILTER`、`ENABLE_DATETIME`、`ENABLE_WEB_SEARCH`、`UPDATE_MODEL_CAPABILITIES` |

**全局 Guard（is_global + active）**

- `openrouter_image_tool_guard`  
- `openrouter_image_context_guard`  
- `openrouter_search_native_tool_guard`  

**必须停用**：`openrouter_web_tools`、`openrouter_image_gen`。

**可 active 但非 global**：`openrouter_direct_uploads`、各 `openrouter_image_filter_*`、Fusion、**全部 video filter**（模型未 public，Wave 1 未做）。不要一次 public 全部视频模型。

Filter **priority 数字越小越先执行**；剥 tools 的 Guard 要靠后。

### 3.5 21 个 public（契约；id 前缀皆 `open_webui_openrouter_integration.`）

与 `scripts/stack_contract.py` 的 `PUBLIC_MODEL_IDS` 一致。现网这 21 个 **均 public + is_active**。picker = 这 21 个。

聊天 / 推理：`x-ai.grok-4.6`、`openai.gpt-5.6-sol-pro`、`openai.gpt-5.6-sol`、`anthropic.claude-opus-5`、`anthropic.claude-fable-5.1`、`deepseek.deepseek-v4-pro-0813`、`moonshotai.kimi-k3`、`qwen.qwen3.8-max`、`google.gemini-3.1-pro-preview`、`google.gemini-3.8-flash`  
搜索：`perplexity.sonar-pro-search`、`perplexity.sonar-deep-research`  
图像：`google.gemini-3-pro-image`、`google.gemini-3.1-flash-image`、`openai.gpt-image-2`、`openai.gpt-5.4-image-2`、`bytedance-seed.seedream-5-0-pro`、`bytedance-seed.seedream-5-0-lite`、`microsoft.mai-image-2.5-pro`、`qwen.qwen-image-3-pro`、`x-ai.grok-imagine-image-2.0`

Sonar / 纯图像：`code_interpreter=false`、`web_search=false`、`builtin_tools=false`；纯图像另 `terminal=false`。filterIds 含 `openrouter_direct_uploads`，图像另加对应 `openrouter_image_filter_*`。**不要**挂 `openrouter_web_tools` / `openrouter_image_gen`。

### 3.6 Picker（= 21 public；只跟已留家族的最新 id）

`GET /api/models` 应为 **21**：与 `PUBLIC_MODEL_IDS` 相同。两条 Gemini 也是 public（不是管理员专属）。

**去除（is_active=false）**：旧 id `claude-fable-5`、`gemini-3.7-flash`；`ibm-granite.granite-4.2-8b`、`inception.mercury-2.5-preview`；以及新出现的家族（现网曾漂过：`inclusionai.ling-3.0-flash-fin`、`meta.muse-spark-1.3`、`meta.muse-spark-1.3-contributor`、`minimax.hailuo-3-max`、`~z-ai.glm-flash-latest`）。契约外模型若带 `*` read，跑 `restore_public_grants.py` 剥掉。

灾后跑 `apply_model_catalog_visibility.py`（按 `ACTIVE_MODEL_IDS`），再跑 `restore_public_grants.py`（21 public + 剥额外 `*`）。不要把新家族塞进 picker。

### 3.7 Knowledge

| 名 | id（现网） | 说明 |
|----|------------|------|
| YouTube Notebook | `d7cad5ce-893b-4f6b-b45f-325679dfed8b` | N1 集合；描述要求 grounded + timestamp，不是 Sonar。文件数探针为 1。重建后 **id 会变**，按名字认 |

### 3.8 用户侧开关（不入库、重建后用户自设）

- **Valves → Reasoning depth**：Pipe UserValves，持久；本站主深度开关。难题用 high/xhigh。  
- **Settings → General → Reasoning Effort**：OWUI 全局参数。若设成 Custom，会 **盖掉** Valves。建议 Default，只调 Valves。  
- 用户 Settings 不随 git 重建；DB 还原则还在。

---

## 4. 现网 vs 仓库脚本（避免救灾时救错）

| 项 | 仓库 / `verify_stack` | 2026-09-01 现网 | 灾后怎么做 |
|----|----------------------|-----------------|------------|
| Banner | 一条 `usage-guide-v3` | 一条 `usage-guide-v3` | 跑 `apply_ui_guidance_banners.py` 即可 |
| 空对话 chips | 0 | 0 | 保持空 |
| Follow-up | `apply_wave0` merge false | `false` | **必须关** |
| Picker | 21 public（留下家族最新 id） | 按 `ACTIVE_MODEL_IDS` | `apply_model_catalog_visibility.py` + `restore_public_grants.py`（21 public + 剥额外 `*`）；新家族关掉 |
| Pipe sha | VERSIONS 表；以 `verify_stack` INFO 为准 | 可能已是 ST-13 `f797e92d6d3f` | 新装 Pipe 后打补丁并更新 VERSIONS |
| openai 槽 | 5 槽全 disable | **5** 槽全 OpenRouter disable | 保持全 disable；不必复活 gptsapi |
| Fable | marker `FABLE_UNSIGNED_SUMMARY_V1` | 同 sha 的 Pipe 上应有 | `patch_pipe_fable_thinking_replay.py`（已有则 no-op） |

`verify_stack.py` 验 Banner v3、suggestions=0、Follow-up 关、Fable marker、picker=`ACTIVE_MODEL_IDS`（21）。不要为了绿把 Banner 改回 v2。

---

## 5. 从零重建顺序（无 DB）

密钥已注入、`WEBUI_SECRET_KEY=""`、镜像与 entrypoint 已按 §2。

1. 安装 OWUI 0.11.x（应急优先 **同一 digest**）+ 安装 **当前** OpenRouter Pipe（id 必须 `open_webui_openrouter_integration`）。  
2. **Merge** Pipe valves：明文 `API_KEY` + §3.4 那 8 个 false。禁止全量覆盖 valves。  
3. `GET /api/models?refresh=true`。若 catalog 空：env 确认空密钥 → 再 merge 明文 key（`apply_ops_l0.py`）。  
4. 确认 3 个 Guard global active；web_tools / image_gen **inactive**。  
5. `python3 scripts/apply_plan_a_hide_integrations.py`  
6. `python3 scripts/restore_public_grants.py`（**禁止**空 `POST /api/v1/models/sync`）  
7. `python3 scripts/apply_model_catalog_visibility.py`（21 public）  
8. `python3 scripts/apply_wave0.py`（capabilities + Task=Grok 4.6 + **Follow-up 关** + 全局 Image Gen 关）  
9. `python3 scripts/apply_ui_guidance_banners.py`（`usage-guide-v3` + 空 chips）。TTS/STT/RAG 按 §3.2 **merge**，不覆盖 key。  
10. Knowledge：建「YouTube Notebook」；`apply_notebook_n1.py`。历史 YouTube 文件只能从 **DB 备份** 回来。  
11. 若新 Pipe 丢了 Images API / Seedream / 跨模型 reasoning / Fable：按 continuity plan **模式**补，或 `patch_pipe_cross_model_reasoning.py` / `patch_pipe_fable_thinking_replay.py`（已有 marker 则 no-op）。  
12. 验收：`verify_ops_l0.py`、`verify_stack.py`、`verify_live_baseline.py`、`verify_compare_cross_model.py`、`verify_fable_thinking_replay.py`、`verify_notebook_youtube.py`。  
13. 更新 `docs/VERSIONS.md`（日期、Pipe sha、Banner id）。通知用户 **重登**。

**有 DB 备份时**：先还原 `webui.db` + volume，再只跑 L0 / verify；用户重登。不要空 sync，不要重装 Pipe 覆盖 content，除非 catalog 坏了。

---

## 6. 禁止（重建时同样有效）

- 空 `POST /api/v1/models/sync`  
- 全量覆盖 Pipe valves  
- 新的非空 `WEBUI_SECRET_KEY`  
- 把 `openai.api_configs` 改成 enable  
- 给 Sonar / 纯图像灌 tools；开 Sol Pro `image_generation` 当同会话作图主路径  
- 一次 public 全部视频模型  
- 关全局 Code Interpreter  
- 未确认换 OWUI Realtime 镜像、装第二前端、改 Notebook 入口  
- 把 YouTube 字幕当成 NotebookLM 达标；Call overlay 冒充 Audio Overview  

---

## 7. Later / Don't（尚未落地，重建时不要「顺便做」）

**Later（须另确认）**：见 SPEC。重建时不要顺便做。含 Wave 1 视频、Wave 2 slides、对比 S3 真分栏、Notebook N2+、独立画图 Studio（含蒙版）、Tika T0、语音 S2S / 持续屏流。

**Don't**：ComfyUI（除非 Studio 方案选它）、第二套 Pipe、重开 Web Search 三件套、466 全 public。

---

## 8. 错误目录（现象 → 根因模式 → 修复；不要盲贴旧 Pipe `content`）

| 现象 | 根因模式 | 修复 |
|------|----------|------|
| `No endpoints found that support tool use` + `get_current_timestamp` | 向不支持 tools 的模型灌了 builtin / OR tools | 3 Guard 剥 tools；Sonar/图像 `builtin_tools=false`；web_tools / image_gen **停用** |
| `gpt-image-*` / `seedream-5` 端点错或 500 | 走错 chat 而非 Images API | Pipe Images API 路由 + Seedream resolution |
| 多轮图像 131072 | 历史 data URI / 多图整段进上下文 | image context guard；ST-13 落盘（若 Pipe 有 `IMAGE_DATA_URI_PERSIST_V1`） |
| Pipe 更新后 Sonar 又坏 | auto-install 覆盖 Filter | `AUTO_INSTALL_*=false` + 重跑方案 A / Guard |
| `model/update` 500 | 缺 `access_grants` | 更新必须带 grants |
| valves 更新后全站断 | 全量覆盖 valves | **只 merge** |
| picker 空 / `Model not found` | env 非空 `WEBUI_SECRET_KEY` 与 `encrypted:` Pipe key 冲突，或空 `models/sync` | env 改回 `""`；merge 明文 key；**禁止空 sync** |
| 容器重建后全员掉线 | JWT 不持久化（L0） | **可接受** — 用户重登；agent 跑 verify |

Filter **priority 数字越小越先执行**；剥 tools 的 Guard 要靠后（per-model Filter 会在 Guard 之后再注入）。

**决策（勿擅自改回）**：方案 A 藏 Web Tools 三件套；搜索只走两档 Sonar；不装第二套 Pipe；界面英文；Banner 不可 dismiss；`openai.api_configs` 全 disable；L0 不持久化 JWT。

## 9. 文档地图

| 文件 | 角色 |
|------|------|
| **本文件** | 灾后入口 + 现网钉子 + 错误目录 |
| `AGENTS.md` | 禁令、Pipe merge、脚本表 |
| `docs/SPEC.md` | 产品契约 |
| `docs/VERSIONS.md` | 上次验收指纹 |
| `scripts/stack_contract.py` | 21 public = picker |
| `docs/open-webui-secret-key-persist-plan.md` | L0 SOP |
| `docs/open-webui-live-voice-screen-plan.md` | P0-B / P0-C |
| `docs/open-webui-notebook-youtube-plan.md` | P0-D |
| `docs/open-webui-file-ingest-plan.md` | 文件录入（T0 未确认） |
| `docs/open-webui-openrouter-image-continuity-plan.md` | 图像错误模式 |
