# SPEC — 独立 Live 产品（语音 + 屏享）

> 真相源。实现可换；验收以 `ACCEPTANCE.md` 为准。  
> Hub（Open WebUI）契约仍在上级仓库 `docs/SPEC.md`；**本产品不修改 Hub 实例。**

## 产品一句话

独立 Web 应用：用户对着麦克风说话，可共享屏幕，模型 **边听边看边说**，用户可以 **打断**。

## 范围

| ID | 必须（MVP） |
|----|-------------|
| LV-1 | Speech-to-Speech：模型直接听/说，不是 STT→文本→TTS 串联 |
| LV-2 | 可 barge-in：用户说话能打断模型播报 |
| LV-3 | 屏幕共享：`getDisplayMedia`；持续送帧，模型能描述/讨论当前画面 |
| LV-4 | 采样：**持续 1 fps**（说话与静音相同），不要用「静音 0.3 fps」 |
| LV-5 | 屏享分辨率：编码画布 **不要 640×480**；以官方 C2S `ScreenCapture` 的 ~1280×720 为下限，并尽量 `media_resolution` high |
| LV-6 | 密钥：浏览器只用 **ephemeral token**；长期 `GEMINI_API_KEY` 仅在后端 |
| LV-7 | 独立部署与独立 Git 仓库；不嵌入 Open WebUI |

| ID | 明确非 MVP（阶段 2，须再确认） |
|----|-------------------------------|
| LV-S2-1 | 点选区域 + 高清 look（旁路第二只 vision） |
| LV-S2-2 | 换脑 A：Live 语音仍是 Gemini，tool 调 Grok/Opus 等 |
| LV-S2-3 | 转写写回 micropigeon OWUI 聊天 |
| LV-S2-4 | LiveKit / 其他 WebRTC 媒体面 |
| LV-S2-5 | 换 S2S 供应商（Gemini↔OpenAI Realtime↔Grok Voice）— **默认不做** |

## 质量口径（写死，避免漂）

- **对标**：Gemini **网页** Live（同一 Live API）。  
- **不是**：超越 Gemini 官方 App / AI Studio 全产品（记忆、Search 生态、手机系统屏享）。  
- **屏享上限**：Live API 为 JPEG **≤ 1 fps**，不是 30fps 视频理解。调 1 fps + 更高画布是为了 **不要比官网更差**，不是超越官网。  
- Hub 上的 OWUI L1 Call（Whisper + MiniMax）**继续存在**，与本产品并行，互不冒充。

## 用户可见行为

1. 打开应用 → 授权麦克风 → 开始通话，模型用语音问候。  
2. 点「共享屏幕」→ 选窗口/标签/整屏 → 问「屏幕上有什么」→ 语音回答与画面一致。  
3. 模型说话时用户插话 → 模型停、听新内容。  
4. 用户停共享或关页 → 轨道结束，无僵尸采集。

## 非目标（MVP）

- 登录打通 Hub 账号  
- 数字人 / 头像  
- 电话 PSTN  
- 多人房间  
- 本地 Whisper/Kokoro 级隐私栈
