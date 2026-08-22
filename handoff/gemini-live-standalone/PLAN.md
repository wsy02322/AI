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
