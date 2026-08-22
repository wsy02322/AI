# Gemini Live Standalone — 完整交接包（单文件整合版）

> **来源：** `https://github.com/wsy02322/AI/tree/main/handoff/gemini-live-standalone`  
> **生成时间：** 2026-08-22  
> **用途：** 下载后上传到新仓库 `AI.LIVE`，拆成 `handoff/gemini-live-standalone/` 下 13 个文件。

## 上传到新仓库建议结构

```
AI.LIVE/
├── handoff/
│   └── gemini-live-standalone/
│       ├── README.md
│       ├── NEW_AGENT_PROMPT.md
│       ├── AGENTS.md
│       ├── SPEC.md
│       ├── ARCHITECTURE.md
│       ├── ACCESS.md
│       ├── LATENCY.md
│       ├── DEPLOYMENT.md
│       ├── PLAN.md
│       ├── ACCEPTANCE.md
│       ├── DONT.md
│       ├── DECISIONS.md
│       └── SOURCES.md
```

每个文件在下方以 `===== FILE: ... =====` 分隔。复制对应段落到同名文件即可。

---

===== FILE: handoff/gemini-live-standalone/README.md =====

# Gemini Live — 新项目交接包

给 **下一个 AI agent**：在本文件夹基础上 **创建全新 GitHub 仓库** 与 Web 应用。与任何现有聊天站点无关；用户会在 **同一台 VPS** 上部署本服务，但进程、端口、域名应 **独立**。

## 必读顺序

1. `NEW_AGENT_PROMPT.md` — 可整段粘贴为任务  
2. `AGENTS.md` — 施工守则  
3. `SPEC.md` — 产品契约  
4. `ARCHITECTURE.md` — 中继到 Gemini（因中国网络）  
5. `ACCESS.md` — **手机怎么打开**（系统浏览器，勿微信内通话）  
6. `LATENCY.md` — 延迟  
7. `DEPLOYMENT.md` — 同 VPS  
8. `PLAN.md` — MVP / 阶段 2  
9. `ACCEPTANCE.md` — 验收  
10. `DONT.md` — 禁止项  
11. `DECISIONS.md` — 已定决策  
12. `SOURCES.md` — 上游链接  

本文件夹 **不是** 可运行应用。创建新仓后，建议整份复制到 `docs/`。

## 一句话

**能说、能看、可打断。** 中国手机用户：系统浏览器 + VPS 中继；看 = 摄像头主路径；整机屏享不作为网页 MVP 承诺。

---

===== FILE: handoff/gemini-live-standalone/NEW_AGENT_PROMPT.md =====

# 可粘贴给新 Agent 的任务说明

```
全新 GitHub 仓库。用户约 5 人，多数在中国，几乎都用手机。

产品：能说、能看、可打断。看 = 手机摄像头为 MVP 主路径；共享「其它 App 的屏幕」在网页上不可靠，不要假装桌面 getDisplayMedia 已经在 iPhone/微信里能用。

访问
- HTTPS 手机网页，PWA 可加到主屏。
- 必须检测微信 WebView，提示「在 Safari / Chrome 中打开」。微信内不作为可验收环境。
- 建议耳机。不要做电话、不要先做商店 App。

架构
- 手机浏览器 WSS → VPS → Gemini Live。不要浏览器直连 Google。
- 采集改编官方 mediaUtils（摄像头 + 麦；屏享仅 Android Chrome 增强）。
- 服务端用官方 Python Live 中继。Key 只在 VPS。独立端口 + Caddy，/ws 要通。
- UI 手机优先。

验收
- 真机：iPhone Safari 与 Android Chrome 各至少一次语音+摄像头。
- 微信内打开：只要求出现「去系统浏览器」引导，不要求通话成功。
- 共享整机屏幕：能则记；不能则文档化为阶段 1.5 原生壳，不要卡死 MVP。

不要：C2S 默认、LiveKit、vision-demo、桌面-only、为「加速」做 App。
先读 ACCESS.md、LATENCY.md、ARCHITECTURE.md、ACCEPTANCE.md。
```

---

===== FILE: handoff/gemini-live-standalone/AGENTS.md =====

# 新项目 Agent 守则

1. 手机优先、中国网络优先：中继到 Gemini。  
2. 微信不是运行环境，是「请到系统浏览器」的入口。  
3. 摄像头 = 网页能交付的「看」；整机录屏 = 可能要原生壳。  
4. 不要做 App 来优化延迟。

向用户要：`GEMINI_API_KEY`、HTTPS 域名、端口；以及 **几人 iPhone、几人 Android**（若未知，两台都测）。

---

===== FILE: handoff/gemini-live-standalone/SPEC.md =====

# SPEC — 语音 + 看画面 Live（手机）

> 验收以 `ACCEPTANCE.md` 为准。

## 产品一句话

手机打开的网页：对着麦克风说话，模型能 **看到摄像头（或尽力看到屏幕）** 并语音回答，用户可打断。

## MVP 必须

| ID | 要求 |
|----|------|
| LV-1 | S2S，非 STT→TTS 串联 |
| LV-2 | barge-in（耳机场景优先） |
| LV-3a | **摄像头** 帧进 Live（手机「能看」主路径） |
| LV-3b | 系统浏览器内尝试屏享；**失败不得假装已达标** |
| LV-4 | 视觉 **1 fps** |
| LV-5 | 编码勿无故压成 640 糊图；竖屏按短边适配 |
| LV-6 | Key 仅 VPS；浏览器只连本站 WSS |
| LV-7 | 独立仓 + 独立端口 |
| LV-8 | **微信内打开** 必须提示去 Safari/Chrome；微信 WebView **不是** 验收环境 |
| LV-9 | UI 手机优先 |

## 非 MVP

| ID | 内容 |
|----|------|
| LV-S2-0 | 原生壳：稳定共享其它 App 画面 + 后台通话（须再确认） |
| LV-S2-1 | 点选高清 look |
| LV-S2-2 | 换脑 A |
| LV-S2-3 | 会话导出 |
| LV-S2-4 | LiveKit |
| LV-S2-5 | 换 S2S 供应商 — 默认不做 |

## 质量口径

- 语音对标网页/App Gemini Live 的「能聊」；手机外放会差一截，写进说明用耳机。  
- 画面仍是 JPEG ≤ 1 fps。  
- **不要**把「手机网页共享整机屏幕」写成已对齐官方 Gemini App。

## 用户流程

1. 系统浏览器打开 HTTPS → 若在微信则先引导离开。  
2. 允许麦克风；需要看时开摄像头。  
3. 说话 / 打断。  
4. 停采集、关页即释放。

## 非目标（MVP）

- 商店上架、微信小程序、电话、多人房、桌面专用布局

---

===== FILE: handoff/gemini-live-standalone/ARCHITECTURE.md =====

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

---

===== FILE: handoff/gemini-live-standalone/ACCESS.md =====

# 用户怎么访问

## 结论（约 5 人、多数在中国、**几乎都用手机**）

- **打开方式：手机系统浏览器访问 HTTPS 网址**（Safari 或 Chrome），**不要用微信内置浏览器**。  
- **形态：先做手机网页（PWA 可加到主屏）**；不是桌面站、不是电话。  
- **通话仍经 VPS 中继到 Google**（大陆浏览器直连 Google 常失败）。  
- **「看」分两档：** 摄像头 = MVP 必做且手机最自然；**共享手机屏幕（其它 App）在网页上不可靠**，微信里基本不行。若必须稳定共享「正在用的 App」，才上原生壳。

## 用户实际会怎么点进来

中国手机用户默认在 **微信里点链接**。微信 WebView：麦克风/摄像头/屏享权限经常残缺或被拒。

页面顶部必须写死操作：

> 请点右上角 `···` → **在 Safari 中打开**（iPhone）或 **在浏览器中打开**（Android Chrome）。  
> 建议戴耳机，避免外放回声。

没有这一步，5 人会表现为「打不开麦 / 黑屏 / 一说话就断」。

## 三种「看」，难度完全不同

| 能力 | 手机网页（Safari/Chrome） | 微信内 | 轻量原生 App |
|------|--------------------------|--------|----------------|
| 语音听/说 | **可做 MVP** | 经常失败 | 更好（后台、AEC） |
| **摄像头**（把镜头对准屏幕/实物） | **可做 MVP** | 经常失败 | 更好 |
| **共享本机屏幕**（其它 App 画面） | Android Chrome 有时可以；**iOS Safari 很别扭或不稳** | **基本不行** | **这才是正路**（系统录屏） |

原「桌面共享窗口」不能原样搬到手机网页。手机上 Gemini 官网 App 能看屏，靠的是 **原生录屏**，不是一个网址。

## 访问步骤（给最终用户）

1. 拿到 `https://live.你的域名/`  
2. **系统浏览器**打开（离开微信）  
3. 允许麦克风；需要「看」时允许摄像头，或（仅 Android Chrome 试验）共享屏幕  
4. 戴耳机后开始说话；可打断  

须 **HTTPS**。不要 iframe。不要做电话拨入。

## 数据怎么走

```
手机浏览器（中国，Safari/Chrome）
  --HTTPS/WSS-->  VPS
                    --WSS-->  Gemini Live
```

页面、麦克风、摄像头/屏帧都先到 VPS。Key 只留 VPS。

---

===== FILE: handoff/gemini-live-standalone/LATENCY.md =====

# 延迟（手机 + 中国）

首响 = 说完到模型出声。屏/摄像头是 1 fps JPEG。数字是量级。

## 默认链路

```
手机 4G/5G ──WSS──► 欧盟 VPS ──WSS──► Google
```

比「能直连 Google 的网页 Live」大约再慢 **0.3–0.8s**（国际 RTT + 蜂窝抖动 + 外放缓冲）。仍须能打断；变成数秒级转写播报则失败。

| 因素 | 影响 |
|------|------|
| 中国 → 欧盟 VPS | 主要增加的一截 |
| 4G/5G vs 宽带 | 抖动更大，偶发卡顿 |
| 外放喇叭 | 回声、打断变差 → **耳机** |
| 微信 WebView | 往往不是延迟问题，是 **根本采不到麦** |
| 原生 App | **几乎不降低** 到 VPS 的 RTT；只改善采集/后台/录屏 |

**不要做 App 来「加速」。** App 只为：**稳定共享手机屏幕**、后台仍通话、少回声。

## 带宽

语音约 32 KB/s；另加 1 fps JPEG。5 人同时，VPS 出站仍大约 **1 MB/s 量级**。瓶颈是国际链路，不是 CPU。

---

===== FILE: handoff/gemini-live-standalone/DEPLOYMENT.md =====

# 同 VPS 部署

与机上其它服务 **并存**。不要改、不要停其它站点，除非用户明确要求。

## 隔离

| 项 | 建议 |
|----|------|
| 进程 | 独立 systemd 或独立容器 |
| 端口 | `127.0.0.1:8090`（示例）；勿占 `8080` |
| 域名 | 新子域名 + HTTPS（Caddy `reverse_proxy`） |
| 环境 | 独立 `.env`：`GEMINI_API_KEY`、`HOST`、`PORT` |
| 日志 | 独立目录 |

用户访问与通话路径见 `ACCESS.md`。本服务 **会转发音视频到 Google**，VPS 出站须能访问 `generativelanguage.googleapis.com`（欧盟机房通常可以）。

## 最小形态

1. 应用监听 `127.0.0.1:8090`  
2. Caddy：HTTPS + 反代，**WebSocket 升级**（`/ws`）必须通  
3. 防火墙只开 443  

## 资源

- 无 GPU  
- 内存 512MB～1GB  
- 5 人同时屏享：出站大约 **1 MB/s 量级**（音频 + 1 fps JPEG）  

## 不要

- 把 API key 写进 Caddy 或前端  
- 绑定 `0.0.0.0` 裸对公网  
- 假设用户在桌面 Chrome 或能直连 Google  
- 假设微信内置浏览器能开麦/摄像头

---

===== FILE: handoff/gemini-live-standalone/PLAN.md =====

# 阶段计划

## 阶段 0 — 建仓

- 新 GitHub 仓库  
- 手机 UI + VPS 中继 + 官方采集代码改编  
- `.env.example`、gitignore、复制本交接包到 `docs/`

## 阶段 1 — MVP（手机网页）

1. 微信 WebView 检测 + 去系统浏览器  
2. iPhone Safari、Android Chrome：语音 + 摄像头 + 打断  
3. 1 fps；中继；独立端口 + Caddy `/ws`  
4. 屏享：能做就做，写明机型；做不到就文档化，不阻塞语音+摄像头验收  
5. `ACCEPTANCE.md`

## 阶段 1.5 — 仅当用户确认「必须共享其它 App 画面」

薄原生壳 + 系统录屏，仍连同一 VPS。5 人内部分发，不上商店也可以。

## 阶段 2 — 再确认

Look、换脑 A、会话导出、LiveKit。

阶段不要混在一个 PR。

---

===== FILE: handoff/gemini-live-standalone/ACCEPTANCE.md =====

# 验收

真机 + 真实 `GEMINI_API_KEY`。微信内成功 **不是** 通过条件。

## MVP

| # | 步骤 | 通过 |
|---|------|------|
| 1 | HTTPS 手机打开 | 无长期 key；WSS 打本站 |
| 2 | **微信内打开** | 明确引导去 Safari/Chrome；不要求在此通话 |
| 3 | **iPhone Safari** 语音短句 | 出声、非数秒串联 |
| 4 | 同上打断 | 让路 |
| 5 | **iPhone Safari 摄像头**对准大字 | 能描述看到的内容 |
| 6 | **Android Chrome** 重复 3–5 | 同样通过 |
| 7 | 耳机提示出现在 UI | 有 |
| 8 | 尝试屏享 | 记下成功机型；失败不判 MVP 失败（记入 README） |
| 9 | VPS 独立端口 + 反代 | 不抢其它服务端口 |

## 失败

- 只在桌面测过  
- 无摄像头路径却声称「能看屏」  
- 默认 C2S  
- 微信里静默失败、无引导  

## 阶段 1.5（未确认不测）

- iPhone 能共享其它 App 画面并继续说话

---

===== FILE: handoff/gemini-live-standalone/DONT.md =====

# 不要做

## MVP

- 当桌面 Chrome 产品做（用户几乎不用电脑）  
- 把微信内置浏览器当可通话环境（不提示离开）  
- 宣称 iPhone 网页已能稳定共享任意 App 屏幕  
- 为「加速」做 App  
- 浏览器直连 Google（C2S）当默认  
- LiveKit / vision-demo / 小程序当第一版  
- 640 糊图当默认  
- 换 S2S 供应商、数字人、PSTN、商店上架  

## 安全 / 部署

- API key 进 git 或前端  
- 占 `8080`、停其它服务  
- 无 TLS  

## 口径

- 不要说 App 能消除中欧 RTT  
- 不要把 1 fps 说成 30fps 视频  
- 不要把手机网页屏享说成已对齐官方 Gemini App

---

===== FILE: handoff/gemini-live-standalone/DECISIONS.md =====

# 已定决策

## 1. 独立产品，同 VPS

约 5 人，中国，**几乎都用手机**。

## 2. 访问 = 系统浏览器里的手机网页，不是微信，不是先做 App

微信内点链接会踩采集权限。MVP 必须引导「在 Safari/Chrome 打开」。

App **不降低** 中国到欧盟延迟。App 只为：**录制其它 App 的屏幕**、后台、少回声。等网页验证语音+摄像头后再考虑（阶段 1.5）。

## 3. 「能看」在手机上 = 摄像头优先，不是桌面屏享

桌面 `getDisplayMedia` 不能当 iPhone/微信的承诺。摄像头对准实物或另一块屏，是网页能做的「看」。

## 4. 中继，不默认 C2S

浏览器 → VPS → Gemini。

## 5. 延迟

手机蜂窝 + 中继，首响大约再慢 **0.3–0.8s**。耳机。不要用 App 宣传加速。

---

===== FILE: handoff/gemini-live-standalone/SOURCES.md =====

# 上游

## MVP 必读

- https://github.com/google-gemini/gemini-live-api-examples  
  - `gemini-live-ephemeral-tokens-websocket/` ← **借采集**：`AudioStreamer`、`VideoStreamer`（摄像头）、可选 `ScreenCapture`  
  - `gemini-live-genai-python-sdk/` ← **借服务端** Live 中继；**勿抄前端 640 屏享**  
- https://ai.google.dev/gemini-api/docs/live-api  
- https://ai.google.dev/gemini-api/docs/live-api/capabilities  

## 连接方式

- **默认：** 浏览器 WSS → 本站 → Google（中国用户）  
- **不要默认：** 浏览器 ephemeral token 直连 `generativelanguage.googleapis.com`

## 阶段 2

- https://docs.livekit.io/agents/models/realtime/plugins/gemini/  

## 可选

- https://github.com/google-gemini/gemini-skills

---

===== END OF BUNDLE =====
