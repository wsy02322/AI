# AGENTS.md — 本仓库怎么动 Open WebUI

先读 **`docs/SPEC.md`**，再读 **`docs/open-webui-optimized-plan.md`**。不要凭记忆重开 Web Tools，也不要同会话作图当主路径。

## 宪法（所有动作）

1. 媲美甚至超越 ChatGPT / Grok 等最顶级付费档。特别困难复杂：**先确认**是否改用略微降级、简单稳定特别多的方案。  
2. 务必简单和稳定，优先易维护。  
3. 重大改动：先 plan，确认后再执行。

视频、slides、Live 屏享均为 **Later 必做**（各有独立 plan）。维持 **19 个 public**。

## 改实例前

1. 跑 `python3 scripts/verify_stack.py`（需要 `OPENWEBUI_URL` / `OPENWEBUI_USERNAME` / `OPENWEBUI_PASSWORD`）  
2. 更新 Pipe valves：**merge**，禁止全量覆盖（会丢 `API_KEY`）  
3. 更新模型：`POST /api/v1/models/model/update` 必须带 `access_grants`  

登录优先 `OPENWEBUI_USERNAME`，不一定等于 email。

## 常用脚本（加速器，不是 SPEC）

| 脚本 | 何时 |
|------|------|
| `scripts/verify_stack.py` | 任何改动后；Pipe 更新后 |
| `scripts/verify_compare_cross_model.py` | 对比 ST-10：Grok 密文回放给 Opus 不得 404；同模型续聊仍成功 |
| `scripts/patch_pipe_cross_model_reasoning.py` | S2′：扩 Pipe 重试门（content-only，不碰 valves） |
| `scripts/apply_wave0.py` | 重放 Wave 0：capabilities + Task 模型 |
| `scripts/apply_plan_a_hide_integrations.py` | Pipe 更新后 Integrations 又露出来 |
| `scripts/apply_ui_guidance_banners.py` | Banner / Description / chips / DEFAULT_MODELS |
| `scripts/fix_sonar_tool_guard.py` | 误启用 web_tools 时的补丁参考 |

## Pipe 更新 Runbook

1. 在 Admin 更新 Pipe（或按上游安装）  
2. **Merge** valves：见 SPEC ST-4～ST-6（`apply_plan_a_hide_integrations.py` 会 merge）  
3. 确认 3 个 Guard 仍 global active：`image_tool_guard`、`image_context_guard`、`search_native_tool_guard`  
4. `python3 scripts/apply_plan_a_hide_integrations.py`  
5. `python3 scripts/apply_ui_guidance_banners.py`  
6. `python3 scripts/apply_wave0.py`  
7. `python3 scripts/verify_stack.py` 全绿  
8. 更新 `docs/VERSIONS.md` 的日期与 Pipe 指纹  

若 Images API / Seedream 路由丢失：按 `docs/open-webui-openrouter-image-continuity-plan.md` **模式**补，不要盲贴旧 `content`。

## 不要做

- 给 Sonar / 纯图像灌 tools  
- 打开 Sol Pro `image_generation` 来做同会话作图  
- 一次 public 全部视频模型  
- 关全局 Code Interpreter（只收 Sonar/图像的 capability）  

Filter inlet：**priority 数字越小越先执行**；剥 tools 的 Guard 要靠后。
