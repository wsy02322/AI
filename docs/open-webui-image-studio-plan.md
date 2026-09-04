# 独立图像 Studio（对标官网最高订阅档）

> **状态**：提案。**未确认不改实例 / 不装第二前端 / 不灌聊天 tools / 不启用 `ENABLE_IMAGE_GENERATION`。**  
> **日期**：2026-09-04  
> **现网**：OWUI **0.11.3**；作图仍是 **路线 S**（切图像模型即出图）。Pipe sha `f797e92d6d3f`（含 Images API、ST-13 `IMAGE_DATA_URI_PERSIST_V1`）。  
> **宪法**：顶级与略降级一并提案；确认再选。讨论 ≠ 执行。

关联：`docs/SPEC.md` UX-6 / ST-9、`docs/open-webui-openrouter-image-continuity-plan.md`（聊天路径错误模式，**不是**本 Studio）、`docs/open-webui-rebuild-archive.md`。

---

## 0. 这不是什么

| 易混项 | 本方案 |
|--------|--------|
| 聊天里切 Banana / GPT Image（路线 S） | **留下**。Studio **另开入口**，不塞回聊天 tool 条 |
| 开全局 `ENABLE_IMAGE_GENERATION` / Sol Pro `image_generation` | **Don't**。同会话作图已爆 404 |
| 把 continuity plan 的 Pipe A/C 当「官网 Studio」 | 只补聊天多轮漂移，**没有**画布 / 蒙版 / 版本栈 |
| Notebook N2+ Studio | YouTube 知识产物，不是画图 |
| `handoff/gemini-live-standalone/` | 语音新产品，**不要并进**本文件 |
| ComfyUI | 默认 **Don't**。只有选了「节点工作流当主 UI」才另确认 |
| 扩新图像家族进 picker | **Don't**。Studio 只用现有 9 个 public 图像模型 |

OWUI 升级已落地。本文件是下一条主线，不搭车上 Tika / N2 / Realtime。

---

## 1. 官网最高档实际在卖什么（2026-09 核对）

不是「模型更能画」。三家旗舰卖的是 **独立 Images 面 + 当前画布 + 局部编辑**。

| 面 | ChatGPT（Images / Plus·Pro） | Grok（Imagine Quality / Image 2.0） | Gemini / AI Studio（Nano Banana Pro / 2） |
|----|------------------------------|-------------------------------------|------------------------------------------|
| 入口 | 侧栏 **Images**；对话里也能出图 | `grok.com/imagine`，与聊天分开 | Gemini 应用 + AI Studio 图像面 |
| 画布 | 点开图进编辑器；Undo / Redo | 当前图为工作对象 | 多轮对话式改同一张 |
| 局部编辑 | **选区笔刷** inpaint；官方承认选区不总是像素级 | **魔棒 / 分割**改一块、其余尽量不动 | 语义多轮改；API 最多 **14** 张参考 |
| 画布扩展 | outpaint / 改比例 | **Smart Resize** 重构图到多种比例 | 极端比例（含 1:8 等）；1K/2K/4K |
| 参考 | 上传图 + 一次 likeness | 多参考合成（产品面约 3～5） | 最多 14 参考 |
| 其它 | 透明底、 pensets、**Images with thinking**（付费） | 去背透明导出、排印更稳 | Search grounding（偏 API）；SynthID |
| 模型 | GPT Image 2 / 1.5 产品层 | Imagine 2.0 Quality Mode | NB Pro / NB2 / Lite |

**现网路线 S 有的**：同源模型上限（Banana Pro、GPT Image 2、Grok Imagine 2.0、Seedream 5…）。  
**没有的（主缺口）**：独立 Images 入口、**canonical 画布**、选区/蒙版 UI、版本栈、比例/质量/透明底控件、多参考合成面、生成历史库。聊天多轮仍是全图重绘，夜空/肤色会漂（continuity plan §4 已测）。

单张质量可以够；**产品层**才是和官网最高档的差距。

---

## 2. 现网资产（Studio 必须复用，禁止另起一套模型栈）

| 项 | 值 |
|----|-----|
| 出图通道 | OpenRouter **`POST /api/v1/images`**（Pipe 已路由 `gpt-image-*` / `seedream-5*`；Gemini 走 chat/images 混合） |
| 统一 Images API | 比例、分辨率、quality、`background`、`input_references`、部分模型 SSE 预览。能力以 `GET /api/v1/images/models` 为准 |
| public 图像模型（9） | Banana Pro、Banana 2、GPT Image 2、GPT-5.4 Image 2、Seedream 5 Pro/Lite、MAI-Image-2.5 Pro、Qwen Image 3 Pro、Grok Imagine 2.0 |
| 落盘 | Pipe `IMAGE_DATA_URI_PERSIST_V1`（ST-13）；Studio **必须**用 file URL，禁止聊天里堆 `data:` |
| Guard | `image_tool_guard` / `image_context_guard` **保持**。Studio 请求不带 tools |
| 聊天 | 路线 S 不动；`ENABLE_IMAGE_GENERATION=false` |

OpenRouter 官方示例对 GPT Image 2 的「编辑」是 **prompt + `input_references`**，不是永远暴露 OpenAI 旧版 `images/edits` + PNG mask。真蒙版要在 IS0 探针里对每个模型的 `supported_parameters` / passthrough **实测**后再画 UI；不能假设九个模型都吃同一张 alpha mask。

---

## 3. 两档方案（请选一档；未选不动手）

### IS-A — 顶级：独立 Image Studio

对标 ChatGPT Images 页 + Grok Imagine + Gemini 图像面的**交集旗舰**：

1. **独立入口**（`studio.micropigeon.com` 或 `micropigeon.com/studio`）。不进聊天 Integrations，不改四格。  
2. **当前画布**是唯一真相：生成 / 上传 / 上一版都落到同一张「工作图」。  
3. **版本栈**：每次出图一条版本；Undo / Redo / 从历史分叉。  
4. **编辑器**：笔刷选区 + 指令（inpaint）。模型吃 mask 就走 mask；不吃则蒙版栅格作为第二参考 + 强 preserve 句（UI 仍是笔刷，用户不感到「这个模型没蒙版」）。  
5. **控件**：模型（上述 9 个）、比例、分辨率、quality、张数 `n`（模型允许时）、透明底（模型允许时）、参考图槽（按该模型 `input_references` 上限裁）。  
6. **历史库**：用户自己的生成图，可再送进画布。文件进现有 OWUI `/api/v1/files` 或 Studio 自用 volume（须备份，同 L0：JWT 不持久化）。  
7. **流式预览**：GPT Image 系若 `supports_streaming` 则 SSE 渐进；其它模型转圈即可。  
8. **不做**：ComfyUI 节点、聊天 native `generate_image`、给图像模型灌 Search / tools、扩新家族。

**实现形状**：独立前端 + 薄后端（只转发 OpenRouter Images + 落盘 + 会话/版本）。鉴权可复用 OWUI 登录或独立 session。文档放本仓库 `docs/` + 脚本；**不要**把前端塞进 OWUI 镜像层（升级 0.11.3 刚证明 custom 补丁易碎）。

**代价**：第二套前端/部署（宪法里「未确认不装第二前端」——选 IS-A 就是在确认这一条）。VPS 要 Caddy 路由、备份策略。蒙版在 Gemini/Grok 的 OpenRouter 槽上可能是「软蒙版」，像素锁定弱于 ChatGPT 选区。

**不做的代价**：继续只有路线 S，官网级局部锁定和独立创作面不存在。

### IS-B — 略降级、简单稳定得多：OWUI 内薄 Studio

不装第二前端。用 **一条独立 OWUI 入口**（单独 Workspace / 固定图像模型的专用页，或 Admin 允许的最小自定义页），产品面先做：

1. 当前画布 + 版本列表（仍落 OWUI files）。  
2. 提示词只发**本轮指令**；参考只带**上一张画布**（continuity plan A，搬到这个入口，不改聊天默认行为）。  
3. 比例 / quality 继承上一轮。  
4. 上传参考图。  
5. **不做**第一波笔刷蒙版、Smart Resize、likeness 库、SSE 预览。

后端仍是现有 Pipe / OpenRouter；运维 = 现网一条站点。

**代价**：入口和编辑器受 OWUI 壳限制，很难做到 ChatGPT Images 页的手感。蒙版仍缺，局部锁定弱。  
**收益**：几天内可验收「有画布的独立面」，不增加镜像/前端栈。

### 明确不够格（不单提案这一档）

只在聊天 Pipe 上打 continuity A/C/B、不给独立入口——**到不了「官网最高档 Studio」**。那是图像连续性增强，不是本主线。若选 IS-A/B，聊天连续性可当附属小补丁，不能冒充 Studio 已达标。

---

## 4. 达标面（选 IS-A 才全部验收；IS-B 只验 1–4）

| ID | 必须 |
|----|------|
| IS-1 | 不打开聊天也能完成：出图 → 改一句 → 再出一张，且工作对象是**同一画布** |
| IS-2 | 历史版本可回退；文件是稳定 URL，不是聊天里的巨型 data URI |
| IS-3 | 九个 public 图像模型可切换；参数按该模型能力表裁剪，禁止硬编一套比例导致 400 |
| IS-4 | 聊天路线 S、Banner、21 public、Guard、`ENABLE_IMAGE_GENERATION=false` **零回归**（`verify_stack.py` 仍绿） |
| IS-5 | **选区编辑**（IS-A）：笔刷 + 指令；至少 GPT Image 2 路径有探针证明「选区外明显少漂」 |
| IS-6 | 透明底 / 多参考 / 流式预览：模型能力在则开，不在则灰掉，不假装三家都能 |
| IS-7 | 不把 Search grounding / 聊天 tools 接到图像模型上 |

---

## 5. 施工波次（确认档位后才跑）

### 两档都要的 IS0（探针，改实例前）

`GET https://openrouter.ai/api/v1/images/models` + 各 public 图像 id 的 `/endpoints`。写成表：mask / `input_references` max / `n` / stream / aspect / resolution / `background`。  
**禁止**未写表就做蒙版 UI。探针脚本只读 OpenRouter，不改 OWUI。

### IS-A

| 波 | 内容 |
|----|------|
| A1 | 薄后端：generate / edit（canvas + 可选 mask）→ OpenRouter Images → 落盘 → 返回 file URL |
| A2 | Studio 页：模型、提示、画布、版本、下载 |
| A3 | 笔刷蒙版 + 能力表驱动的灰显 |
| A4 | 多参考槽、透明底、GPT 系流式预览、比例重出 |

### IS-B

| 波 | 内容 |
|----|------|
| B1 | 入口形态（须先定：专用 Workspace vs 最小自定义页） |
| B2 | 画布 + 版本 + 参数继承（Pipe 或旁路调用 Images API，**merge-only**，不覆盖 valves） |
| B3 | 若以后要蒙版 → 升 IS-A，不在 B 里硬塞第二前端 |

---

## 6. 风险与禁令

- **第二前端**：IS-A 才允许；IS-B 不允许。未确认保持 AGENTS「不装第二前端」。  
- **密钥**：Studio 用现有 OpenRouter key（Pipe / `api_keys[0]` 形状），**merge**；不启用 `openai.api_configs`。  
- **空 `models/sync` / 新 `WEBUI_SECRET_KEY`**：仍禁。  
- **Grok 官网魔棒 ≠ OpenRouter 一定有 `mask_indexs`**。没有就软蒙版，不写假按钮。  
- **GPT-5.4 Image 2**：OpenRouter 建议 generational 用专用 image 模型；Studio 默认 GPT Image 2 / Banana Pro，5.4 Image 2 当「带 thinking」档。  
- 升级 OWUI 时 Studio 若独立部署，**不要**绑进 `/custom/entrypoint.sh`。

---

## 7. 请确认（选一项即可）

- [ ] **IS-A** 独立 Studio（第二前端 + 画布 + 蒙版目标）。顶级。  
- [ ] **IS-B** OWUI 内薄 Studio（无第二前端，先画布/版本，蒙版 Later）。简单稳定。  
- [ ] 先只跑 **IS0 探针表**（仍不改实例），看清九个模型谁真吃 mask 再选 A/B。  
- [ ] 暂缓。继续用路线 S；升级后的使用问题另开。

默认建议：**先 IS0（只读）→ 再锁 IS-A**。没有探针就承诺「和 ChatGPT 选区一样」会骗人。若你要最快可玩、先接受无笔刷：**IS-B**。

确认前：**不改** Pipe、不改 picker、不装前端、不向 VPS 要新容器。
