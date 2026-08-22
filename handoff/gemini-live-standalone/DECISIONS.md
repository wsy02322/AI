# 已做决定（给新 agent，避免重开讨论）

记录于 2026-08-22，Hub 仓库讨论与官方示例复查之后。

## 1. 为什么不在 Open WebUI 里做

- Hub Call = Whisper → 文本模型 → MiniMax TTS，无真正 S2S。  
- GA-A：经 Pipe 的 gpt-audio **无** `output_audio`（Responses API 拒 `modalities.audio`）。  
- rbb `open-webui-realtime` overlay **无**持续 `getDisplayMedia`，只补语音。  
- 宪法：少分叉；顶级 Voice+屏享 = 第二产品（原 plan L3a）。

Hub 维持 L1 过渡。本产品独立。

## 2. 为什么 MVP 不是 LiveKit Cloud

曾建议 LiveKit starter + Gemini plugin，因为屏享是 video track、工程成熟。

查阅 https://github.com/google-gemini/gemini-live-api-examples 后修正：

- Google **C2S + ephemeral token** 才是官方低延迟路径。  
- 该仓已有 `ScreenCapture` + 1 fps，不必靠 LiveKit 才有共享按钮。  
- LiveKit 默认静音 ~0.3 fps，不调就会比官网差。  
- 多一套 LiveKit 账号，违反「简单」。  

LiveKit = 阶段 2 媒体加固，不是第一版骨架。

## 3. 为什么打不赢 / 如何「超越」

同一 Live API：JPEG ≤ 1 fps。官网客户端 + 生态 + 手机仍更强。

可超越的是官网 **没有** 的工作流（阶段 2）：点选高清 look、换脑 A、写回 Hub。那不是把 fps 调到 5。

## 4. 两种实现难度（仍成立）

| 档 | 骨架 | 相对难度 |
|----|------|----------|
| MVP | 官方 C2S 改编 | 1×（现成屏享+token） |
| 超越三项一起 | 自研 HUD + 第二模型 + OWUI 身份 | ~3×；不要与 MVP 同单 |

点选高清在 C2S 上略易（canvas 已在浏览器）。换 S2S 供应商仍然禁止。

## 5. Hub 侧不要动的事实

- 默认模型：仅 Grok 4.6；picker 仅 19 public  
- `WEBUI_SECRET_KEY=""`；用户重登可接受  
- Pipe `open_webui_openrouter_integration`；`openai.api_configs` 全 `enable: false`
