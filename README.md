# AI

Open WebUI + OpenRouter。生产：`https://micropigeon.com`。

GitHub **几乎仅用于灾后重建**（规格 + 脚本 + 钉子）。

## 先读哪份

| 文件 | 角色 |
|------|------|
| `docs/open-webui-rebuild-archive.md` | **灾后入口** / 现网钉子 / 错误目录 |
| `AGENTS.md` | 禁令、Pipe merge、脚本表 |
| `docs/SPEC.md` | **产品契约** |
| `docs/VERSIONS.md` | 上次验收指纹 |

## 专题 plan（未完成主线；重建时不要顺便做）

- `docs/open-webui-upgrade-0113-plan.md` — **已落地**：官方 **0.11.3** 钉 digest（VPS 换镜像 + 仓库脚本重放）
- `docs/open-webui-notebook-youtube-plan.md` — P0-D
- `docs/open-webui-live-voice-screen-plan.md` — P0-B / P0-C
- `docs/open-webui-openrouter-image-continuity-plan.md` — 图像错误模式
- `docs/open-webui-file-ingest-plan.md` — 文件录入（T0 未确认）
- `docs/open-webui-secret-key-persist-plan.md` — 运维 L0

## 独立产品（不要并进 OWUI）

`handoff/gemini-live-standalone/` — Gemini Live 新产品交接。工作源是该目录下的拆分文件。
