# AI

Open WebUI + OpenRouter。生产：`https://micropigeon.com`。

## 先读哪份

| 文件 | 角色 |
|------|------|
| `AGENTS.md` | Agent 入口：禁令、Pipe merge、脚本表 |
| `docs/SPEC.md` | **产品契约**（UX / ST / P0） |
| `docs/open-webui-rebuild-archive.md` | **灾后 / 现网钉子**（2026-09-01） |
| `docs/VERSIONS.md` | 上次验收的 OWUI / Pipe 指纹 |
| `docs/open-webui-optimized-plan.md` | 波次与 Later / Don't |
| `docs/open-webui-delta-vs-stock.md` | 相对官方差异长表（不是契约） |

## 专题 plan

- `docs/open-webui-notebook-youtube-plan.md` — **P0-D** Notebook / YouTube（N1 已执行；口播受 YouTube 风控）
- `docs/open-webui-live-voice-screen-plan.md` — **P0-B/P0-C** Live（L1 已落地；`verify_live_baseline.py` 已有）
- `docs/open-webui-openrouter-image-continuity-plan.md` — 图像能力、错误与补丁历史
- `docs/open-webui-compare-first-class-plan.md` — 多模型对比（确认前不改实例）
- `docs/open-webui-gpt-audio-trial-plan.md` — gpt-audio GA-A 已执行（改 Call 仍为 Don't）
- `docs/open-webui-file-ingest-plan.md` — 文件录入（T0 未确认，不装 Tika）
- `docs/open-webui-user-guidance-plan.md` — 英文指引（现网一条 `usage-guide-v3`）
- `docs/open-webui-secret-key-persist-plan.md` — 运维 L0（接受重登；不持久化 JWT）
- `docs/open-webui-disaster-recovery-rebuild-plan.md` — 灾备策略（规格驱动，非全量快照）

## 独立产品（不要并进 OWUI）

`handoff/gemini-live-standalone/` — Gemini Live 新产品交接。工作源是该目录下的拆分文件；`HANDOFF_BUNDLE.md` 只是打包下载用。根目录 `AGENTS.md` / `docs/SPEC.md` 管的是 Open WebUI，不是这个 handoff。
