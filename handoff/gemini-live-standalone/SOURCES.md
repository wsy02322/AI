# 上游

## MVP 必读

- https://github.com/google-gemini/gemini-live-api-examples  
  - `gemini-live-ephemeral-tokens-websocket/` ← **只借采集**：`ScreenCapture`、`AudioStreamer`（1 fps，≥1280）  
  - `gemini-live-genai-python-sdk/` ← **只借服务端** Live 会话；**勿抄前端 640×480**  
- https://ai.google.dev/gemini-api/docs/live-api  
- https://ai.google.dev/gemini-api/docs/live-api/capabilities  

## 连接方式

- **默认：** 浏览器 WSS → 本站 → Google（中国用户）  
- **不要默认：** 浏览器 ephemeral token 直连 `generativelanguage.googleapis.com`

## 阶段 2

- https://docs.livekit.io/agents/models/realtime/plugins/gemini/  

## 可选

- https://github.com/google-gemini/gemini-skills
