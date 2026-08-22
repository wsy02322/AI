# 不要做

## 产品 / 架构

- 不要在 Open WebUI 里做本产品（Call overlay、改镜像、改 Pipe valves）  
- 不要启用 Hub 的 `openai.api_configs`  
- 不要空 `POST /api/v1/models/sync`（那是 Hub 事故；新仓也不要去调 Hub 写 API）  
- 不要 clone `livekit-examples/vision-demo` 当起点  
- 不要用 `gemini-live-genai-python-sdk` 的 640×480 屏享当默认  
- 不要默认静音 0.3 fps（LiveKit 默认；比官网差）  
- 不要 MVP 就上 LiveKit / Pipecat / Daily / FastRTC / Anam / OpenLive  
- 不要把 gpt-audio / OpenRouter `/chat/completions` 当 S2S（Hub 上 GA-A：Pipe `/responses` 拒 `modalities.audio`）  
- 不要通话中途换 S2S 供应商（换脑 B）  
- 不要数字人、不要与 Hub 四格聊天混成一个 SPA  

## 安全

- 不要把 `GEMINI_API_KEY` 提交到 git 或下发浏览器  
- 不要在交接包或新仓 README 写入真实密钥  
- 不要为了 Live 去 SSH/翻 Hub VPS 上的 Pipe key  

## 口径

- 不要把 L1 OWUI Call 写成已达顶级 Live  
- 不要把 1 fps JPEG 写成「视频流理解已超越官网」
