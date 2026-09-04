# 版本与上次验收

> **不锁死** OWUI / Pipe 版本。本页只记录「哪次 verify 全绿」，便于 Pipe 更新后对比。  
> 现网钉子（Banner / Follow-up / picker 漂移）见 `docs/open-webui-rebuild-archive.md`。

| 项 | 值 |
|----|-----|
| 记录日期 | **2026-09-04**（升级 0.11.3 **之前**的绿基线） |
| OWUI | **仍 0.11.0**（`GET /api/version`）；镜像仍钉 `e97bf9531916`。**已确认**换官方 `v0.11.3` 钉 digest，见 `docs/open-webui-upgrade-0113-plan.md`；digest 换完改本行 |
| Pipe id | `open_webui_openrouter_integration` |
| Pipe 名称 | Open WebUI OpenRouter Integration |
| Pipe content SHA256（前 12） | `f797e92d6d3f`（更早：`7415c2e4347a` → `a0b95c2cf90d` → S2′ 前 `081c3773444c`） |
| Pipe 补丁探针 | `_is_openrouter_images_api_model`、`seedream-5`、`middle-out`、`apply_chat_context_transforms`、`COMPARE_CROSS_MODEL_REASONING_V1`、`FABLE_UNSIGNED_SUMMARY_V1` **均应存在** |
| Banner | **一条** `usage-guide-v3`（不可 dismiss） |
| 空对话 chips | **0**（`ui.prompt_suggestions=[]`） |
| Follow-up | **关**（`ENABLE_FOLLOW_UP_GENERATION=false`）；Autocomplete / Title 仍开 |
| 上次 `verify_stack.py` | **2026-09-04 全绿**（27 ok / 0 err）：Banner v3、chips=0、Follow-up 关、Fable marker、**21 public**。升级前曾漂到 picker 23（`nemotron-3.5-content-safety`、`grok-4.3:batch`），已关掉。旧 `claude-fable-5` / `gemini-3.7-flash` 及新家族不在 picker |
| 上次 `verify_live_baseline.py` | **2026-09-04**：TTS/STT/Call 仍绿；Banner v3 **不写** screen share（脚本 needle 过期，1 err，不改 Banner） |
| 上次 GA-A | **2026-08-21**：MiniMax TTS 可用；gpt-audio-mini & gpt-audio **无**可播音频（Pipe `/responses` 拒 `modalities.audio`）。脚本已出树，结论见 SPEC Don't |
| 上次 `verify_notebook_youtube.py` | **2026-08-21 全绿**（12 ok / 0 err）：RAG OpenRouter；YouTube Notebook 有 shown 时间线；口播被 YouTube 数据中心风控拦住 |
| 上次 `verify_compare_cross_model.py` | **2026-09-04 全绿**（5 ok / 0 err）：Opus 跟在 Grok persist marker 后 200；`usage.input_tokens` = 2× 状态栏 Input；同模型 Grok 续聊 200；`PERSIST_REASONING_TOKENS` 仍为默认 conversation |
| Wave 0 已应用到实例 | capabilities；默认聊天 + Task = **Grok 4.6**；全局 Image Gen **关**；Follow-up **关** |
| S2′ | Pipe content-only；**未**关全局 persist |
| ST-11 Fable | Pipe marker `FABLE_UNSIGNED_SUMMARY_V1`（sha `f797e92d6d3f`；2026-09-04 `verify_fable_thinking_replay.py` 7 ok） |
| HTTPS / catalog | `WEBUI_URL=https://micropigeon.com`；5× OpenRouter slot **全 `enable=false`** |
| ST-1 Sonar | **2026-08-21**：两档 Sonar `builtin_tools=false`（堵住 UI native FC 注入 `get_current_timestamp`） |
| VPS 维护 / L0 | **已执行** `apply_ops_l0` + `verify_ops_l0`（2026-08-21，5 ok）；K1/K2 冻结 |
| Pipe `API_KEY` 形态 | `encrypted:`（API 保存）；decrypt 失败时 merge 明文 |
| 上次 `verify_ops_l0.py` | **2026-09-04**：5 ok / 1 err。`/api/v1/models` 列表 = 21（inactive 仍可按 id GET）；不要为「>400」去 refresh |

## Pipe 更新后

见 `AGENTS.md` → **Pipe 更新 Runbook**。更新后重填本表。重放 S2′：`python3 scripts/patch_pipe_cross_model_reasoning.py`。重放 ST-11：`python3 scripts/patch_pipe_fable_thinking_replay.py`（marker 已在则 no-op）。
