# 可粘贴给新 Agent 的任务说明

```
全新 GitHub 仓库。用户约 5 人，多数在中国，几乎都用手机。

产品：能说、能看、可打断。看 = 手机摄像头为 MVP 主路径；共享「其它 App 的屏幕」在网页上不可靠，不要假装桌面 getDisplayMedia 已经在 iPhone/微信里能用。

访问
- HTTPS 手机网页，PWA 可加到主屏。
- 必须检测微信 WebView，提示「在 Safari / Chrome 中打开」。微信内不作为可验收环境。
- 建议耳机。不要做电话、不要先做商店 App。

架构
- 手机浏览器 WSS → VPS → Gemini Live。不要浏览器直连 Google。
- 采集改编官方 mediaUtils（摄像头 + 麦；屏享仅 Android Chrome 增强）。
- 服务端用官方 Python Live 中继。Key 只在 VPS。独立端口 + Caddy，/ws 要通。
- UI 手机优先。

验收
- 真机：iPhone Safari 与 Android Chrome 各至少一次语音+摄像头。
- 微信内打开：只要求出现「去系统浏览器」引导，不要求通话成功。
- 共享整机屏幕：能则记；不能则文档化为阶段 1.5 原生壳，不要卡死 MVP。

不要：C2S 默认、LiveKit、vision-demo、桌面-only、为「加速」做 App。
先读 ACCESS.md、LATENCY.md、ARCHITECTURE.md、ACCEPTANCE.md。
```
