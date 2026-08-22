# 架构

## 选定：官方 client-to-server

```
浏览器
  ├─ getUserMedia     → PCM 16 kHz
  ├─ getDisplayMedia  → JPEG 1 fps（屏享）
  └─ WSS 直连 Gemini（ephemeral token）
后端（极小）
  └─ GEMINI_API_KEY → 签发 token → /api/token
  └─ 静态前端
```

Google 文档：client-to-server 比「浏览器→你的后端→API」延迟更低。用户访问方式见 `ACCESS.md`，延迟对比见 `LATENCY.md`。

## 底本（必须改编，勿从零写协议）

- https://github.com/google-gemini/gemini-live-api-examples  
- 目录：`gemini-live-ephemeral-tokens-websocket/`  
- 关键：`ScreenCapture`、`AudioStreamer`、`mediaUtils.js`

## MVP 不选

| 选项 | 原因 |
|------|------|
| LiveKit starter | 多一跳；默认静音帧率偏低；阶段 2 |
| `gemini-live-genai-python-sdk` 前端 | 屏享 640×480 |
| `vision-demo` | outdated |
| Pipecat / FastRTC / OpenLive | 另一套媒体或 cascade |

## API 硬限制

- WSS；音频 PCM 16k 入 / 24k 出  
- 画面 JPEG **≤ 1 fps**  
- 音+视频会话有时长上限 → 生产需 session resumption（MVP 文档化，能做则做）  
- 生产用 ephemeral token  

## 建议仓库布局

```
<repo>/
  README.md
  .env.example
  server.py
  frontend/
    index.html
    geminilive.js
    mediaUtils.js   # ScreenCapture fps=1；宽度≥1280
    script.js
  docs/             # 本交接包
```

## 阶段 2 接线（勿在 MVP 实现）

- **Look**：`takeSnapshot()` + 裁块 → 非 Live 的 vision HTTP → 文本回会话  
- **换脑 A**：function calling → 服务端调 OpenRouter/OpenAI 等（本仓自己的 key）  
- **LiveKit**：仅替换媒体面
