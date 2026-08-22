# 已定决策（2026-08-22）

## 1. 独立 Web 产品

新 GitHub 仓库 + 同 VPS 独立端口。约 5 名用户，多数在中国。

## 2. 访问 = 桌面浏览器，不是 App

屏享依赖 `getDisplayMedia`。手机网页屏享差；原生 App 不缩短中国到欧盟 VPS 的 RTT，MVP 不做。

## 3. 默认中继，不默认 C2S

浏览器直连 Google（官方 ephemeral C2S）延迟更好，但大陆常不可达。  
默认：**浏览器 → VPS → Gemini**。VPS 出站访问 Google。

采集代码用 C2S 示例的 `ScreenCapture`（1 fps、≥1280）；服务端用 Python SDK 的 Live 连接。禁止抄 SDK 示例 640×480。

## 4. 延迟预期

中国用户首响大约比「能直连 Google 的网页 Live」再慢 **0.2–0.6s 量级**。仍须打断可用。不要用 App/LiveKit 幻想打赢物理 RTT。

## 5. 阶段 2

Look、换脑 A、会话导出。可选 C2S 仅当全员能访问 Google。
