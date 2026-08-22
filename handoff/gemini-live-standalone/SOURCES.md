# 上游

## MVP 必读

- https://github.com/google-gemini/gemini-live-api-examples  
  - `gemini-live-ephemeral-tokens-websocket/` ← **底本**  
  - `gemini-live-genai-python-sdk/` ← 转写/tool 参考；**勿抄 640 屏享**  
- https://ai.google.dev/gemini-api/docs/live-api  
- https://ai.google.dev/gemini-api/docs/live-api/capabilities  

## C2S 要点

- `ScreenCapture`：`getDisplayMedia`，fps=1，理想 1280×720  
- `AudioStreamer`：16 kHz + AEC  
- `takeSnapshot()`：阶段 2 look 钩子  
- Token：后端 key → 前端短时 token → `generativelanguage.googleapis.com`

## 阶段 2 才读

- https://docs.livekit.io/agents/models/realtime/plugins/gemini/  
- https://github.com/livekit-examples/agent-starter-python  

## 可选

- https://github.com/google-gemini/gemini-skills（Live API Dev skill）
