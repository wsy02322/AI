# Astra 进 ST-14 薄 Web Search

> **状态**：**P2 已确认执行**（2026-09-06）。Pipe content-only 打一条 stream status，Sol + Astra 各一枪，看完必须 `--revert`。Banner 不动。  
> **现网**：OWUI 0.11.3；Pipe `f797e92d6d3f`；23 public；ST-14 仍 7 个。

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

- Filter：`TEXT_WEB_SEARCH_MODEL_IDS` 去掉 Astra，再 `apply_text_web_search.py --mode final`（`attach_models` 的 inspect 不含已移出 id，剥 Astra 须另写一遍）。
- 档案：需要时可把 capabilities 写回整排 true（默认不写回）。
- Banner：没升 v6 则不用回。

## 5. C 波结果（2026-09-06）

| 步 | 结果 |
|----|------|
| C1 | Astra / Astra Pro `capabilities` → `null`（与 Sol 相同） |
| C2 | 9 模型挂载校验绿 |
| C3 | **红**。Astra search `input_tokens=41`、Pro `1931`（Pro 的大输入不是工具；仍无 `web_search`）。模型仍说没有 web_search |
| 回滚 | Filter 已剥；档案 **保持 null**；Banner 未改 |

C 排除：「整排勾」不是原因。只关 `image_generation` 和整份 `null` 都一样红。

## 6. P1 只读（2026-09-06）

现网模型档案里 `meta.openrouter_pipe.capabilities` **Sol 与 Astra 相同**：`image_output=false`、`video_generation=false`、`vision=true`、`file_input=true`。Pipe 元数据键是 `openrouter_pipe`（与薄 Filter 写入的键一致）。

Pipe 请求路径（`f797e92d6d3f`）：

- `image_output` → `tools=None`，且 `_apply_server_tools_metadata` 直接 return（连 Search 也不注入）
- 无 `function_calling` → 不转发 OWUI tools，但 **仍应** 注入 metadata 里的 `server_tools`
- 因此：若运行时缓存把 Astra 标成出图 → 完全对上 41 token；若只是缺 `function_calling` 而 Filter 跑过 → 应仍能搜

P1 **不能**读 `ModelFamily._DYNAMIC_SPECS` 内存。本环境也没有 VPS 容器日志。

**P2（下一刀，须再动手）：** 不要打到 stdout。在 `_apply_server_tools_metadata` 前后往 **聊天 stream 写一条 status**（我们烟雾已经收 `events`）：`image_output` / `function_calling` / `server_tools` keys / `tools` 条数。Sol + Astra 各一条，看完删补丁。不改业务门。
