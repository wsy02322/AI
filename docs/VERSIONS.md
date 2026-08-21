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
| 上次 `verify_stack.py` | **2026-08-21 全绿**（24 ok / 0 err）：catalog **473**、19 public、Grok/Opus/Sol Pro/Sonar smoke 200 |
| 上次 `verify_live_baseline.py` | **2026-08-21**：TTS = `minimax/speech-2.8-turbo`；OWUI `/audio/speech` **200**；STT whisper-large-v3-turbo 可用 |
| 上次 `verify_notebook_youtube.py` | **2026-08-21 全绿**（12 ok / 0 err）：RAG OpenRouter；YouTube Notebook 有 shown 时间线；口播被 YouTube 数据中心风控拦住 |
| 上次 `verify_compare_cross_model.py` | **2026-08-20 全绿**（5 ok / 0 err）：Opus 跟在 Grok persist marker 后 200；`usage.input_tokens` = 2× 状态栏 Input（内部重试一次）；同模型 Grok 续聊 200；`PERSIST_REASONING_TOKENS` 仍为默认 conversation |
| Wave 0 已应用到实例 | capabilities；默认聊天 + Task = **Grok 4.6**；全局 Image Gen **关** |
| S2′ | Pipe content-only；**未**关全局 persist |
| HTTPS / catalog | `WEBUI_URL=https://micropigeon.com`；gptsapi slot0 **禁用**；5× OpenRouter slot **全 `enable=false`** |
| VPS 维护（2026-08-21） | Hetzner cx23→cx33；曾误设 env `WEBUI_SECRET_KEY` → decrypt 失败 → catalog 空；已回滚；**运维 L0 已确认**（接受重登、Pipe 明文、不执行 K1/K2） |
| Pipe `API_KEY` 形态 | **明文**（L0 默认）；merge 恢复；**不**主动 Fernet 加密 |

## Pipe 更新后

见 `AGENTS.md` → **Pipe 更新 Runbook**。更新后重填本表。重放 S2′：`python3 scripts/patch_pipe_cross_model_reasoning.py`（若 marker 已在则 no-op）。
