# Gemini Live — 新项目交接包

给 **下一个 AI agent**：在本文件夹基础上 **创建全新 GitHub 仓库** 与 Web 应用。与任何现有聊天站点无关；用户会在 **同一台 VPS** 上部署本服务，但进程、端口、域名应 **独立**。

## 必读顺序

1. `NEW_AGENT_PROMPT.md` — 可整段粘贴为任务  
2. `AGENTS.md` — 施工守则  
3. `SPEC.md` — 产品契约  
4. `ARCHITECTURE.md` — 中继到 Gemini（因中国网络）  
5. `ACCESS.md` — **手机怎么打开**（系统浏览器，勿微信内通话）  
6. `LATENCY.md` — 延迟  
7. `DEPLOYMENT.md` — 同 VPS  
8. `PLAN.md` — MVP / 阶段 2  
9. `ACCEPTANCE.md` — 验收  
10. `DONT.md` — 禁止项  
11. `DECISIONS.md` — 已定决策  
12. `SOURCES.md` — 上游链接  

本文件夹 **不是** 可运行应用。创建新仓后，建议整份复制到 `docs/`。

## 一句话

**能说、能看、可打断。** 中国手机用户：系统浏览器 + VPS 中继；看 = 摄像头主路径；整机屏享不作为网页 MVP 承诺。
