# Gemini Live 独立产品 — 交接包

本文件夹是给 **下一个 AI agent** 的完整 brief。新 agent **参考这里去创建全新 Git 仓库与产品**，**不要**在 Open WebUI / micropigeon 现网里实现 Live。

现网站点：`https://micropigeon.com`（OWUI 0.11 Hub：聊天 / 图像 / Sonar / 对比）。语音+持续屏享的顶级路径已决定 **独立出去**。

## 新 agent 必读顺序

1. `NEW_AGENT_PROMPT.md` — 可整段当作系统任务  
2. `AGENTS.md` — 怎么干活、先确认什么  
3. `SPEC.md` — 产品契约与验收面  
4. `ARCHITECTURE.md` — 用哪条链路（官方 C2S，不是先 LiveKit）  
5. `PLAN.md` — MVP vs 超越阶段  
6. `ACCEPTANCE.md` — 怎样算做成  
7. `DONT.md` — 禁止项  
8. `DECISIONS.md` — 为什么这样选  
9. `SOURCES.md` — 上游链接与上游文件  

读完再创建新仓库。本交接包 **不是** 可运行的应用。

## 一句话任务

独立产品：能说、能看屏、可打断。MVP = Google 官方 **client-to-server** Live 示例 + 屏享 1 fps。不改 Open WebUI。LiveKit / 点选高清 / 换脑 / 写回 Hub 都是后续阶段。
