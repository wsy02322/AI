# 可粘贴给新 Agent 的任务说明

```
全新 GitHub 仓库 + 桌面 Web 应用：语音对话、屏幕共享、可打断。

用户：约 5 人，多数在中国。访问方式是电脑 Chrome/Edge 打开 HTTPS 网址。不要做手机 App。

架构（已拍板，因中国网络）
- 浏览器不要直连 Google。音视频经 VPS 中继：浏览器 WSS → 你的服务 → Gemini Live。
- 底本拆开用：
  - 屏享/麦采集：gemini-live-api-examples 里 ephemeral-tokens 的 mediaUtils.js（ScreenCapture，1 fps，画布≥1280，禁止 640×480）
  - 服务端转 Google：gemini-live-genai-python-sdk 的 Live 会话写法（不要抄它前端 640 屏享）
- GEMINI_API_KEY 只在 VPS。同机独立端口（如 127.0.0.1:8090）+ Caddy HTTPS，/ws 必须支持 WebSocket。
- 模型 ID 跟官方示例当前 README，不要钉死过期 ID。
- 体验对标网页 Gemini Live；不声称超越官方 App。中国用户首响会比能直连 Google 时多约 0.2–0.6s，仍须可打断、非数秒串联。

MVP 不要做
- 浏览器 ephemeral token 直连 Google 当默认（大陆常失败）
- LiveKit / 原生 App / vision-demo
- 点选高清、换 S2S 供应商

先读 ACCESS.md、LATENCY.md、ARCHITECTURE.md、DEPLOYMENT.md、ACCEPTANCE.md。
用真实 key 在「模拟中国访问」（至少：浏览器不得直连 googleapis）下测通通话与屏享。
```
