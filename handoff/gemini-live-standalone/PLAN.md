# 阶段计划

## 阶段 0 — 建仓

- 用户新建 GitHub 仓库  
- 用户新建 GitHub 仓库  
- 服务端中继 + 官方 ScreenCapture 采集（见 `ARCHITECTURE.md`）  
- `.env.example`、README、gitignore  
- 复制本交接包到 `docs/`

## 阶段 1 — MVP

1. 桌面 Web；浏览器 WSS 到本站，由 VPS 中继到 Gemini（不直连 Google）  
2. 麦克风 S2S + 打断  
3. `ScreenCapture`，fps=1，画布 ≥ 1280（禁止 640×480）  
4. Caddy HTTPS + WebSocket；独立端口  
5. `ACCEPTANCE.md` 全过（含：通话流量不打到 googleapis 的浏览器直连）  

**完成定义：** 真实 key + 中国可达的域名上能说话、能看屏。

## 阶段 2 — 须用户再确认

1. Look（先整帧高清，再点选）  
2. 换脑 A（tool 调其它模型）  
3. 本产品内会话导出/历史  
4. LiveKit（弱网/多人）  

阶段 1 与 2 不要同一 PR。
