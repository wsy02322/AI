# 可粘贴给新 Agent 的任务说明

把下面代码块整段交给负责「创建新项目」的 agent。它还应能读到本文件夹其余文件。

```
你要创建的是一个全新的独立 Git 仓库与 Web 应用，不是 Open WebUI 插件，也不是改 https://micropigeon.com。

产品目标（MVP）
- 用户能语音对话（Speech-to-Speech，可 barge-in / 打断）
- 用户能屏幕共享，模型持续看到画面并围绕画面说话
- 体验尽量接近 Gemini 官网 Live（同一套 Live API），不声称超越 Gemini App

必须采用的架构（已拍板）
- 以 Google 官方示例为底：
  https://github.com/google-gemini/gemini-live-api-examples
  子目录 gemini-live-ephemeral-tokens-websocket
- 浏览器用 ephemeral token 直连 Gemini Live API（client-to-server WSS）
- 后端只签发短时 token，禁止把 GEMINI_API_KEY 下发到浏览器
- 屏享用 getDisplayMedia；采样持续 1 fps（说话与静音都是 1 fps）
- 屏享画布不要缩到 640×480（那是另一份 Python SDK 示例的错误默认）。C2S 示例 ScreenCapture 默认约 1280×720；可再开 media_resolution high
- 默认模型跟官方示例当前值（撰写时为 gemini-3.1-flash-live-preview），以该仓库 README 为准，不要钉死过期的 2.0/2.5 ID

明确不要做（MVP）
- 不要用 LiveKit / Pipecat / FastRTC / OpenLive 当第一版骨架
- 不要 clone livekit-examples/vision-demo（官方已标 outdated）
- 不要改 micropigeon 的 Open WebUI、Pipe、Call overlay、镜像
- 不要做点选高清、通话中换 S2S 供应商、写回 OWUI 聊天（那是阶段 2）
- 不要把本产品塞进现有 wsy02322/AI 仓库当 OWUI 功能

阶段 2（仅当 MVP 验收通过且用户确认后再做）
- 点选区域 + 高清 look tool（旁路第二只 vision；Live API 仍是 JPEG≤1fps）
- 换脑 A：语音始终 Gemini Live，难题/代码经 tool 调 Grok 等
- 转写写回 Hub（micropigeon OWUI）；先解决身份映射
- LiveKit Cloud：仅当需要弱网 WebRTC / 多人 / 电话接入时再上

验收见同目录 ACCEPTANCE.md。宪法：先 plan、用户确认后再动现网；本产品在新仓内实现，不碰 Hub 实例。

先读同目录 SPEC.md、ARCHITECTURE.md、PLAN.md、DONT.md、DECISIONS.md、SOURCES.md。
```
