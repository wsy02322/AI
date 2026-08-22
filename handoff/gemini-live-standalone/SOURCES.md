# 上游与参考

## 必须打开的上游

- https://github.com/google-gemini/gemini-live-api-examples  
  - `gemini-live-ephemeral-tokens-websocket/` ← **MVP 底本**  
  - `gemini-live-genai-python-sdk/` ← 可看转写/tool；**不要抄 640×480 屏享**  
- https://ai.google.dev/gemini-api/docs/live-api  
- https://ai.google.dev/gemini-api/docs/live-api/capabilities  

官方 C2S 要点（查阅时）：

- `ScreenCapture.start`：`getDisplayMedia`，默认 fps=1，width/height 理想 1280×720  
- `VideoStreamer`：摄像头，默认 640×480（摄像头可以；屏享不要用这套尺寸）  
- `BaseVideoCapture.takeSnapshot()`：阶段 2 look 的钩子  
- Token：后端 `GEMINI_API_KEY` → 前端短时 token → 直连 `generativelanguage.googleapis.com`

## LiveKit（阶段 2 才读）

- https://docs.livekit.io/agents/models/realtime/plugins/gemini/  
- https://github.com/livekit-examples/agent-starter-python  
- https://github.com/livekit-examples/agent-starter-react  
- https://github.com/livekit-examples/vision-demo ← **不要当起点**（WARNING: outdated）

## Hub 仓库（只读背景，禁止当 Live 实现场所）

上级目录即 Open WebUI 文档仓（`docs/SPEC.md`、`docs/open-webui-live-voice-screen-plan.md`）。

- 站点：https://micropigeon.com  
- Live L1 已落地、非顶级  
- P0-B 语音与 P0-C 屏享同级；统一顶级 = 本独立产品  

## 技能（可选）

- https://github.com/google-gemini/gemini-skills（Gemini Live API Dev skill）
