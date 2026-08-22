# 阶段计划

用户已倾向：**独立新仓 + 能说/能看屏/可打断**。架构已从「先 LiveKit Cloud」改为 **先官方 C2S 示例**。

## 阶段 0 — 新 agent 创建仓库

- 新 Git 仓库，MIT 或与用户一致的许可  
- 复制官方 `gemini-live-ephemeral-tokens-websocket`  
- `.env.example`、本地 README、gitignore（禁止提交 `.env`）  
- 本交接包放入新仓 `docs/handoff-source/` 或 `docs/`

## 阶段 1 — MVP（本交接批准的实现范围）

1. Token 后端 + 浏览器直连 Live。  
2. 麦克风 S2S + 打断。  
3. 屏享按钮：`ScreenCapture`，**fps=1 固定**。  
4. 屏享画布 ≥ 1280 宽（保持宽高比更好）；避免 640×480。  
5. 能开 `media_resolution` high 则开，并在 README 注明费用更高。  
6. 停共享 / 关页释放轨道。  
7. 按 `ACCEPTANCE.md` 手工测。

**阶段 1 完成定义：** 本地（或独立小部署）用真实 Gemini key 跑通，而不是只改了代码没通话。

## 阶段 2 — 超越官网工作流（须用户再确认，可拆单）

建议顺序：

1. **Look**：先「整帧高清快照」tool，再做拉框点选。  
2. **换脑 A**：Gemini 语音 + tool 调文本/代码模型。禁止做换 S2S 供应商。  
3. **转写导出**（文件/剪贴板）→ 再考虑写回 OWUI。  
4. **LiveKit**：仅当 C2S 在真实网络/移动端不够稳。

## 不要并行

阶段 1 与阶段 2 不要同一 PR/同一施工。Hub 仓库继续只维护 OWUI。
