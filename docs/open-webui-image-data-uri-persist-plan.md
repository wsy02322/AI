# 生成图 data URI 落盘（ST-13）— **已执行**

> **状态**：**已执行**（2026-09-03）。P1 + P2 均已上现网，`verify_image_data_uri_persist.py` **16 ok / 0 err**。
> **Pipe sha**：`7415c2e4347a` → **`f797e92d6d3f`**。Guard sha `2201a71cb229` → **`1cef7c0da5ac`**。
> **ST 编号**：**ST-13** = 生成图落盘为 file URL。不要和 ST-11（Fable 续聊）/ ST-12（Follow-up 关）混号。
> **未动**：valves / `API_KEY` / Banner / models / 镜像 / `api_configs` / `WEBUI_SECRET_KEY`。蒙版 inpainting 仍为 Later。

关联：`docs/open-webui-openrouter-image-continuity-plan.md` §10（131072 溢出旧记录）、`AGENTS.md` Pipe 更新 Runbook。

---

## 1. 事故与根因

**现象**（2026-09-03T16:08:13Z，error id `77de6621c4ab134c`）：切到 `google/gemini-3.1-flash-image` 报

```
400 INVALID_ARGUMENT
The input token count exceeds the maximum number of tokens allowed 131072.
```

**根因链**（三处均已在现网 Pipe `content` 中核对）：

1. `_materialize_image_entry` 的 dict 分支把 `url` / `image_url` / `imageUrl` / `content_url` 的**字符串原样返回**，不落盘：

```python
for key in ("url", "image_url", "imageUrl", "content_url"):
    candidate = entry.get(key)
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip()          # data: 也直接返回
```

紧随其后的 `b64_json` / `b64` / `base64` 分支才调 `_persist_generated_image`。**同一份 base64，走字符串入口 `_materialize_image_from_str` 会落盘并返回 `/api/v1/files/<id>/content`，走 dict 的 url 分支就不会。**

2. `_render_image_markdown` 把该返回值拼成 `![Generated image N](<url>)` 写进助手消息 → 5,385,652 字符 data URI 落进 `webui.db`（该 chat 10.8MB）。alt 文本与 Pipe 的 `f"Generated image {count}"` 完全一致，可证是 Pipe 渲染，不是模型自己吐 markdown。

3. 下一轮 `_append_assistant_text_chunks(assistant_text)` 把助手正文**原样**放回上下文。全 Pipe 无一处从助手正文剥 markdown 图。base64 按**文本** token 计，约 130 万 → 任何 128k 模型必 400。

**量级**：`gemini-3.1-flash-image` 官方 context window = **131,072**，每张输入图 **1,120 token**。同一张图走 image part 只算 1,120，走文本约 130 万——差三个数量级。

**这与上游自己的策略相反。** 输入侧 `_to_input_image` 的 docstring 写明：

> Image data URLs and remote URLs are ALWAYS saved to storage … inline image payloads significantly degrade UI performance and storage efficiency.

输入侧永远落盘，输出侧的 dict-url 分支却不落盘。**ST-13 是补这个不一致，不是加新特性。**

## 2. 为什么不是「provider 宕机」

当天多家模型过载，但这一枪与过载无关：

| 判据 | 结论 |
|------|------|
| 错误类别 | 过载是 `429` / `503` / `provider_overloaded`；这次是 `400` + `INVALID_ARGUMENT` + 精确 token 数，**确定性校验**，重试无用 |
| 131072 是否降级口径 | **否**。Google 文档写死 `gemini-3.1-flash-image` = 131,072 |
| 是否边缘超限 | **否**。约 130 万 token，即使 1M 口径端点也过不去 |

过载的真实作用是**触发器**，并让这个 Bug 更容易被踩：

- 模型都在挂 → 用户在**同一线程内跨模型接力**（Grok Imagine → Qwen → Banana）。平时一条线程一个图像模型，踩不到。
- OpenRouter 降级改走备用 provider 时，返回形状可能从 `b64_json` 变成 `image_url.url` —— 恰好只有后者不落盘。

即触发频率挂在**上游稳定性**上，不可预测，且每次都留下**永久** DB 污染。这正是该在 Pipe 里堵死的缺陷。

---

## 3. P1（根治）— Pipe content-only 补丁

**改动**：`_materialize_image_entry` 的 url 循环里，仅当 `candidate` 是**字符串且以 `data:` 开头**时改走 `_materialize_image_from_str`（已有函数，会落盘）；落盘失败则**回退原 data URI**。

```python
for key in ("url", "image_url", "imageUrl", "content_url"):
    candidate = entry.get(key)
    if isinstance(candidate, str) and candidate.strip():
        text = candidate.strip()
        if text.startswith("data:"):
            stored = await _materialize_image_from_str(text)
            return stored or text          # 落盘失败 → 保持现状，图仍可见
        return text
    if isinstance(candidate, dict):
        ...                                # nested 递归不变
```

**边界（刻意不动）**：`http(s)`、`/api/v1/files/`、相对路径全部保持 `return text` 原样，`http(s)` 行为不变。nested dict 递归不变——递归回到本函数，内层 `{"url": "data:…"}` 同样受益。

### 3.1 落盘失败语义：**回退 data URI**（与 VPS agent 意见不同）

VPS agent 倾向「丢图 + 状态提示」，理由是回退等于没修。我主张**回退**：

- 落盘失败（`_get_storage_context()` 拿不到 request/user）是**罕见且瞬时**的。为此让用户**看不到图**，是一个比现状更差的可见回归。
- 「回退等于没修」只在没有 P2 时成立。**P2 落地后，历史里的 data URI 不会再被回灌**，所以回退最坏只是这一张画布在下一轮丢失，**不会** 400。
- 简单稳定优先（宪法 2）：`stored or text` 一个表达式，无新分支、无新状态码。

落盘成功时 `_materialize_image_from_str` 自带 `IMAGE_BASE64_SAVED` 状态提示，失败静默。若要失败也提示，需另加 emit ——**本 plan 不加**，避免在错误路径上引入新的 event emitter 调用。

### 3.2 P1 之后画布仍在

Pipe 用 `_markdown_images_from_text` 解析助手正文的 markdown URL → `last_assistant_images` → 配合 `IMAGE_INPUT_SELECTION=user_then_assistant`、`MAX_INPUT_IMAGES_PER_REQUEST=5`。

只要画布是 file URL，`_to_input_image` 会把它当**真正的 image part** 内联（1,120 token），连续改图正常。**§5A 不需要我们自己造**——上游已实现，我们只需让画布不是 data URI。

**P1 不修存量**：已在 DB 里的 5.4MB 不会因为打了补丁而消失。

---

## 4. P2（兜底）— Guard content-only 补丁

**改动**：`openrouter_image_context_guard` 保留集合里的那张画布，**只剥 `data:image`，保留 `/api/v1/files/`**。其余逻辑（保留集合的选法、非保留消息全剥）不变。

### 4.1 不设阈值（与 VPS agent 意见不同）

VPS agent 提 1MB 阈值。按文本 token 折算，1MB base64 ≈ 25 万 token，**本身就已超 131k**；要压到万级需把阈值降到几十 KB，那等于「任何 data URI 都不留」。所以直接去掉阈值：

- **任何**尺寸的 `data:image` 都不该以**文本**形式回灌。
- P1 落地后新会话的画布都是 file URL，P2 对新会话是 **no-op**；只有旧线程会命中。
- 少一个要调的旋钮（宪法 2）。

### 4.2 保护边界

- **当前用户消息不动**（已在保留集合内）。用户新贴的图仍照常送出。
- 非保留消息保持现有行为：`data:` 与 `/api/v1/files/` 都换占位（历史图本来就不该重送）。
- 画布若是 file URL → **完全不动**。

### 4.3 占位文案

现状 `[Earlier image omitted to reduce context size]` 没告诉用户怎么办。改为可执行的一句，例如：

```
[Earlier image omitted to fit the model's context. Start a new chat and attach only the image you want to edit.]
```

英文（对齐 §7.3 用户侧英文）。

---

## 5. 不做什么

- **不改** Pipe valves / `API_KEY`（`AUTO_CONTEXT_TRIMMING`、`IMAGE_INPUT_SELECTION`、`MAX_INPUT_IMAGES_PER_REQUEST`、`BASE64_MAX_SIZE_MB` 全部保持默认）
- **不开** middle-out「再一次」——它默认已开，且救不了 130 万 token
- **不改** Banner / models / `access_grants` / 镜像 / `api_configs` / `WEBUI_SECRET_KEY`
- **不做** §5A 自研载荷组装（上游已有）
- **不迁移**存量 chat 里的 data URI（要改用户 chat 记录，风险高于收益；用 P2 兜住）
- **不动** `SEND_CACHE_SESSION_ID`（宕机时把对话钉在同一 provider 可能更糟，但这是另一议题，需单独确认）

---

## 6. Marker / 脚本 / 验收

| 项 | 值 |
|----|-----|
| P1 marker | `IMAGE_DATA_URI_PERSIST_V1` |
| P2 marker | `IMAGE_CONTEXT_DATA_URI_CAP_V1` |
| P1 脚本 | `scripts/patch_pipe_image_data_uri_persist.py`（content-only，marker 已在则 no-op） |
| P2 脚本 | `scripts/patch_guard_image_context_data_uri.py`（content-only） |
| 离线单测 | `scripts/test_patch_pipe_image_data_uri_persist.py`（沿用 `test_patch_pipe_*.py` 模式） |
| 现网验收 | `scripts/verify_image_data_uri_persist.py` |

`stack_contract.py` 的 `PIPE_PATCH_MARKERS` 增加 `IMAGE_DATA_URI_PERSIST_V1`，使 `verify_stack.py` 一并守护。

### 6.1 验收探针（`verify_image_data_uri_persist.py`）

1. Pipe `content` 含 `IMAGE_DATA_URI_PERSIST_V1`；Guard `content` 含 `IMAGE_CONTEXT_DATA_URI_CAP_V1`。
2. 三个 Guard 仍 global active；Pipe valves ST-4/5/6 未漂（只读，不写）。
3. **落盘 E2E**：用 `qwen.qwen-image-3-pro` 出一张图 → 助手消息含 `/api/v1/files/`、**不含** `data:image`、长度 < 4KB。
4. **续聊 E2E**（正是事故场景）：同一 chat 切 `google.gemini-3.1-flash-image` 发纯文字改图指令 → **200**，不得 400/131072。
5. **P2 合成回归**：`POST /api/chat/completions`，history 里塞一条约 2MB 的 `![x](data:image/png;base64,…)` 助手消息 → **200**（Guard 已剥）。不依赖那条 10.8MB 旧 chat。
6. 第 3/4 步各花一次图像生成额度；宕机期跑可能因上游 429/503 失败——**那是环境问题，不是 ST-13 回归**，重跑即可。

---

## 7. Runbook 与容器重建

**Pipe `content` 在 `webui.db`,不在磁盘。** 所以：

| 场景 | 补丁是否丢 |
|------|------------|
| 容器重建（保留 volume / 还原 `webui.db`） | **不丢**。无需 entrypoint 幂等重放 |
| Admin 更新 / 重装 Pipe | **会丢** → 必须重跑 P1 脚本 |
| Guard Function 被覆盖 | 会丢 → 重跑 P2 脚本 |

即与 `/opt/open-webui/custom/strip_bound_reasoning.py`（entrypoint 幂等应用**磁盘**文件）性质不同，ST-13 不需要 entrypoint 介入。

Runbook 插入位置：`AGENTS.md` → Pipe 更新 Runbook，第 8 步（Fable marker）之后新增

```
9. 若 Pipe 丢了 ST-13 marker：python3 scripts/patch_pipe_image_data_uri_persist.py
```

原第 9/10 步顺延。

---

## 8. 上游

`_materialize_image_entry` 的 dict-url 分支与 `_to_input_image` 的「ALWAYS saved to storage」策略不一致，属上游可修 Bug。**建议**向 `rbb-dev/Open-WebUI-OpenRouter-pipe` 报一条 issue，长期免维护本地补丁。**本 plan 不含**提交 issue 的动作（需用户点头，且不代表用户身份发言）。

---

## 9. 决策记录

| 日期 | 决策 |
|------|------|
| 2026-08-18 | 旧 131072 修复：`openrouter_image_context_guard` + chat 路径 `middle-out` / `context-compression`（挡不住「保留的画布本身是巨型 data URI」） |
| 2026-09-03 | 定位到 `_materialize_image_entry` dict-url 分支不落盘；写成本 plan（ST-13） |
| 2026-09-03 | 用户确认「先处理本次，蒙版等顶级功能后续再做」→ **P1 + P2 已执行**；落盘失败**回退 data URI**、P2 **不设阈值**（见 §3.1 / §4.1） |

## 10. 执行结果（2026-09-03）

`python3 scripts/verify_image_data_uri_persist.py` → **16 ok / 0 err**：

| 探针 | 结果 |
|------|------|
| 7 个 Pipe marker（含 `IMAGE_DATA_URI_PERSIST_V1`） | 全在 |
| Guard `IMAGE_CONTEXT_DATA_URI_CAP_V1` + active + global | 通过 |
| valves ST-4/5/6 与 `API_KEY` | 未漂、仍在（content-only 更新） |
| Qwen Image 3 Pro 出图 | 助手回复 **81 字符**（事故那条是 5,385,652），含 `/api/v1/files/`，无 `data:image` |
| Nano Banana 2 在该画布上续聊改图 | **200**（正是 `77de6621c4ab134c` 那一轮） |
| history 塞 2MB 内联 data URI | **200**（Guard 已剥） |

`verify_stack.py`：**26 ok / 1 err**。唯一 err 是 **picker 27 ≠ 21**，改前 baseline 即存在，与 ST-13 无关；见 `docs/VERSIONS.md`「未决漂移」。

离线单测 `scripts/test_patch_pipe_image_data_uri_persist.py`：**16 tests OK**（含落盘失败回退、`http(s)`/file URL 不变、当前用户消息不动、非图像模型不动）。
