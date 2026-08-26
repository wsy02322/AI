# 版本与上次验收

> **不锁死** OWUI / Pipe 版本。本页只记录「哪次 verify 全绿」，便于 Pipe 更新后对比。

| 项 | 值 |
|----|-----|
| 记录日期 | 2026-08-21 |
| OWUI | **0.11.0**（`GET /api/version`） |
| Pipe id | `open_webui_openrouter_integration` |
| Pipe 名称 | Open WebUI OpenRouter Integration |
| Pipe content SHA256（前 12） | `a0b95c2cf90d`（S2′ 前为 `081c3773444c`） |
| Pipe 补丁探针 | `_is_openrouter_images_api_model`、`seedream-5`、`middle-out`、`apply_chat_context_transforms`、`COMPARE_CROSS_MODEL_REASONING_V1` **均存在** |
| 上次 `verify_stack.py` | **2026-08-26 全绿**（25 ok / 0 err）：**单默认 Grok 4.6**；active picker **19**；19 public；smoke 200；**Suggested 空**；蓝条只强调 Sonar=联网 / 图像模型=作图 |
| 上次 `verify_live_baseline.py` | **2026-08-21**：TTS = `minimax/speech-2.8-turbo`；OWUI `/audio/speech` **200**；STT whisper-large-v3-turbo 可用 |
| 上次 GA-A `run_ga_a_trial.py` | **2026-08-21**：MiniMax MP3 31149 B / 1.62s 整段；gpt-audio-mini & gpt-audio **无**可播音频（Pipe `/responses` 拒 `modalities.audio`）；§1 仅关闭问题 3 |
| 上次 `verify_notebook_youtube.py` | **2026-08-21 全绿**（12 ok / 0 err）：RAG OpenRouter；YouTube Notebook 有 shown 时间线；口播被 YouTube 数据中心风控拦住 |
| 上次 `verify_compare_cross_model.py` | **2026-08-20 全绿**（5 ok / 0 err）：Opus 跟在 Grok persist marker 后 200；`usage.input_tokens` = 2× 状态栏 Input（内部重试一次）；同模型 Grok 续聊 200；`PERSIST_REASONING_TOKENS` 仍为默认 conversation |
| Wave 0 已应用到实例 | capabilities；默认聊天 + Task = **Grok 4.6**；全局 Image Gen **关** |
| S2′ | Pipe content-only；**未**关全局 persist |
| HTTPS / catalog | `WEBUI_URL=https://micropigeon.com`；gptsapi slot0 **禁用**；5× OpenRouter slot **全 `enable=false`** |
| ST-1 Sonar | **2026-08-21**：两档 Sonar `builtin_tools=false`（堵住 UI native FC 注入 `get_current_timestamp`） |
| VPS 维护 / L0 | **已执行** `apply_ops_l0` + `verify_ops_l0`（2026-08-21，5 ok）；K1/K2 冻结 |
| Pipe `API_KEY` 形态 | `encrypted:`（API 保存）；decrypt 失败时 merge 明文 |
| 上次 `verify_ops_l0.py` | **2026-08-21 全绿**（5 ok / 0 err） |

## Pipe 更新后

见 `docs/AGENT-ONBOARDING.md` → **Pipe 更新 Runbook**。更新后重填本表。重放 S2′：`python3 scripts/patch_pipe_cross_model_reasoning.py`（若 marker 已在则 no-op）。
