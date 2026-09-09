# 版本与上次验收

> **不锁死** OWUI / Pipe 版本。只记当前指纹，便于 Pipe 更新后对照。过门日记不写在这里。  
> 现网钉子见 `docs/open-webui-rebuild-archive.md`。契约见 `docs/SPEC.md`。

| 项 | 值 |
|----|-----|
| 记录日期 | **2026-09-09** |
| OWUI | **0.11.3**（`GET /api/version`）。image id `129f4038ec70`；RepoDigest `ghcr.io/open-webui/open-webui@sha256:751b617714b91e4cfd0186a509c72480c858e012976103b09a30dad053c36175` |
| Pipe id | `open_webui_openrouter_integration` |
| Pipe content SHA256（前 12） | `45844d32b3d9`（`SERVER_TOOL_FAIL_RETRY_V1`） |
| Pipe 补丁探针 | `_is_openrouter_images_api_model`、`seedream-5`、`middle-out`、`apply_chat_context_transforms`、`COMPARE_CROSS_MODEL_REASONING_V1`、`FABLE_UNSIGNED_SUMMARY_V1`、`IMAGE_DATA_URI_PERSIST_V1`、`SEARCH_PAGE_COMPACT_V1`、`MAX_TOOL_CALLS_FORWARD_V1`、`SERVER_TOOL_FAIL_RETRY_V1` **均应存在** |
| Banner | **一条** `usage-guide-v7` |
| 空对话 chips | **0** |
| Follow-up | **关**；Autocomplete / Title 仍开 |
| 上次 `verify_stack.py` | **2026-09-07** `VERIFY_SMOKE=0` 24 ok（C2 后）。之后只改过 Tool / Pipe 补丁，picker 若漂移见 archive 错误目录 |
| 默认聊天 + Task | **Grok 4.6**；全局 Image Gen **关** |
| ST-14 | 薄 Filter deny 类；public 文本 12 default-on。OpenAI native + `max_tool_calls=3`；Google / xAI native；Anthropic / 中国三只 `auto`。质量收口见 `docs/open-webui-text-web-search-eval-b-results.md` |
| ST-11 / S2′ | `FABLE_UNSIGNED_SUMMARY_V1`；`PERSIST_REASONING_TOKENS` 仍 conversation |
| ST-16 高德 | `AMAP_DRIVE_ROUTE_NAV_WEB_ONLY_V1`（多站只出分段网页导航，无 App 深链） |
| HTTPS / catalog | `WEBUI_URL=https://micropigeon.com`；5× OpenRouter slot **全 `enable=false`** |
| Pipe `API_KEY` | `encrypted:`（API 保存）；decrypt 失败时 merge 明文 |
| L0 | `WEBUI_SECRET_KEY=""`；重建后用户重登。K1/K2 冻结 |

## Pipe 更新后

见 `AGENTS.md` → **Pipe 更新 Runbook**。更新后重填 **Pipe sha / 探针 / verify_stack**。重放：`patch_pipe_cross_model_reasoning.py`、`patch_pipe_fable_thinking_replay.py`、`patch_pipe_search_page_compact.py`、`patch_pipe_max_tool_calls.py`、`patch_pipe_server_tool_fail.py`（已有 marker 则 no-op）。
