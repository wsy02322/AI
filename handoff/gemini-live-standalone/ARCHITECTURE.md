# 架构

## 选定：手机网页 → VPS → Gemini

中国 + 手机：浏览器 **不要** 直连 Google。

```
手机 Safari / Chrome
  ├─ 麦克风 PCM
  ├─ 摄像头（MVP「能看」主路径）
  ├─ getDisplayMedia 屏享（仅作增强，Android 优先）
  └─ 同站 WSS ──► VPS ──► Gemini Live
```

UI **手机优先**（大按钮、竖屏、耳机提示、微信内打开时全屏引导去系统浏览器）。

## 底本

| 用 | 来源 | 注意 |
|----|------|------|
| 麦 + 摄像头 + 可选 ScreenCapture | 官方 `mediaUtils.js`（`VideoStreamer` / `ScreenCapture`） | 摄像头不要锁死桌面 1280；竖屏按短边缩放，长边不要糊成 640 |
| 服务端 Live 中继 | `gemini-live-genai-python-sdk` | 勿抄其 640 屏享默认 |
| 前端连本站 `/ws` | 改编官方 JS | 禁止连 googleapis |

## 原生 App 何时才上（阶段 1.5，须确认）

仅当验收证明：**系统浏览器里语音+摄像头可用，但「共享微信/别的 App 画面」是刚需且网页做不到。**

建议形态：同一套 VPS 中继，薄壳（Capacitor 或原生）只补 **系统录屏 + 后台音频**。不要为延迟重写协议。不要先上架商店：5 人可用 TestFlight / 侧载 / 内部分发。

## 不做默认

| 选项 | 原因 |
|------|------|
| 桌面 Chrome 专用 UI | 用户几乎不用电脑 |
| 微信小程序当 MVP | 采集/Live 协议限制大，且仍要中继 |
| C2S 直连 Google | 大陆常失败 |
| LiveKit | 不解决微信/录屏，还多一跳 |
| 一上来双端商店 App | 5 人过重 |

## API 硬限制

JPEG ≤ 1 fps；PCM 16k/24k；长会话要 resumption。
