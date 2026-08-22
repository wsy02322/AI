# 上游

## MVP 必读

- https://github.com/google-gemini/gemini-live-api-examples  
  - `gemini-live-ephemeral-tokens-websocket/` ← **借采集**：`AudioStreamer`、`VideoStreamer`（摄像头）、可选 `ScreenCapture`  
  - `gemini-live-genai-python-sdk/` ← **借服务端** Live 中继；**勿抄前端 640 屏享**  
- https://ai.google.dev/gemini-api/docs/live-api  
- https://ai.google.dev/gemini-api/docs/live-api/capabilities  

## 连接方式

- **默认：** 浏览器 WSS → 本站 → Google（中国用户）  
- **不要默认：** 浏览器 ephemeral token 直连 `generativelanguage.googleapis.com`

## 阶段 2

- https://docs.livekit.io/agents/models/realtime/plugins/gemini/  

## 可选

- https://github.com/google-gemini/gemini-skills
