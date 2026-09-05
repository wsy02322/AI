# 独立图像 Studio（对标官网最高订阅档）

> **状态**：**施工中（IS-A+）**。决策见 §7。代码在 `image-studio/`。VPS 按 `image-studio/DEPLOY.md` 起独立容器并注入钥匙；**尚未**关 OWUI 图像模型。  
> **日期**：2026-09-04  
> **现网**：OWUI **0.11.3**；作图仍是路线 S。Pipe sha `f797e92d6d3f`。  
> **档位**：独立站点 `image.micropigeon.com`；OpenAI + Gemini + xAI **直连** + OpenRouter 长尾。ComfyUI 不上。视频 Later。  
> **宪法**：讨论 ≠ 执行。钥匙不入库、不进聊天。

关联：`docs/SPEC.md` UX-6 / ST-9、`docs/open-webui-openrouter-image-continuity-plan.md`（聊天路径错误模式，**不是**本 Studio）、`docs/open-webui-rebuild-archive.md`。

---

## 0. 这不是什么

| 易混项 | 本方案 |
|--------|--------|
| 聊天里切 Banana / GPT Image（路线 S） | **先双轨**：聊天还能切图像；Studio 另站。关 picker 须另确认。看图理解一直留。 |
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

1. **入口**：`https://image.micropigeon.com`。OWUI 图像模型 **先保留**；Studio 能用且你点头后再关（也可能一直双轨）。  
2. **画布 + 版本 + 笔刷蒙版 + 多参考 + 比例/质量/透明底 + 历史库**。  
3. **路由**：  
   - **OpenAI 直连**（已有钥匙）：GPT Image 2 → 官方 Images + **PNG mask** + SSE。选区主路径。  
   - **Google 直连**（已有）：Banana Pro / 2 → 最多 14 参考、4K、语义「只改 X」。  
   - **xAI 直连**（已有）：`grok-imagine-image-2.0` edits，最多 5 参考。官网魔棒若 API 没有就不做假按钮。  
   - **OpenRouter**：Seedream / Qwen / MAI 等长尾。  
   - **fal / Replicate**：v1 **不开**（见 §7 白话）。以后选区仍不够再另确认。  
   - **ComfyUI**：**不上**。  
4. **参数**：每个上游一张能力表（IS0 扩到直连 endpoint）。UI 只露出该模型真支持的控件。  
5. **鉴权（已定，求简单）**：不建第二套用户表。`image.` 自己的登录页，用 **和 OWUI 同一套账号密码** 调现网 `POST /api/v1/auths/signin`；成功后发 Studio 自己的 httpOnly cookie（只挂在 `image.micropigeon.com`）。OWUI 重建掉 JWT 时，Studio 会话各自过期、再登一次即可（L0 同类）。不把 OWUI cookie 硬挂到父域（脆）。  
6. **存储**：Studio **独立 volume**，升配时和 `webui.db` **分开备**。  
7. **OWUI**：聊天 / Sonar / 对比 / Live / **看图理解** 不动。`ENABLE_IMAGE_GENERATION` 保持 false。图像模型先不关。

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
| IS-4 OWUI | 聊天看图留下；图像模型 **先留**；`verify_stack` 现契约仍绿。关模型另确认 | 可双轨 | 路线 S 零回归 |
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
| A5 | （另确认）才关 OWUI 图像模型 / 改 Banner 与 `stack_contract` |

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

## 7. 已确认（2026-09-04）

| 项 | 决定 |
|----|------|
| 档位 | **IS-A+**：独立 Studio，直连优先 |
| 域名 | `image.micropigeon.com` |
| 谁能用 | 现网 **所有已有 OWUI 账号**（同一套用户，不新建用户库） |
| 登录 | Studio 登录页 → OWUI `signin` 验密码 → `image.` 自己的 cookie。细节见 §3.5 |
| 钥匙 | OpenRouter + **OpenAI Images** + **Gemini** + **xAI**。钥匙只进 Studio 环境变量，不进 git、不进 OWUI `api_configs`、不 merge Pipe |
| fal / Replicate | **v1 不开**（白话见下）。选区不够再另确认 |
| ComfyUI | **不上** |
| OWUI 图像模型 | **先保留**（双轨）。Studio 稳定后你再决定关还是留 |
| 聊天看图 | **留下**（Grok / Gemini 文本模型照常理解图） |
| 视频 | **图像搞好之前不做** |
| likeness 库 | **v1 不做**（白话见下） |
| 一次出几张 | 默认 **1 张**（贵）。以后再加「出 4 张草稿」 |
| 图库 | Studio 独立 volume，和 `webui.db` 分开备份 |

### fal / Replicate 是什么（白话）

不是新模型家族，是 **别人家的出图服务器**。你按张付钱，对方有 GPU，所以你 **不用自己买显卡**。

上面常挂 Flux Kontext 一类：擅长「看着这张图，只改一块」。有点像租来的局部修改器。

你现在已经有 **OpenAI 真蒙版 + Gemini 语义改 + Grok 直连编辑**。v1 够打官网选区主路径。再开 fal = 多一把钥匙、多一家账单、多一套故障。所以 **先不开**。以后若笔刷仍不够狠，再开也不迟。

### likeness 库是什么（白话）

ChatGPT Images 可以 **把你的脸上传一次**，以后出图都长得像你，不用每次从相册找。

代价：服务器上长期存一张你的脸；还要管「这张脸能用在哪些图」。隐私和误用都重。

v1 **不做这个库**。需要像某个人时，**这一次上传参考图** 就行（和现在聊天贴图一样，用完不必进「脸档案」）。

---

## 8. 开工进度

2026-09-04 已说开工。仓库侧 A1–A3 已落地（`image-studio/`）：登录、画布、版本、OpenAI 笔刷蒙版归一化、无钥匙 503。

| 步 | 状态 |
|----|------|
| IS0 OpenRouter catalog 探针 | 仓库脚本 `image-studio/scripts/probe_capabilities.py`（无需 key） |
| IS0 直连最小出图 | **VPS 注入四把钥匙后**再打。本仓库 agent **没有**这些 key，不要往聊天贴 |
| A1 薄后端 | 已写：`app/main.py` 路由 OpenAI/Gemini/xAI/OpenRouter + 独立 volume 落盘 |
| A2 画布页 | 已写：`templates/` + `static/` |
| A3 OpenAI 笔刷蒙版 | 已写：UI 白笔 = 编辑区 → OpenAI 透明像素。非 GPT Image 2 不自动切模型 |
| UX-A | **已确认**：全英文；一个主按钮；Select area 是工具；Generate new 二次确认；**Download**（当前图 + 每版本）；Open 按钮 + 拖到画布 + 粘贴 |
| A4 多参考 / 4K 流式 | **未做**（下一波） |
| VPS 容器 + Caddy `image.` | 已上 `https://image.micropigeon.com`。前端 UX-A 需 VPS pull 重建 |
| 关 OWUI 图像模型 | **另确认**，现在不动 |

未注入钥匙前：`verify_studio.py` 必须对 generate/edit 得到 **503 missing key**，且错误里没有 key。
