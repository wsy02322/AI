# 架构

## 选定：浏览器 → 你的 VPS → Gemini（server 中继）

**原因：多数用户在中国，浏览器直连 Google Live 经常不可达。**  
延迟会比「能直连 Google 的 C2S」略差，但 **能用** 优先于「理论更低延迟却连不上」。

```
浏览器（桌面 Chrome）
  ├─ getUserMedia      PCM 16 kHz
  ├─ getDisplayMedia   JPEG 1 fps
  └─ WSS（同站 HTTPS）──► VPS Python
                              └─ WSS──► Gemini Live
```

`GEMINI_API_KEY` 只在 VPS。

## 底本

两份官方示例 **拆着用**，不要整份照抄错误默认：

| 用 | 来源 | 注意 |
|----|------|------|
| 浏览器采集：麦 + **ScreenCapture 屏享** | `gemini-live-ephemeral-tokens-websocket` 的 `mediaUtils.js` | 屏享 **≥1280 宽、1 fps** |
| 服务端 `genai` Live 会话、把音视频转给 Google | `gemini-live-genai-python-sdk` | **不要**抄它前端 `captureFrame` 的 **640×480** |
| 前端连 **自己的** `/ws`，不要连 `generativelanguage.googleapis.com` | 改编 C2S 的 `geminilive.js` | 去掉 ephemeral token 直连 |

## 明确不选为默认

| 选项 | 原因 |
|------|------|
| 官方 C2S（浏览器直连 Google + ephemeral token） | 大陆用户经常失败；仅当用户明确全员能访问 Google 再考虑 |
| LiveKit Cloud | 用户仍要连海外；多一跳；5 人过重 |
| 原生 App | 不降低中德 RTT；屏享/上架成本高 |
| `vision-demo` | outdated |

## API 硬限制（与中继无关）

- 画面 JPEG **≤ 1 fps**  
- 音频 PCM 16k 入 / 24k 出  
- 音+视频会话有时长上限 → session resumption（MVP 文档化，能做则做）  

## 建议仓库布局

```
<repo>/
  README.md
  .env.example          # GEMINI_API_KEY=  HOST=127.0.0.1  PORT=8090
  server.py             # 静态文件 + /ws 中继到 Gemini
  frontend/
    index.html          # 桌面 Web 通话 UI
    mediaUtils.js       # ScreenCapture fps=1；宽度≥1280
    ...
  docs/
```

## 阶段 2（勿在 MVP 做）

- Look / 点选  
- 换脑 A（function calling）  
- 会话导出  
- 仅当 **全员能访问 Google** 时，可加可选 C2S 模式降延迟——默认仍中继
