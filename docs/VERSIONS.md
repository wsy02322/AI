# 版本与上次验收

> **不锁死** OWUI / Pipe 版本。本页只记录「哪次 verify 全绿」，便于 Pipe 更新后对比。

| 项 | 值 |
|----|----|
| 记录日期 | 2026-08-20 |
| OWUI | **0.11.0**（`GET /api/version`） |
| Pipe id | `open_webui_openrouter_integration` |
| Pipe 名称 | Open WebUI OpenRouter Integration |
| Pipe content SHA256（前 12） | `081c3773444c` |
| Pipe 补丁探针 | `_is_openrouter_images_api_model`、`seedream-5`、`middle-out`、`apply_chat_context_transforms` **均存在** |
| 上次 `verify_stack.py` | **2026-08-20 全绿**（20 ok / 0 err）；Task 模型后改为 **Grok 4.6** |
| Wave 0 已应用到实例 | capabilities；Task = **Grok 4.6**；默认聊天 = Sol Pro |

## Pipe 更新后

见 `AGENTS.md` → **Pipe 更新 Runbook**。更新后重填本表。
