# Astra 进 ST-14 薄 Web Search

> **状态**：**P2 已做完并 revert**（2026-09-06）。**F 波（Filter 下一刀）只写了 plan，未确认、未执行。**  
> **现网**：OWUI 0.11.3；Pipe `f797e92d6d3f`；23 public；Banner `usage-guide-v5`；ST-14 仍 7 个；Astra 档案 `capabilities=null`，**无**薄 Filter。

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

**P2（已做、已 revert，Pipe sha 回 `f797e92d6d3f`）：**

同一句提示、同一 `filter_ids`：

| | Sol | Astra |
|--|-----|-------|
| `function_calling` | True | True |
| `image_output` | False | False |
| metadata `server_tools` | `web_search`, `web_fetch` | **`None`** |
| 出门 tools | 2（`openrouter:web_search/fetch`） | **None** |
| `web_search_requests` | 1 | 0 |
| `input_tokens` | 4321 | 27 |

**结论：不是 Pipe 的出图门，也不是 Astra 不会 function calling。** 薄 Filter 对 Astra **没有**写入 `openrouter_pipe.server_tools`。Toggle Filter 重载后仍 `st=None`。

---

## 7. F 波：查薄 Filter 为什么对 Astra 不写 `server_tools`（未确认）

P2 把锅钉在 Filter。A 波已经扩过 allowlist：本地用 GET 模型记录跑 `inlet` **会写** `server_tools`，同一套名单真请求 **不写**。所以下一刀不是「再挂一次」，而是看运行时 Filter 有没有跑、refs 是什么、写有没有写丢。

### 7.1 已钉死（不要再验一遍当新发现）

| 事实 | 含义 |
|------|------|
| OpenRouter 上 Astra ≈ Sol Pro（`tools`、只出文本、有 search 计价） | 模型本身能搜 |
| C 波档案 `capabilities=null`（与 Sol 同）仍红 | 不是 OWUI「整排勾」 |
| P2：Astra `fn=True` `img=False`，`st=None`，出门 tools=0，`input_tokens=27` | Pipe 门开着，没东西可注入 |
| 同脚本、同 `filter_ids`，Sol `st={web_search,web_fetch}`、出门 2 个 tool | 不是烟雾脚本忘带 Filter |
| A 波本地 inlet（完整模型记录）会写 | 仓库 suffix 字符串当时已经能对上 GET 档案 |

### 7.2 假设（F1 用来打掉，不是用来猜着改）

| 编号 | 假设 | 若成立，F1 戳会怎样 |
|------|------|---------------------|
| **H1** | 运行时 refs 是 `openai/gpt-6-astra`（斜杠），allowlist 是 `openai.gpt-6-astra`（点）。GET 档案是点号，所以本地绿、线上红 | `ran=1` `allow=0`，refs 里只有 `/` 没有点号 suffix |
| **H2** | OWUI 对 Astra **没跑** 这根 Filter（调度 / toggle / 模型记录里的 `filterIds` 被跳过） | Pipe 看不到 Filter 戳（`ran` 缺失） |
| **H3** | 运行时 `_is_denied`（refs 误撞 deny，或 caps 带 `image_output`） | `ran=1` `denied=1` |
| **H4** | `__metadata__` 不是 dict。现网 `inlet` 写 `__metadata__ = {}` 只改**局部变量**，从不写回 `body["__metadata__"]`。Sol 的 metadata 是共享 dict 所以绿；Astra 若是 `None`，写了也丢 | `ran=1` `allow=1` `meta_is_dict=0`，Pipe 仍 `st=None`（除非探针同时写回 body） |

H1 单独解释不了「suffix 已含 Astra 且 GET 能匹配」——除非 **运行时** `body.model` / `__model__` 被改成斜杠 OpenRouter id。F1 的 `refs` 就是为了看这件事。

现网相关代码（不要在未确认时改）：

```python
        if self._is_denied(body, __model__, __metadata__) or not self._is_allowlisted(body, __model__):
            return body
        # ...
        if not isinstance(__metadata__, dict):
            __metadata__ = {}   # 局部变量；未写回 body
```

allowlist 是子串：`suffix in refs`；suffix 全是点号（`openai.gpt-5.6-sol`）。deny 早退时**什么都不写**。

### 7.3 方案（顶级 + 略降级，先选再做）

**顶级（推荐）：F1 诊断 → 对症 F2 → 仅绿了才 F3 Banner。**  
Filter 自己没有 event emitter，必须靠 Pipe 把戳打进我们已在收的 stream `events`（P2 同手法）。看完 **必须** revert Pipe + 去掉 Filter 戳。多一轮临时补丁，换的是不再第三次盲挂。

**略降级、简单很多：跳过 F1，Filter 一次做两处便宜修补后直接挂 Astra。**  
1. allowlist 把 `/` 与 `.` 当成同一分隔符（`refs.replace("/", ".")` 再比 suffix）。  
2. `inlet` 无论从参数还是新建 dict，写完都赋回 `body["__metadata__"]`。  
省一轮 Pipe 调试。覆盖 H1+H4。若是 H2 / H3，再红一轮、再剥，Banner 仍不动。

不推荐第三档：再只扩 `ALLOWLIST_SUFFIXES` / 再挂。A 波已经证明这不够。

### 7.4 推荐路径（点头顶级方案后才执行）

| 步 | 动作 | 过门 |
|----|------|------|
| **F1** | Filter `inlet` **无论 allow/deny** 都往 `body["__metadata__"]["openrouter_pipe"]["filter_probe"]` 盖小戳：`ran / allow / denied / meta_is_dict / refs` 头（截断）。Pipe content-only 在 `_apply_server_tools_metadata` 后打一条 stream status（新 marker，例如 `ASTRA_SEARCH_FILTER_PROBE_V1`）。临时把 Astra 挂上薄 Filter（否则 H2 与「没挂」分不清）。Sol + Astra 各一条现有 Search 烟雾。读 events。然后 **立刻** revert Pipe、去掉 Filter 戳；若本波不停 F2，顺手剥 Astra Filter | 两行戳都在；能判 H1–H4（或「Filter 没跑」） |
| **F2** | 只改薄 Filter，按戳选补丁。常见：H1 → `/`≡`.`；H4 → 写回 `body["__metadata__"]`；H3 → 修 deny（先把误撞的 marker/caps 记进本文件，再改）。**不**改 Pipe 业务门、不抬 `$0.05`、不加指引。再挂 Astra，只跑 Search + Fetch | Astra / Pro 各 200；有 hosted `web_search`；`input_tokens` 明显大于 27；Sol 对照仍绿 |
| **F3** | **仅 F2 绿**：契约 `TEXT_WEB_SEARCH_MODEL_IDS` 扩到 9；Banner → `usage-guide-v6`（第一句加 Astra）；`verify_stack` + `verify_text_web_search --mode final` | Banner 与 9 模型一致 |
| **F2 红** | 剥回 Astra Filter；Banner 停在 v5；档案保持 `null`。把 F1 戳写进本文件。不升 Controller，不把「OWUI 对 Astra 不跑 Filter」冒充已修好 | 附件回到 7 |

F1 戳必须同时写 `body["__metadata__"]`，不能只改 inlet 参数：否则 H4 的戳自己也会丢，Pipe 会误判成 H2。

F1 的 Pipe 补丁可复用 `scripts/patch_pipe_astra_search_debug.py` 缩小版（换 marker，多打 `filter_probe`）。**禁止**把 P2 的 `ASTRA_SEARCH_PIPE_DEBUG_V1` 留在现网（当前 sha `f797e92d6d3f` 应已无此 marker）。

剥 Astra：`attach_models` 的 inspect = `TEXT_WEB_SEARCH_MODEL_IDS + wanted`。契约仍是 7 个时，只跑 `apply_text_web_search.py --mode final` **剥不到**已移出的 Astra，必须把两个 Astra id 放进 inspect 再剥。

### 7.5 不改

- Pipe valves / `API_KEY` / `WEBUI_SECRET_KEY` / `openai.api_configs`
- public 23；未绿之前 Banner 仍 v5
- `$0.05` 门、Filter 指引、Search Controller
- EVAL-B / 原 7 的质量重跑
- 空 `POST /api/v1/models/sync`
- 激活 broad `openrouter_web_tools`
- 把 Studio / Live / 论文档绑进本波
- 现网留下任何 debug marker

### 7.6 回滚

- Pipe：content-only revert 到 `f797e92d6d3f`（或当前无 debug 的 sha）
- Filter：去掉 probe 字段；allowlist / 写回 body 仅保留已确认的 F2 补丁
- 挂载：两个 Astra 移出 `filterIds` / `defaultFilterIds`
- Banner：没升 v6 则不用回

### 7.7 确认门

未点头前：**不改实例、不改 Pipe、不改 Filter、不改 Banner、不扩 `TEXT_WEB_SEARCH_MODEL_IDS`。**

请选一档：

1. **顶级**：F1 → 对症 F2 → 绿了才 F3  
2. **略降级**：跳过 F1，直接 `/`≡`.` + 写回 `body["__metadata__"]`，再挂烟雾；红了剥回再议 H2/H3
