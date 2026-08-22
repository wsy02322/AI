# Gemini Live — 新项目交接包

给 **下一个 AI agent**：在本文件夹基础上 **创建全新 GitHub 仓库** 与 Web 应用。与任何现有聊天站点无关；用户会在 **同一台 VPS** 上部署本服务，但进程、端口、域名应 **独立**。

## 必读顺序

1. `NEW_AGENT_PROMPT.md` — 可整段粘贴为任务  
2. `AGENTS.md` — 施工守则  
3. `SPEC.md` — 产品契约  
4. `ARCHITECTURE.md` — 中继到 Gemini（因中国网络）  
5. `ACCESS.md` — 怎么打开（桌面 Web）  
6. `LATENCY.md` — 延迟  
7. `DEPLOYMENT.md` — 同 VPS  
8. `PLAN.md` — MVP / 阶段 2  
9. `ACCEPTANCE.md` — 验收  
10. `DONT.md` — 禁止项  
11. `DECISIONS.md` — 已定决策  
12. `SOURCES.md` — 上游链接  

本文件夹 **不是** 可运行应用。创建新仓后，建议整份复制到 `docs/`。

## 一句话

**能说、能看屏、可打断。** 桌面 Web；中国用户经 VPS 中继到 Gemini Live；屏享 1 fps（采集代码来自官方 C2S 示例，连接不要直连 Google）。
