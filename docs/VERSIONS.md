# 版本与上次验收

> **不锁死** OWUI / Pipe 版本。本页只记录「哪次 verify 全绿」，便于 Pipe 更新后对比。  
> 现网钉子（Banner / Follow-up / picker 漂移）见 `docs/open-webui-rebuild-archive.md`。

| 项 | 值 |
|----|-----|
| 记录日期 | **2026-09-03**（ST-13 落地） |
| OWUI | **0.11.0**（`GET /api/version`）；镜像钉死 `e97bf9531916` |
| Pipe id | `open_webui_openrouter_integration` |
| Pipe 名称 | Open WebUI OpenRouter Integration |
| Pipe content SHA256（前 12） | **`f797e92d6d3f`**（ST-13 前 `7415c2e4347a`；更早 `a0b95c2cf90d` → S2′ 前 `081c3773444c`） |
| Pipe 补丁探针 | `_is_openrouter_images_api_model`、`seedream-5`、`middle-out`、`apply_chat_context_transforms`、`COMPARE_CROSS_MODEL_REASONING_V1`、`FABLE_UNSIGNED_SUMMARY_V1`、**`IMAGE_DATA_URI_PERSIST_V1`** **均应存在** |
| Guard 补丁探针 | `openrouter_image_context_guard` 含 **`IMAGE_CONTEXT_DATA_URI_CAP_V1`**（sha `1cef7c0da5ac`，ST-13 前 `2201a71cb229`） |
| Banner | **一条** `usage-guide-v3`（不可 dismiss） |
| 空对话 chips | **0**（`ui.prompt_suggestions=[]`） |
| Follow-up | **关**（`ENABLE_FOLLOW_UP_GENERATION=false`）；Autocomplete / Title 仍开 |
| 上次 `verify_stack.py` | **2026-09-03**：**26 ok / 1 err**。唯一 err = picker **27 ≠ 21**（见下「未决漂移」）。Banner v3、chips=0、Follow-up 关、7 个 Pipe marker、Guard marker、19 public、4 条 smoke 全 200 |
| 上次 `verify_image_data_uri_persist.py` | **2026-09-03 全绿**（16 ok / 0 err）：Qwen 出图回复 81 字符含 `/api/v1/files/`；Nano Banana 2 续聊 200；2MB 内联 data URI 200 |
| 上次 `verify_live_baseline.py` | **2026-08-21**：TTS = `minimax/speech-2.8-turbo`；OWUI `/audio/speech` **200**；STT whisper-large-v3-turbo 可用 |
| 上次 GA-A `run_ga_a_trial.py` | **2026-08-21**：MiniMax MP3 31149 B / 1.62s 整段；gpt-audio-mini & gpt-audio **无**可播音频（Pipe `/responses` 拒 `modalities.audio`）；§1 仅关闭问题 3 |
| 上次 `verify_notebook_youtube.py` | **2026-08-21 全绿**（12 ok / 0 err）：RAG OpenRouter；YouTube Notebook 有 shown 时间线；口播被 YouTube 数据中心风控拦住 |
| 上次 `verify_compare_cross_model.py` | **2026-08-26 全绿**（5 ok / 0 err）：Opus 跟在 Grok persist marker 后 200；`usage.input_tokens` = 2× 状态栏 Input（内部重试一次）；同模型 Grok 续聊 200；`PERSIST_REASONING_TOKENS` 仍为默认 conversation |
| 上次 `verify_fable_thinking_replay.py` | **2026-08-26 全绿**（7 ok / 0 err）：Fable 第 1 轮 thinking `output` 带 `signature` + `format=anthropic-claude-v1`；续聊 200，无 `cannot be modified` |
| Wave 0 已应用到实例 | capabilities；默认聊天 + Task = **Grok 4.6**；全局 Image Gen **关**；Follow-up **关** |
| S2′ | Pipe content-only；**未**关全局 persist |
| ST-11 Fable | Pipe marker `FABLE_UNSIGNED_SUMMARY_V1`（sha `7415c2e4347a`） |
| HTTPS / catalog | `WEBUI_URL=https://micropigeon.com`；5× OpenRouter slot **全 `enable=false`** |
| ST-1 Sonar | **2026-08-21**：两档 Sonar `builtin_tools=false`（堵住 UI native FC 注入 `get_current_timestamp`） |
| VPS 维护 / L0 | **已执行** `apply_ops_l0` + `verify_ops_l0`（2026-08-21，5 ok）；K1/K2 冻结 |
| Pipe `API_KEY` 形态 | `encrypted:`（API 保存）；decrypt 失败时 merge 明文 |
| 上次 `verify_ops_l0.py` | **2026-08-21 全绿**（5 ok / 0 err） |

## 未决漂移（2026-09-03，**未处理，待确认**）

`GET /api/models` = **27**，契约 `ACTIVE_MODEL_IDS` = 21。ST-13 之前的 baseline 就是 27，**与 ST-13 无关**。

| 多出来的 | grants |
|----------|--------|
| `anthropic.claude-fable-5.1` | **`*` read**（等于对全体可见） |
| `google.gemini-3.8-flash` | **`*` read** |
| `inclusionai.ling-3.0-flash-fin` | 空（仅管理员） |
| `meta.muse-spark-1.3` | 空 |
| `meta.muse-spark-1.3-contributor` | 空 |
| `minimax.hailuo-3-max` | 空 |
| `~z-ai.glm-flash-latest` | 空 |

少了一个：`google.gemini-3.7-flash`（OpenRouter 侧疑似下线/改名，`gemini-3.8-flash` 像是替代）。

**注意**：前两个带 `*` read，所以**现网实际公开 = 21，不是 19**，与「维持 19 个 public」不符。`verify_stack` 的 `public 19` 只验「那 19 个是 public」，不验「没有别的也 public」。

处理需要用户先决定留哪些（`gemini-3.8-flash` 是否接替 3.7、`fable-5.1` 是否要），再跑 `apply_model_catalog_visibility.py` 并更新 `ACTIVE_MODEL_IDS`。**不要**在未确认时直接关。

## Pipe 更新后

见 `AGENTS.md` → **Pipe 更新 Runbook**。更新后重填本表。重放 S2′：`python3 scripts/patch_pipe_cross_model_reasoning.py`（若 marker 已在则 no-op）。重放 ST-11：`python3 scripts/patch_pipe_fable_thinking_replay.py`（若 marker 已在则 no-op）。重放 **ST-13**：`python3 scripts/patch_pipe_image_data_uri_persist.py`；Guard 侧 `python3 scripts/patch_guard_image_context_data_uri.py`。
