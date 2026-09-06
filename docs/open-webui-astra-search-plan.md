# Astra 进 ST-14 薄 Web Search

> **状态**：**C 波已确认执行**（2026-09-06）。先把 Astra 档案改成和 Sol 一样再挂；一轮烟雾决定是否改 Banner 或转 Pipe。  
> **现网起点**：OWUI 0.11.3；Pipe `f797e92d6d3f`；23 public；ST-14 仍 7 个；Banner `usage-guide-v5`。  
> **A 波**：只挂 Filter，A3 红（`input_tokens=27`），已回滚。

关联：`docs/open-webui-text-web-search-plan.md`；`docs/SPEC.md` UX-3 / ST-14。

---

## 0. 目标

Astra / Astra Pro 与现有 7 个文本同一套薄 Web Search。Banner 第一句带 Astra。不上 Controller、不加 Filter 指引、不抬 `$0.05`。

## 1. 已排除（A 波）

- 只扩 allowlist：Filter 本地会写 `server_tools`，真请求工具没出门。
- 只关 `image_generation`：仍 27 token。
- 模型本身：OpenRouter 上与 Sol Pro 同级（`tools`、只出文本、有 search 计价）。

## 2. 本波分步（已确认）

| 步 | 动作 | 过门 |
|----|------|------|
| **C1** | Astra / Astra Pro 的 `meta.capabilities` 改成与 Sol 相同的 **`null`**（整份去掉，不是再拧一个勾） | GET 模型 `capabilities` 为 null |
| **C2** | Filter allowlist + 挂载 default-on（9 个） | `verify_text_web_search --mode final` 绿 |
| **C3** | **只**对两个 Astra 跑现有 Search + Fetch 烟雾 | 各 200；有 hosted `web_search` / Fetch；`input_tokens` 明显大于 27 |
| **C4** | 仅 C3 绿：Banner → `usage-guide-v6`（第一句加 Astra）+ 契约 9 模型 | `verify_stack` 绿 |
| **C3 红** | 剥回 Astra Filter；Banner 不动。档案：保持 `null`（更像 Sol，便于下一刀） | 附件回到 7 |
| **P1** | C3 红之后：只读对照 Pipe（`build_tools` / `_apply_server_tools_metadata` / `ModelFamily`）+ Sol vs Astra 一条请求 | 写出「哪道门」或「必须打日志」 |
| **P2** | 若 P1 不够：Pipe **content-only** 临时日志（不打 key），Sol + Astra 各一条，看完删除 | 另见当时记录；不扩大改逻辑 |

C3 失败不改 Banner。不重跑原 7 的 EVAL-B。

## 3. 不改

Pipe valves / `WEBUI_SECRET_KEY` / `openai.api_configs` / public 23 / `$0.05` 门 / 空 `models/sync`。

## 4. 回滚

- Filter：`TEXT_WEB_SEARCH_MODEL_IDS` 去掉 Astra，再 `apply_text_web_search.py --mode final`。
- 档案：需要时可把 capabilities 写回整排 true（默认不写回）。
- Banner：没升 v6 则不用回。
