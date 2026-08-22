# SPEC — 语音 + 屏享 Live

> 真相源。验收以 `ACCEPTANCE.md` 为准。

## 产品一句话

Web 应用：麦克风说话 + 可选屏幕共享，模型 **边听边看边说**，用户可 **打断**。

## MVP 必须

| ID | 要求 |
|----|------|
| LV-1 | Speech-to-Speech，非 STT→文本→TTS 串联 |
| LV-2 | barge-in |
| LV-3 | `getDisplayMedia` 屏享；模型能讨论当前画面 |
| LV-4 | 持续 **1 fps**（静音不降频到 ~0.3 fps） |
| LV-5 | 屏享画布 **≥ 1280 宽**（勿 640×480）；尽量 `media_resolution` high |
| LV-6 | 长期 key 仅 VPS；浏览器只连本站 WSS（中国用户不直连 Google） |
| LV-7 | 独立 Git 仓库；独立 VPS 进程/端口 |

## 非 MVP（阶段 2，须再确认）

| ID | 内容 |
|----|------|
| LV-S2-1 | 点选区域 + 高清 look |
| LV-S2-2 | 换脑 A：Gemini 语音 + tool 调其它模型 |
| LV-S2-3 | 本产品内会话历史 / 导出（Markdown 等） |
| LV-S2-4 | LiveKit 等媒体加固 |
| LV-S2-5 | 通话中途换 S2S 供应商 — **默认不做** |

## 质量口径

- 对标：Gemini **网页** Live（同一 API）。  
- 屏享上限：JPEG **≤ 1 fps**，不是 30fps 视频流。  
- 1 fps + 高分辨率是为了 **不弱于官网**，不是超越官网。

## 用户流程

1. 打开页 → 授权麦克风 → 语音问候。  
2. 共享屏幕 → 问画面内容 → 语音回答一致。  
3. 插话 → 模型让路。  
4. 停共享 / 关页 → 采集结束。

## MVP 非目标

- 与其它站点账号打通  
- 数字人  
- PSTN 电话  
- 多人房间  
- 全本地 Whisper/TTS 栈  
- 手机 App / 商店分发
