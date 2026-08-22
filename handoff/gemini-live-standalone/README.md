# Gemini Live — 新项目交接包

给 **下一个 AI agent**：在本文件夹基础上 **创建全新 GitHub 仓库** 与 Web 应用。与任何现有聊天站点无关；用户会在 **同一台 VPS** 上部署本服务，但进程、端口、域名应 **独立**。

## 必读顺序

1. `NEW_AGENT_PROMPT.md` — 可整段粘贴为任务  
2. `AGENTS.md` — 施工守则  
3. `SPEC.md` — 产品契约  
4. `ARCHITECTURE.md` — 技术选型（官方 C2S）  
5. `DEPLOYMENT.md` — 同 VPS 部署约束  
6. `PLAN.md` — MVP / 阶段 2  
7. `ACCEPTANCE.md` — 验收  
8. `DONT.md` — 禁止项  
9. `DECISIONS.md` — 已定决策  
10. `SOURCES.md` — 上游链接  

本文件夹 **不是** 可运行应用。创建新仓后，建议整份复制到 `docs/`。

## 一句话

**能说、能看屏、可打断。** MVP = Google 官方 `gemini-live-ephemeral-tokens-websocket`（浏览器直连 Live API + ephemeral token + 屏享 1 fps）。
