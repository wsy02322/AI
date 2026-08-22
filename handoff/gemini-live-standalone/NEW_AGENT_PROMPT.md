# 可粘贴给新 Agent 的任务说明

```
你要创建的是一个全新的 GitHub 仓库与 Web 应用（语音 + 屏幕共享 + 可打断）。

产品目标（MVP）
- Speech-to-Speech：用户语音对话，可 barge-in（打断）
- 屏幕共享：getDisplayMedia，模型持续看到画面并围绕画面说话
- 体验对标 Gemini 官网网页 Live（同一 Live API），不声称超越 Gemini App

架构（已拍板）
- 底本：https://github.com/google-gemini/gemini-live-api-examples
  子目录 gemini-live-ephemeral-tokens-websocket
- 浏览器用 ephemeral token 直连 Gemini Live API（client-to-server WSS）
- 后端只签发短时 token；GEMINI_API_KEY 不得进前端
- 屏享：持续 1 fps（说话与静音都是 1 fps）
- 屏享编码画布不要 640×480；C2S 的 ScreenCapture 默认约 1280×720；尽量 media_resolution high
- 模型 ID 跟官方示例 README（撰写时为 gemini-3.1-flash-live-preview），不要钉死过期 ID

部署
- 用户会在同一台 VPS 上跑本服务，与机上其它站点并存
- 使用独立端口 / 独立 systemd 或容器 / 独立 Caddy 路由；见 DEPLOYMENT.md
- 不要占用或停掉机上已有 127.0.0.1:8080 等服务（除非用户明确要求）

MVP 不要做
- LiveKit / Pipecat / FastRTC / OpenLive 当第一版骨架
- clone livekit-examples/vision-demo（官方标 outdated）
- gemini-live-genai-python-sdk 那份 640×480 屏享当默认
- 点选高清、换 S2S 供应商、与其它产品账号打通（阶段 2）

阶段 2（MVP 验收后且用户确认）
- 点选 + 高清 look tool
- 换脑 A：语音仍 Gemini Live，难题经 tool 调其它文本/代码模型
- 转写导出；会话持久化在本产品内
- LiveKit：仅弱网/多人需要时

先读同目录 SPEC.md、ARCHITECTURE.md、DEPLOYMENT.md、ACCESS.md、LATENCY.md、ACCEPTANCE.md、DONT.md。
验收见 ACCEPTANCE.md；用真实 GEMINI_API_KEY 通话，不要只做到页面能打开。
```
