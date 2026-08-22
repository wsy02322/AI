# 不要做

## MVP

- LiveKit / Pipecat / FastRTC / OpenLive 当第一版  
- `livekit-examples/vision-demo`  
- `gemini-live-genai-python-sdk` 的 640×480 屏享默认  
- 静音 0.3 fps 采样  
- 通话中途换 S2S 供应商  
- 数字人 / PSTN / 多人房间  

## 安全

- `GEMINI_API_KEY` 进 git 或前端  
- token 后端无 TLS 直接暴露公网  

## 部署

- 未经用户同意占用 `8080` 或停掉机上其它服务  
- 改其它项目的 env / 数据库 / 容器  

## 口径

- 不要把 1 fps JPEG 说成「30fps 视频理解」  
- 不要把 MVP 说成已超越 Gemini 官方 App
