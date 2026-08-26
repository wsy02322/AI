# AI

Open WebUI + OpenRouter 文档见 `docs/`：

- `AGENTS.md` — **当前 Agent 宪法**（Cloud 自动注入；不要把操作手册写回来）
- `.cursor/rules/no-browser.mdc` — 一般情况不开浏览器（覆盖「凡 UI 必须浏览器」）
- `docs/AGENT-ONBOARDING.md` — **新 Agent / 新 session 开工包**（脚本、Runbook、VPS、不要做）
- `deploy/owui-ui/` — **界面覆盖**（`custom.css` ai-ui-1；空 `loader.js`）
- `docs/SPEC.md` — 体验与稳定性契约（含 P0 四条并列；宪法与 AGENTS.md 同步）
- `docs/VERSIONS.md` — 上次验收的 OWUI / Pipe 指纹
- `docs/open-webui-compare-first-class-plan.md` — **多模型对比为一等公民**（连续多轮多图；确认前不改实例）
- `docs/open-webui-optimized-plan.md` — **优化计划**（P0：图像 / 语音聊天 / 屏享 / Notebook·YouTube；视频生成与 slides 为后续必做）
- `docs/open-webui-notebook-youtube-plan.md` — **P0-D Notebook / YouTube**（N1 已执行；口播抓取受 YouTube 风控）
- `docs/open-webui-live-voice-screen-plan.md` — **P0-B/P0-C Live**（L1 已落地于 OWUI）
- `docs/open-webui-gpt-audio-trial-plan.md` — **gpt-audio GA-A 已执行**（无 output_audio；改 Call 仍为 Don't）
- `handoff/gemini-live-standalone/` — **独立 Gemini Live 新产品交接包**（另建新 GitHub 仓库；与 OWUI 无关）
- `docs/open-webui-delta-vs-stock.md` — **相对纯官方 OWUI 的全部改动记录**（单一真相源）
- `docs/open-webui-secret-key-persist-plan.md` — **运维 L0**（接受重登；不持久化 JWT / 不加密 Pipe key）
- `docs/open-webui-disaster-recovery-rebuild-plan.md` — **灾备 v2：规格驱动重建**（非全量快照）
- `docs/open-webui-openrouter-image-continuity-plan.md` — 图像能力、错误与补丁历史
- `docs/open-webui-user-guidance-plan.md` — 界面英文指引意图
