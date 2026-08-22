# 架构（已拍板）

## 选定：官方 client-to-server

```
浏览器
  ├─ getUserMedia  → PCM 16 kHz 音频
  ├─ getDisplayMedia → 每秒 1 张 JPEG（屏享）
  └─ WebSocket 直连 generativelanguage.googleapis.com（ephemeral token）
后端（极小）
  └─ GEMINI_API_KEY → 签发短时 token → GET/POST /api/token
```

这是 Google 文档写的 **更低延迟** 路径（媒体不经你的业务后端）。

**实现底本（必须 fork/改编，不要从零发明协议）：**

- 仓库：https://github.com/google-gemini/gemini-live-api-examples  
- 目录：`gemini-live-ephemeral-tokens-websocket/`  
- 关键类：`ScreenCapture`、`AudioStreamer`、`VideoStreamer`、`AudioPlayer`（见该仓 `frontend/mediaUtils.js`）

默认模型：以该示例 README 为准（交接时为 `gemini-3.1-flash-live-preview`）。

## 明确不选为 MVP 骨架

| 选项 | 原因 |
|------|------|
| LiveKit Cloud + agent-starter | 多一跳 SFU；默认静音 ~0.3 fps 比官网差；多一套账号。**阶段 2 弱网/多人才考虑** |
| `gemini-live-genai-python-sdk` 那份前端 | 有屏享，但 `captureFrame` **写死 640×480**，屏享会糊 |
| `livekit-examples/vision-demo` | 官方标 outdated，`MultimodalAgent` 旧 API |
| 塞进 Open WebUI Call | Hub 的 Call 是 STT→TTS；Pipe 无法 `output_audio`（GA-A 已证）；rbb Realtime overlay 无持续 `getDisplayMedia` |
| Pipecat / FastRTC / OpenLive | 另一媒体平面或桌面 cascade，不是 Gemini 官网同款 S2S |

## 官方 API 硬限制（不要试图「调帧率超越」）

- 协议：有状态 WSS  
- 音频入：PCM 16-bit LE 16 kHz；出：PCM 24 kHz  
- 画面：JPEG，**≤ 1 fps**  
- 音+视频会话有时长上限（无压缩时很短）→ 生产必须做 **session resumption**（MVP 至少要文档化；能做则做）  
- Google 生产建议 ephemeral token，不要把长期 key 放进前端  

## 建议新仓布局

```
<new-repo>/
  README.md
  .env.example          # GEMINI_API_KEY=
  server.py             # 仅 token + 静态文件（改编官方 server.py）
  frontend/
    index.html
    geminilive.js
    mediaUtils.js       # 保留 ScreenCapture；fps=1；屏享宽度≥1280
    script.js
    tools.js            # MVP 可留空或极简；不要玩具 CSS injection 当卖点
  docs/                 # 可复制本交接包
```

## 阶段 2 怎么接（先不要实现）

- **Look / 点选**：浏览器已有 canvas 与 `takeSnapshot()`。高清 = 从原始 display track 裁块 → **非 Live** 的 vision HTTP → 把文本塞回 Live 会话。Live 通道仍 ≤1 fps JPEG。  
- **换脑 A**：Live function calling → 服务端调 Grok（OpenRouter，与 Hub 同类，但是 **新仓自己的 key/配置**，禁止去翻 Hub 容器偷 Pipe key）。  
- **写回 Hub**：用 Live 转写 HTTP POST 到 OWUI `/api/v1/chats`；必须单独设计用户身份（OWUI JWT 容器重建会变）。  
- **LiveKit**：仅替换媒体面，Live API 仍是 Gemini；不要和 C2S MVP 同时开工。
