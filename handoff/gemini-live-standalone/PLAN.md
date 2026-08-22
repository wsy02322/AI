# 阶段计划

## 阶段 0 — 建仓

- 用户新建 GitHub 仓库  
- Fork/改编 `gemini-live-ephemeral-tokens-websocket`  
- `.env.example`、README、gitignore  
- 复制本交接包到 `docs/`

## 阶段 1 — MVP

1. Token 后端 + 浏览器直连 Live  
2. 麦克风 S2S + 打断  
3. `ScreenCapture`，fps=1 固定  
4. 屏享画布 ≥ 1280；`media_resolution` high（README 注明费用）  
5. 停共享 / 关页释放轨道  
6. `ACCEPTANCE.md` 全过  
7. `DEPLOYMENT.md`：VPS 上独立端口 + 反代（用户确认域名后）

**完成定义：** 真实 `GEMINI_API_KEY` 通话成功，非仅静态页。

## 阶段 2 — 须用户再确认

1. Look（先整帧高清，再点选）  
2. 换脑 A（tool 调其它模型）  
3. 本产品内会话导出/历史  
4. LiveKit（弱网/多人）  

阶段 1 与 2 不要同一 PR。
