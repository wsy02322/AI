# 已定决策（2026-08-22）

## 1. 独立产品

语音 + 持续屏享 + 打断 = **新 GitHub 仓库 + 新部署**，不嵌入任何现有聊天产品。

## 2. MVP 骨架：官方 C2S，不是 LiveKit

- 底本：`gemini-live-api-examples` → `gemini-live-ephemeral-tokens-websocket`  
- 已有 `ScreenCapture`、`getDisplayMedia`、ephemeral token  
- LiveKit 默认静音 ~0.3 fps，不调会弱于官网；留阶段 2  

## 3. 与官网的关系

- 同一 Live API：JPEG ≤ 1 fps → **不能**靠调帧率超越 Gemini  
- 超越只能来自阶段 2 工作流（look、换脑 A），不是换媒体层  

## 4. 难度对比

| 档 | 内容 | 相对难度 |
|----|------|----------|
| MVP | C2S 改编 + VPS 独立端口 | 1× |
| 阶段 2 全套 | look + 换脑 + 会话存储 | ~3× |

## 5. 部署

- 与用户其它站点 **同 VPS、不同进程/端口**  
- 具体域名由用户在新 agent 会话里提供
