# 独立图像 Studio（对标官网最高订阅档）

> **状态**：提案。**未确认不改实例 / 不装第二前端 / 不灌聊天 tools / 不启用 `ENABLE_IMAGE_GENERATION`。**  
> **日期**：2026-09-04  
> **现网**：OWUI **0.11.3**；作图仍是 **路线 S**（切图像模型即出图）。Pipe sha `f797e92d6d3f`。  
> **已声明**：为最高出图/编辑，**接受 OWUI 完全取消作图**；除 OpenRouter 外有 **Gemini 直连**、**xAI/Grok 直连**。OpenAI Images、fal/Replicate **尚未声明**。  
> **宪法**：顶级与略降级一并提案；确认再选。讨论 ≠ 执行。

关联：`docs/SPEC.md` UX-6 / ST-9、`docs/open-webui-openrouter-image-continuity-plan.md`（聊天路径错误模式，**不是**本 Studio）、`docs/open-webui-rebuild-archive.md`。

---

## 0. 这不是什么

| 易混项 | 本方案 |
|--------|--------|
| 聊天里切 Banana / GPT Image（路线 S） | 若选 **IS-A+ / 剥离聊天作图**：OWUI picker **关掉全部纯图像模型**；Banner / 四格 Images 改指向 Studio。旧聊天里的图还在。 |
| 开全局 `ENABLE_IMAGE_GENERATION` / Sol Pro `image_generation` | **Don't**。同会话作图已爆 404 |
| 把 continuity plan 的 Pipe A/C 当「官网 Studio」 | 只补聊天多轮漂移，**没有**画布 / 蒙版 / 版本栈 |
| Notebook N2+ Studio | YouTube 知识产物，不是画图 |
| `handoff/gemini-live-standalone/` | 语音新产品，**不要并进**本文件 |
| ComfyUI | **不是默认**。无拘无束档里作为可选本地/GPU 节点层；未点头不上 |
| 扩新图像家族进 **OWUI picker** | **Don't**。新家族只进 Studio，不进聊天 21 public |

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
| 聊天（现状） | 路线 S；`ENABLE_IMAGE_GENERATION=false` |
| 聊天（若确认剥离） | 9 个纯图像模型 `is_active=false` 且剥 `*`；21 public → **12 文本/搜索**。`verify_stack` / `stack_contract` 必须先改契约再动 |

OpenRouter 官方示例对 GPT Image 2 的「编辑」是 **prompt + `input_references`**，不是永远暴露 OpenAI 旧版 `images/edits` + PNG mask。真蒙版要在 IS0 探针里对每个模型的 `supported_parameters` / passthrough **实测**后再画 UI；不能假设九个模型都吃同一张 alpha mask。

---

## 3. 无拘无束最高档 vs 略降级

「最高 performance」拆开是四件事，不能混成一句：

| 轴 | 官网旗舰在做什么 | 只走现网 OpenRouter+Pipe 的上限 |
|----|------------------|--------------------------------|
| **质量** | 各家最新原生权重 | OpenRouter 上的同一权重，通常够 |
| **编辑锁定** | 官方选区 / 魔棒 / 原生 edits | 多为 prompt + `input_references`；**真 mask 不保证** |
| **延迟 / 吞吐** | 直连 + 流式预览 + `n` 多张 | 多一跳；部分模型无 SSE |
| **功能面** | 画布、历史、likeness、4K、Search grounding | 被 OWUI 聊天壳和 Pipe 裁掉 |

OWUI 取消作图 **只去掉壳**，不自动变快。要顶满四轴，必须 **独立 Studio + 能直连的官方 API**。OpenRouter 留下给没有直连钥匙的长尾（Seedream / Qwen / MAI / Flux 等）。

### IS-A+ — 无拘无束最高档（推荐在你已接受「OWUI 彻底不作图」之后）

独立站点，**完全不经过** OWUI 聊天 / Pipe / Guard。

1. **入口**：`studio.` 或 `/studio`。OWUI 九个纯图像模型关闭；四格「Images」改链到 Studio。  
2. **画布 + 版本 + 笔刷蒙版 + 多参考 + 比例/质量/透明底 + 历史库**（同原 IS-A 产品面）。  
3. **路由（按模型选最快/最完整的上游，不是只认 OpenRouter）**：  
   - **OpenAI 直连**（若有钥匙）：GPT Image 2 / 1.5 → 官方 Images + **mask/edits** + SSE。这是选区锁定的主路径。  
   - **Google 直连**（若有钥匙）：Nano Banana Pro / 2 → 最多 14 参考、1K/2K/4K、官方多轮；Search grounding **只在 Studio**，不进 OWUI。  
   - **xAI 直连**（若 Imagine API / 钥匙存在）：官网魔棒/分割；没有钥匙则 Grok Imagine 仍走 OpenRouter（软编辑）。  
   - **OpenRouter Images**：Seedream、Qwen、MAI、以及未直连的后备。  
   - **fal / Replicate（可选）**：Flux Kontext 等 **强 img2img / inpaint**（Reve 也在 fal）。不自建 GPU 时，这是最接近「无拘无束局部编辑」的托管层。  
   - **ComfyUI（可选，最重）**：ControlNet / 节点级锁定。要 GPU 或云 Comfy。只当上面官方+fal 仍不够像素控制时再上。  
4. **参数**：每个上游一张能力表（IS0 扩到直连 endpoint）。UI 只露出该模型真支持的控件。  
5. **鉴权 / 存储**：独立 session 或复用 OWUI cookie；图存在 **Studio 自己的 volume**（和 `webui.db` 分开备份）。不把巨型 data URI 写回聊天。  
6. **OWUI**：继续聊天 / Sonar / 对比 / Live。Banner 写清「作图去 Studio」。`ENABLE_IMAGE_GENERATION` 保持 false。

**代价**：第二前端 + 可能多把官方钥匙 + Caddy + 独立备份。钥匙不够就那一家退化成 OpenRouter，**不能假装直连**。  
**不做的代价**：继续被 Pipe/聊天裁功能；选区永远软。

### IS-A — 独立 Studio，仍只认 OpenRouter

产品面同 IS-A+，上游 **只有** 现有 OpenRouter key。OWUI 仍可关图像模型。  
编辑锁定、流式、4K grounding 受 OpenRouter 暴露面限制。比 A+ 简单，比 B 完整。

### IS-B — 略降级：OWUI 内薄 Studio

不装第二前端。一条独立 OWUI 入口（专用 Workspace 或最小自定义页），产品面先做：

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

## 4. 达标面

| ID | IS-A+ | IS-A | IS-B |
|----|-------|------|------|
| IS-1 画布多轮 | 必须 | 必须 | 必须 |
| IS-2 版本 / 稳定 URL | 必须 | 必须 | 必须 |
| IS-3 能力表驱动控件 | 必须（多上游） | 必须（仅 OR） | 尽量 |
| IS-4 OWUI | **关掉** 9 个图像模型；public=12；Banner 指 Studio；`verify_stack` 改契约后仍绿 | 默认同左（可暂留路线 S） | 路线 S 零回归 |
| IS-5 选区 | GPT Image **直连** mask 有「区外少漂」探针；无钥匙则标明软蒙版 | OpenRouter 能吃 mask 才承诺 | 不做 |
| IS-6 透明底 / 多参考 / 流式 | 有则开 | 有则开 | 不做 |
| IS-7 聊天 tools | Studio 外永不灌 | 同左 | 同左 |

---

## 5. 施工波次（确认档位后才跑）

### IS0（只读，改实例前）

OpenRouter `GET /api/v1/images/models` + 各 id `/endpoints`。若已有直连钥匙：再打 OpenAI Images、Gemini image、xAI/fal 各一条。表：mask / refs max / `n` / stream / aspect / resolution / `background`。  
**禁止**未写表就做蒙版 UI。不改 OWUI。

### IS-A+ / IS-A

| 波 | 内容 |
|----|------|
| A1 | 薄后端：按路由表打上游 → 落盘 → file URL。A+ 先接「已有钥匙」的直连 + OR 后备 |
| A2 | Studio 页：模型、提示、画布、版本、下载 |
| A3 | 笔刷蒙版 + 能力表灰显 |
| A4 | 多参考、透明底、流式、比例重出 |
| A5 | （仅确认剥离后）OWUI 关 9 个图像模型、改 Banner / `stack_contract` / `verify_stack` |

### IS-B

| 波 | 内容 |
|----|------|
| B1 | 入口形态（须先定：专用 Workspace vs 最小自定义页） |
| B2 | 画布 + 版本 + 参数继承（Pipe 或旁路调用 Images API，**merge-only**，不覆盖 valves） |
| B3 | 若以后要蒙版 → 升 IS-A，不在 B 里硬塞第二前端 |

---

## 6. 风险与禁令

- **第二前端**：IS-A+ / IS-A 才允许。未确认保持 AGENTS「不装第二前端」。  
- **密钥**：Studio **自用**钥匙，不写进 OWUI `openai.api_configs`（保持全 disable）。不把官方 key merge 进 Pipe valves。  
- **空 `models/sync` / 新 `WEBUI_SECRET_KEY`**：仍禁。  
- **Grok 官网魔棒 ≠ OpenRouter 一定有分割 API**。没有就软蒙版。  
- **「无拘无束」= 产品/架构不被 OWUI 裁**，不是绕过各家安全策略或做违法内容。上游拒画就如实显示。  
- 不要把 Studio 绑进 `/custom/entrypoint.sh`。  
- 关 OWUI 图像模型前必须先改 `stack_contract.PUBLIC_MODEL_IDS`，禁止空 sync。

---

## 7. 还要沟通什么（无拘无束档清单）

下面每条都会改架构或钱。没答的当「未确认」，不施工。

### 7.1 档位

- [ ] **IS-A+**（独立 Studio + 能直连就直连 + OWUI 可关作图）  
- [ ] **IS-A**（独立 Studio，只用现有 OpenRouter）  
- [ ] **IS-B**（OWUI 内薄 Studio）  
- [ ] 先 **IS0** 只读探针  

你已接受「OWUI 可彻底不作图」→ 默认按 **IS-A+** 问下面的题。若钥匙一条都没有，A+ 自动落成 A，产品面仍独立。

### 7.2 钥匙（2026-09-04 对照官方文档）

| 钥匙 | 你这边 | 直连实际解锁（不是官网 App 广告） |
|------|--------|----------------------------------|
| **OpenRouter** | 已有（现网） | 长尾 + 后备：Seedream / Qwen / MAI / Flux（若 catalog 有） |
| **Google Gemini** | **已声明有** | Banana Pro/2：**最多 14 参考**、1K/2K/4K、官方多轮。局部编辑是 **语义 inpaint**（「只改 X」），**不是** PNG 像素 mask |
| **xAI** | **已声明有** | `grok-imagine-image-2.0`：`/images/edits` + 最多 **5** 参考。文档是 **整图 + 指令**。`grok.com` 的魔棒/分割 **没有**写进这份 edits API |
| **OpenAI Images** | **未声明** | 这是 **真笔刷 mask**（`/v1/images/edits` + 同尺寸 PNG alpha）和 GPT Image 2 官方 SSE 的主路径。没有它，选区只能软 |
| **fal / Replicate** | **未声明** | Flux Kontext 等强 img2img/inpaint，不必 GPU。比「再加一把 OpenAI」更接近「无拘无束局部控制」的托管层 |
| **ComfyUI** | 默认不上 | 节点级锁定；要 GPU |

**结论**：有 Gemini + xAI 直连，已经值得做 **IS-A+**（独立 Studio，按模型打不同上游）。  
**还顶不满 ChatGPT Images 选区**，除非补 **OpenAI Images 钥匙**（或 fal Kontext 当第二蒙版引擎）。  
没有的不装假直连；官网 App 有、API 文档没有的控件，UI 要么不做，要么标明「软」。

### 7.3 从 OWUI 剥多干净

- [ ] **关 picker 里全部纯图像模型**（21→12），Banner / 四格改「去 Studio」  
- [ ] 先双轨：聊天暂时还能切图像，Studio 上线后再关  
- [ ] 旧聊天里的图：只读保留（默认） / 迁到 Studio 库  

聊天里 **看图 / 理解图**（Grok、Gemini 文本模型）默认 **留下**，只剥「生成」。若也要剥视觉理解，另说。

### 7.4 产品范围（避免做成第二个聊天）

- **视频**（Grok Imagine 视频、Seedance 等）：进 Studio 第一年 / Later / 永不？默认 **Later**（Wave 1 仍是另线）。  
- **likeness / 人物一致库**：要 / 不要（隐私+存原图）。  
- **一次出 n 张草稿**：要（贵、快选） / 只要 1 张。  
- **谁能用**：仅你 / 现网所有登录用户。  
- **域名**：`studio.micropigeon.com` / `micropigeon.com/studio`。  
- **登录**：复用 OWUI 账号 / Studio 独立账号。

### 7.5 重控制层（默认可先不上）

- [ ] **不上 ComfyUI**（默认）。官方 mask + fal Kontext 先打满。  
- [ ] **要 ComfyUI**：接受 GPU 或云 Comfy、节点 UI、另一套备份。  
- [ ] **要 fal/Replicate、不要 Comfy**：托管 inpaint，无 GPU。

### 7.6 运维

- 图库存哪：Studio 独立 volume（推荐） / 仍写 `webui.db` files。独立库要 **另备份**，升配时别只备 OWUI。  
- 月费心理上限（直连 4K + `n` + fal 会明显贵于现在「聊天里偶发出一张」）。  
- VPS：Caddy 反代一条新服务；**不要**进 OWUI 容器。

### 7.7 明确不做（除非你改口）

绕过上游安全网、把 Studio 密钥写进 OWUI `api_configs`、为 Studio 换 Realtime 镜像、把 Flux/新家族塞回 OWUI picker、空 `models/sync`。

---

## 8. 请直接回（最短）

已知：Gemini + xAI + OpenRouter；接受 OWUI 可彻底不作图。还缺：

1. **OpenAI Images 钥匙**：能开 / 没有 / 不打算开  
2. **fal 或 Replicate**：能开 / 不要  
3. OWUI：**Studio 能用再关图像模型**（推荐） / **现在就关**  
4. 视频进第一年？**默认 Later**  
5. 谁能用：仅你 / 现网登录用户  
6. 域名 + 登录：`studio.` vs 路径；复用 OWUI 账号 vs 独立  
7. Comfy：**不上**（推荐） / 要  

确认前：**不改** Pipe、不改 picker、不装前端、不向 VPS 要新容器。钥匙未交到 Studio 环境变量前，IS0 只能打 OpenRouter 公开 catalog，打不了你的直连额度。
