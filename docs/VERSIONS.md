# 版本与上次验收

> **不锁死** OWUI / Pipe 版本。本页只记录「哪次 verify 全绿」，便于 Pipe 更新后对比。  
> 现网钉子（Banner / Follow-up / picker 漂移）见 `docs/open-webui-rebuild-archive.md`。

| 项 | 值 |
|----|-----|
| 记录日期 | **2026-09-05**（ST-14 薄 Web Search 落地） |
| OWUI | **0.11.3**（`GET /api/version`）。image id `129f4038ec70`；RepoDigest `ghcr.io/open-webui/open-webui@sha256:751b617714b91e4cfd0186a509c72480c858e012976103b09a30dad053c36175`（旧钉 `e97bf9531916` / 0.11.0） |
| Pipe id | `open_webui_openrouter_integration` |
| Pipe 名称 | Open WebUI OpenRouter Integration |
| Pipe content SHA256（前 12） | `f797e92d6d3f`（更早：`7415c2e4347a` → `a0b95c2cf90d` → S2′ 前 `081c3773444c`） |
| Pipe 补丁探针 | `_is_openrouter_images_api_model`、`seedream-5`、`middle-out`、`apply_chat_context_transforms`、`COMPARE_CROSS_MODEL_REASONING_V1`、`FABLE_UNSIGNED_SUMMARY_V1`、`IMAGE_DATA_URI_PERSIST_V1` **均应存在** |
| Banner | **一条** `usage-guide-v4`（不可 dismiss） |
| 空对话 chips | **0**（`ui.prompt_suggestions=[]`） |
| Follow-up | **关**（`ENABLE_FOLLOW_UP_GENERATION=false`）；Autocomplete / Title 仍开 |
| 上次 `verify_stack.py` | **2026-09-05 全绿**（28 ok / 0 err）：Banner v4、ST-14 薄 Web Search active/non-global、7 文本 default-on、Sonar/图像未挂、chips=0、Follow-up 关、**21 public** = picker。烟雾 Grok/Opus/Sol/Sonar 200 |
| 上次 `verify_live_baseline.py` | **2026-09-04（0.11.3）**：TTS/STT/Call 仍绿；Banner v3 **不写** screen share（脚本 needle 过期，1 err，不改 Banner） |
| 上次 GA-A | **2026-08-21**：MiniMax TTS 可用；gpt-audio-mini & gpt-audio **无**可播音频（Pipe `/responses` 拒 `modalities.audio`）。脚本已出树，结论见 SPEC Don't |
| 上次 `verify_notebook_youtube.py` | **2026-08-21 全绿**（12 ok / 0 err）：RAG OpenRouter；YouTube Notebook 有 shown 时间线；口播被 YouTube 数据中心风控拦住 |
| 上次 `verify_compare_cross_model.py` | **2026-09-04 全绿**（5 ok / 0 err，0.11.3）：Opus 跟在 Grok persist marker 后 200；`usage.input_tokens` = 2× 状态栏 Input；同模型 Grok 续聊 200 |
| Wave 0 已应用到实例 | capabilities；默认聊天 + Task = **Grok 4.6**；全局 Image Gen **关**；Follow-up **关** |
| S2′ | Pipe content-only；**未**关全局 persist |
| ST-11 Fable | Pipe marker `FABLE_UNSIGNED_SUMMARY_V1`（sha `f797e92d6d3f`；0.11.3 上 `verify_fable_thinking_replay.py` 7 ok，2026-09-05 复验） |
| ST-14 文本联网 | 薄 Filter `openrouter_text_web_search`；7 模型 attached + default-on；Flash canary 有 `web_search`/`web_fetch` 事件；allowlist smoke 7/7 search；图像三条路由无 tool-use 404。`verify_text_web_search.py --mode final` 11 ok |
| ST-14 质量基线 | **2026-09-05 EVAL-B v2**：隐含时效 42/42；误搜 0/21；精确 Fetch **10/14 红**。Anthropic A/B：HTML 8/8、GitHub API 0/4，指引无效。Filter/Pipe/Banner 未改。见 `docs/open-webui-text-web-search-eval-b-results.md` |
| HTTPS / catalog | `WEBUI_URL=https://micropigeon.com`；5× OpenRouter slot **全 `enable=false`** |
| ST-1 Sonar | **2026-08-21**：两档 Sonar `builtin_tools=false`（堵住 UI native FC 注入 `get_current_timestamp`） |
| VPS 维护 / L0 | 0.11.3 recreate 后再跑 `apply_ops_l0`（merge 明文；脚本因列表=21 报 catalog low，picker 已恢复）。K1/K2 冻结 |
| Pipe `API_KEY` 形态 | `encrypted:`（API 保存）；decrypt 失败时 merge 明文 |
| 上次 `verify_ops_l0.py` | **2026-09-04（0.11.3）**：5 ok / 1 err。`/api/v1/models` 列表 = 21（JWT 轮换后 merge 恢复的就是这 21）。不要为「>400」去 refresh |

## Pipe 更新后

见 `AGENTS.md` → **Pipe 更新 Runbook**。更新后重填本表。重放 S2′：`python3 scripts/patch_pipe_cross_model_reasoning.py`。重放 ST-11：`python3 scripts/patch_pipe_fable_thinking_replay.py`（marker 已在则 no-op）。
