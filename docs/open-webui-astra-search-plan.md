# Astra 进 ST-14 薄 Web Search

> **状态**：**A3 未过门，已回滚挂载**（2026-09-06）。public 仍 23；Banner 仍 `usage-guide-v5`；ST-14 仍原 7 个。  
> **现网**：OWUI 0.11.3；Pipe `f797e92d6d3f`。  
> **确认过的目标**：挂薄 Web Search。未过烟雾，**没有**改 Banner、没有留 Astra 附件。

关联：`docs/open-webui-text-web-search-plan.md`（ST-14 机制）、`docs/SPEC.md` UX-3 / ST-14。

---

## 0. 目标（未达成）

Astra / Astra Pro 与现有 7 个文本同一套 Web Search。Banner 第一句带 Astra。

## 1. 已做与回滚

| 步 | 结果 |
|----|------|
| **A1** | 仓库 allowlist 曾扩到 9；单测绿 |
| **A2** | `apply --mode final` 曾挂上两个 Astra（default-on）；`verify_text_web_search --mode final` 11 ok |
| **A3** | **红**。两模型 Search+Fetch 各 200，但 `web_search_requests=0`、无 hosted 事件、`input_tokens=27`（工具定义没出门） |
| **回滚** | 剥回 Astra 的 `openrouter_text_web_search`；仓库契约改回 7 + Banner v5 |

模型原话是「这个聊天没有 web_search」，不是 `No endpoints found that support tool use`。

## 2. 已排除

- OpenRouter 目录：Astra **支持 `tools` / `tool_choice`**，`output_modalities=["text"]`，不是出图模型。
- 薄 Filter **本地 inlet** 对 Astra 会写入 `server_tools`（allowlist 命中、未 deny）。
- 同一助手、同一 `chat_with_optional_search`：Grok 有 `web_search_requests=1`。
- 现网 Filter content 已含 Astra suffix；toggle 重载无效。
- 把 Astra `image_generation` 改成 false **无效**（token 仍 27）。挂载已回滚；该 capability 实验后已恢复。

结论：卡在 **OWUI/Pipe 运行时没把 `server_tools` 发给 OpenRouter**，不是 allowlist 写错。候选：Pipe `_apply_server_tools_metadata` / `build_tools` 对 Astra 的 `ModelFamily` 缓存、或 Filter 在该模型请求上没真正执行。未再改 Pipe content。

## 3. 下一步（另确认）

| 档 | 做什么 |
|----|--------|
| **简单** | 维持现状：Astra 能选能聊，不挂搜索；Banner 不写 Astra。代价：旗舰看起来像能搜。 |
| **顶级** | Pipe content-only 加日志/例外，确认 `server_tools` 是否被 `image_output` 门或 metadata key 丢掉；修好后再挂、再改 Banner。动 Pipe，须另点头。 |
| **Later** | EVAL-B 子集。工具都没出门，现在跑评测无意义。 |

不上 Controller、不加 Filter 指引、不抬 `$0.05`。
