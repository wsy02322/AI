# Image Studio 下一波（IS-A+ 收口）

> **状态**：**待确认，未执行**。只暂存优先级判断；不改 Studio 容器、OWUI、Pipe、Caddy、picker。  
> **日期**：2026-09-05  
> **来源**：ST-14 落地后问「现在什么最值得做」。  
> **现网**：OWUI 0.11.3；聊天作图仍是路线 S；Studio 站点 `https://image.micropigeon.com`（A1–A3 已写，UX-A 前端待 VPS pull）。  
> **母 plan**：`docs/open-webui-image-studio-plan.md`（档位、禁令、IS0–A5 仍以它为准）。  
> **确认门**：未收到明确确认前，不部署、不打直连钥匙、不关 OWUI 图像模型、不改 Banner / `stack_contract`。

关联：`docs/SPEC.md` P0-A / UX-6 / ST-9；`image-studio/DEPLOY.md`；语音/屏享 `docs/open-webui-live-voice-screen-plan.md`；Notebook `docs/open-webui-notebook-youtube-plan.md`。

---

## 0. 结论

ST-14 之后，**最值得做的是收口已确认的 Image Studio IS-A+**：把「仓库能跑、站点已挂」收成日常能用的旗舰画布，而不是再开第五条主线。

P0-B 语音、P0-C 屏享、P0-D Notebook 仍并列最高优先级。它们当前分别卡在 Realtime 钥匙/中继、持续屏流、入口形态，确认成本和复杂度都高于 Studio 收口。rbb L2 只能补语音，不能冒充屏享达标。

---

## 1. 为什么是这条

官网最高档卖的不是「更能画一张」，而是独立 Images 面 + 当前画布 + 局部编辑 + 版本/参考/比例控件。现网路线 S 已有同源模型上限；缺的是产品层。

| 已有 | 还缺 |
|------|------|
| 独立站点、登录（OWUI 同一账号）、画布/版本、OpenAI 笔刷蒙版、无钥匙 503 | 四家直连真实出图/编辑验收 |
| UX-A 文案与主按钮（仓库已写） | VPS pull 后的线上 UX-A |
| OpenRouter 长尾路由（代码） | A4：多参考、4K、流式、能力表驱动控件 |
| 聊天路线 S 双轨 | 关 OWUI 图像模型（另确认，本波不绑） |

这条不改 OWUI / Pipe / 21 public，钥匙继续只进 Studio env。投入产出比高于再开 Live 或 Notebook 入口。

---

## 2. 两档（先确认再选）

### 顶级档（推荐）

分两个验收门，不要一次混成「全部做完才算开工」。

**门 1 — 能日常用**

1. VPS 确认四把直连钥匙已在 `/opt/image-studio/.env`（不入库、不进聊天、不进 Pipe / `api_configs`）。  
2. pull 当前 Studio 分支并重建容器，使线上 UX-A 与仓库一致。  
3. 浏览器走通：登录 → 生成 → 画布多轮 → 版本/下载 → OpenAI 选区编辑。  
4. 记录每家真实能力（mask / refs / stream / 4K / 失败形态），禁止未测就画假按钮。

**门 2 — 对标官网产品层（A4）**

1. Gemini：多参考、语义「只改 X」、有则开 4K。  
2. OpenAI：PNG mask 主路径 + 有则开 SSE 预览。  
3. xAI：edits / 参考；官网魔棒 API 没有就不做假按钮。  
4. OpenRouter 长尾：Seedream / Qwen / MAI 按能力表灰显。  
5. 控件由能力表驱动，不假装九个模型吃同一张 alpha mask。

**门 2 之后另确认**：是否关 OWUI 9 个纯图像模型（须先改 `stack_contract`，禁止空 `models/sync`）。本 plan 默认继续双轨。

### 略降级、简单稳定特别多

只收口门 1：线上 UX-A + 三家直连各一条真实 generate/edit + OpenRouter 一条长尾。暂缓多参考、4K、流式。

代价：选区/参考/4K 仍明显落后 ChatGPT Images / Gemini / Grok Imagine。  
收益：几天内可日常出图改图，不扩维护面。

不单提案这一档。若选它，必须是用户点头，不是执行者自行放弃 A4。

---

## 3. 本波明确不做

- 不改 OWUI 镜像 / Pipe valves / `openai.api_configs` / `WEBUI_SECRET_KEY`  
- 不把 Studio 绑进 `/custom/entrypoint.sh`  
- 不关 OWUI 图像模型（A5，另确认）  
- 不上 ComfyUI、fal / Replicate、likeness 库、视频  
- 不把 Image Studio 并进 Live / Notebook 文档  
- 不换 Realtime 镜像、不改 Notebook 入口、不装第二套 OWUI  

---

## 4. 验收（确认执行后）

门 1：`image.micropigeon.com` 用现网账号能登录；至少 OpenAI 出图 + mask 编辑、Gemini 语义编辑、xAI 或 OpenRouter 一条出图；错误不含钥匙明文；`verify_stack.py` 仍绿。

门 2：能力表与 UI 一致；无钥匙/不支持的控件灰显或隐藏；历史与独立 volume 仍和 `webui.db` 分开。

未注入钥匙的仓库探针仍须：`verify_studio.py` 对 generate/edit 得 **503 missing key**，且正文无 key。

---

## 5. 等待确认的唯一决策

> **确认 Studio 下一波**：按顶级档收口 IS-A+（先门 1 日常可用，再门 2 做 A4）。继续双轨，不关 OWUI 图像模型。不搭车 Live / Notebook。

若不确认，本文件只作为暂存；生产与 Studio 容器保持现状。
