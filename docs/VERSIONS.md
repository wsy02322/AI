# 版本与上次验收

> **不锁死** OWUI / Pipe 版本。本页只记录「哪次 verify 全绿」，便于 Pipe 更新后对比。  
> 现网钉子（Banner / Follow-up / picker 漂移）见 `docs/open-webui-rebuild-archive.md`。

| 项 | 值 |
|----|-----|
| 记录日期 | **2026-09-07**（C2：public 文本 12 个默认搜，含中国三只） |
| OWUI | **0.11.3**（`GET /api/version`）。image id `129f4038ec70`；RepoDigest `ghcr.io/open-webui/open-webui@sha256:751b617714b91e4cfd0186a509c72480c858e012976103b09a30dad053c36175`（旧钉 `e97bf9531916` / 0.11.0） |
| Pipe id | `open_webui_openrouter_integration` |
| Pipe 名称 | Open WebUI OpenRouter Integration |
| Pipe content SHA256（前 12） | `9c4836ace251`（更早：`f797e92d6d3f` → `7415c2e4347a` → `a0b95c2cf90d` → S2′ 前 `081c3773444c`） |
| Pipe 补丁探针 | `_is_openrouter_images_api_model`、`seedream-5`、`middle-out`、`apply_chat_context_transforms`、`COMPARE_CROSS_MODEL_REASONING_V1`、`FABLE_UNSIGNED_SUMMARY_V1`、`IMAGE_DATA_URI_PERSIST_V1`、`SEARCH_PAGE_COMPACT_V1` **均应存在** |
| Banner | **一条** `usage-guide-v7`（不可 dismiss；🌐 Text chat models can search；同一段、无粗体） |
| 空对话 chips | **0**（`ui.prompt_suggestions=[]`） |
| Follow-up | **关**（`ENABLE_FOLLOW_UP_GENERATION=false`）；Autocomplete / Title 仍开 |
| 上次 `verify_stack.py` | **2026-09-07 C2 后全绿**（24 ok / 0 err，`VERIFY_SMOKE=0`）：Pipe `9c4836ace251`；薄 Filter deny 类 + 12 文本 default-on（含 DeepSeek / Kimi / Qwen）；Banner v7。中国三只 Search+Fetch 6/6；Kimi「你继续」0 次新搜 / `$0.008` |
| 即时搜 W0 | **2026-09-07**：`max_tool_calls=3` 转发成功；Flash/Sol 两轮 4 次搜；Grok「继续」11 次。合计 `$0.336`。生产 Filter/Pipe **已还原**（`f2fe14388726` / `9c4836ace251`）。`verify_text_web_search.py --mode final` 14 ok。W6 仍关 |
| 即时搜 W1 | **已过门**（2026-09-07）：Key 在 Tool Valves；Flash 北京南站→首都机场 **36.7km / ~44 分钟 / 畅通为主**；`function_call_count=1`；无电话/评分。`verify_amap --require-key` 16 ok；`verify_stack` 24 ok |
| 即时搜 W3 | **已过门**（2026-09-07）：xAI Search+Fetch **native**。Grok 引 `x.com/elonmusk/status/…`（4 次搜 / `$0.23`）；网页题 1 次搜；Flash Exa 回归仍搜。`verify_text_web_search --mode final` 15 ok；Pipe 仍 `9c4836ace251` |
| 上次 `verify_live_baseline.py` | **2026-09-04（0.11.3）**：TTS/STT/Call 仍绿；Banner v3 **不写** screen share（脚本 needle 过期，1 err，不改 Banner） |
| 上次 GA-A | **2026-08-21**：MiniMax TTS 可用；gpt-audio-mini & gpt-audio **无**可播音频（Pipe `/responses` 拒 `modalities.audio`）。脚本已出树，结论见 SPEC Don't |
| 上次 `verify_notebook_youtube.py` | **2026-08-21 全绿**（12 ok / 0 err）：RAG OpenRouter；YouTube Notebook 有 shown 时间线；口播被 YouTube 数据中心风控拦住 |
| 上次 `verify_compare_cross_model.py` | **2026-09-04 全绿**（5 ok / 0 err，0.11.3）：Opus 跟在 Grok persist marker 后 200；`usage.input_tokens` = 2× 状态栏 Input；同模型 Grok 续聊 200 |
| Wave 0 已应用到实例 | capabilities；默认聊天 + Task = **Grok 4.6**；全局 Image Gen **关**；Follow-up **关** |
| S2′ | Pipe content-only；**未**关全局 persist |
| ST-11 Fable | Pipe marker `FABLE_UNSIGNED_SUMMARY_V1`（sha `f797e92d6d3f`；0.11.3 上 `verify_fable_thinking_replay.py` 7 ok，2026-09-05 复验） |
| ST-14 文本联网 | 薄 Filter `openrouter_text_web_search`；**public 文本 12** attached + default-on（含中国三只）；`TEXT_WEB_SEARCH_DENY_CLASS_V1`。OpenAI / Google → Exa；**xAI native**；Anthropic / 中国三只 `auto`。`verify_text_web_search.py --mode final` 15 ok |
| ST-14 质量基线 | **2026-09-05 已收口**。EVAL-B v2：隐含 42/42；误搜 0/21；精确 Fetch 10/14。Anthropic：HTML 能读，`api.github.com` 不能；指引无效。不上 Controller / 指引。见 `docs/open-webui-text-web-search-eval-b-results.md` |
| HTTPS / catalog | `WEBUI_URL=https://micropigeon.com`；5× OpenRouter slot **全 `enable=false`** |
| ST-1 Sonar | **2026-08-21**：两档 Sonar `builtin_tools=false`（堵住 UI native FC 注入 `get_current_timestamp`） |
| VPS 维护 / L0 | 0.11.3 recreate 后再跑 `apply_ops_l0`（merge 明文；脚本因列表=21 报 catalog low，picker 已恢复）。K1/K2 冻结 |
| Pipe `API_KEY` 形态 | `encrypted:`（API 保存）；decrypt 失败时 merge 明文 |
| 上次 `verify_ops_l0.py` | **2026-09-04（0.11.3）**：5 ok / 1 err。`/api/v1/models` 列表 = 21（JWT 轮换后 merge 恢复的就是这 21）。不要为「>400」去 refresh |

## Pipe 更新后

见 `AGENTS.md` → **Pipe 更新 Runbook**。更新后重填本表。重放 S2′：`python3 scripts/patch_pipe_cross_model_reasoning.py`。重放 ST-11：`python3 scripts/patch_pipe_fable_thinking_replay.py`（marker 已在则 no-op）。重放 T1 压页：`python3 scripts/patch_pipe_search_page_compact.py`（已有 `SEARCH_PAGE_COMPACT_V1` 则 no-op）。
