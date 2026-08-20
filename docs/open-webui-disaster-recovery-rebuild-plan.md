# Open WebUI 灾备与从零重建规划

> **状态**：规划已记录，待确认后分阶段落地  
> **最后更新**：2026-08-20  
> **目的**：  
> 1. **预防** 服务器崩坏、配置被覆盖、密钥丢失等 **不可逆** 损失；  
> 2. 让 **其他 AI Agent** 仅凭仓库 + 密钥 + 本规划，**从零重建** 到当前实例已实现的 **全部效果与体验**。  
> **关联文档**：  
> - `docs/open-webui-openrouter-image-continuity-plan.md` — 图像修复、方案 A、模型测试  
> - `docs/open-webui-user-guidance-plan.md` — 英文界面指引（Banners / Description / Chips）

---

## 1. 当前「效果与体验」到底包含什么（重建目标清单）

重建成功 = 以下 **全部** 可验证通过，而非「能登录、能聊天」。

### 1.1 产品体验（用户可见）

| # | 体验 | 验收 |
|---|------|------|
| E1 | 两条 **常驻英文 Banner**（选模型 + Reasoning depth，不可 dismiss） | 登录聊天页可见蓝/橙条 |
| E2 | 空对话 **Suggested chips**（4 条，英文，含 “Select … first”） | 新对话可见 |
| E3 | 置顶模型 **英文 Description**（Sonar / Sol / Opus / 图像） | 选模型时副标题 |
| E4 | Integrations **仅** Direct Uploads（+ 图像模型 native filter） | 无 Web Tools / Image Gen / Web Search |
| E5 | 快搜 **Sonar Pro Search**、深度 **Sonar Deep Research** 可用 | chat 200，无 tool 404 |
| E6 | 旗舰文本 **Sol Pro / Opus 5** 等 public | 普通用户可选 |
| E7 | 图像模型 public 且可出图（Banana 2/Pro、GPT Image 2、Seedream 5 等） | 见 §1.3 |
| E8 | 多轮图像对话不常爆 131072 token（context guard） | 长对话图像编辑 |

### 1.2 稳定性与简约（工程约束）

| # | 约束 | 验收 |
|---|------|------|
| S1 | Pipe **不** auto-attach Web Tools / Image Gen | valves + filterIds |
| S2 | OWUI 原生 Web Search **关闭** | `enable_web_search=false` |
| S3 | Sonar / 图像模型 **无** tool calling 404 | 显式 tools 仍 200 |
| S4 | 全局 Guard Filters 存在且 active | 见 §3.2 |
| S5 | Pipe `UPDATE_MODEL_CAPABILITIES=false` | 防止 web_search 被 catalog 写回 |
| S6 | Direct Connections **关闭** | Admin connections |

### 1.3 已测通能力（2026-08-18～19 记录）

**Public 图像 / 文本（前缀 `open_webui_openrouter_integration.`）**：

- 文本：Sonar Pro Search、Sonar Deep Research、Claude Opus 5、GPT-5.6 Sol Pro（+ 其他旗舰若仍 public）
- 图像：GPT Image 2、Nano Banana Pro、Nano Banana 2、GPT-5.4 Image 2、Qwen Image 3 Pro、MAI-Image Pro、Grok Imagine 2.0、Seedream 5.0 Pro/Lite

**Pipe 层补丁（在 OWUI Function 表内，非纯 git）**：

- Images API 路由（gpt-image、seedream-5）
- `openrouter_web_tools` / `openrouter_image_gen` Sonar 早退
- 全局：`openrouter_image_tool_guard`、`openrouter_image_context_guard`、`openrouter_search_native_tool_guard`

### 1.4 已知未达成（重建时 **不要** 假装已有）

- 默认新对话模型仍为 **非 Pipe** 的 `DEFAULT_MODELS` 字符串（待修）
- 图像 **画布连续性**（canonical canvas）Pipe 补丁未做
- `model/update` 显示名 API 曾 500
- Reve 2.1 无 OpenRouter 实例

---

## 2. 不可逆风险登记（为什么要灾备）

| 风险 | 后果 | 可预防？ |
|------|------|----------|
| **整盘 / VM 损坏** 无备份 | OWUI DB、Function 源码补丁、用户数据全丢 | 定期备份 DB + export |
| **Pipe 自动更新** 覆盖 Filter 补丁 | Sonar 404、图像 tool 404 复发 | `AUTO_INSTALL_*=false` + 版本快照 |
| **Pipe valves 全量覆盖** | `API_KEY` 被清空，全站不可用 | 永远 **merge** valves |
| **密钥只存在 valves/环境** 无第二份 | 重建无法调 OpenRouter | Secrets Manager + 恢复流程 |
| **配置只存在于线上** 未进 git | Agent 无法复现 Banners/模型 public | 定期 export + 脚本 |
| **误删 Function**（Filter/Pipe） | Guard 消失，稳定性崩塌 | DB 备份 + Function 导出 |
| **OpenRouter 账户欠费/封禁** | 所有模型失败 | 监控余额（非 OWUI 范畴） |
| **Google PSE key 在 retrieval config** | Web Search 若误开可能异常 | 方案 A 已关；export 时注意勿泄露 |

---

## 3. 必须保护的资产（分三层）

### 3.1 密钥与身份（**永不进 git**）

| 资产 | 存放 | 重建时需要 |
|------|------|------------|
| OpenRouter API Key | Pipe valves `API_KEY` + 备份在 Secrets | 写入 valves merge |
| OWUI Admin 密码 | 用户密码管理器 | `OPENWEBUI_USERNAME` / `PASSWORD` |
| 其他直连 API keys | `/openai/config` 等 | 按 export 恢复 |

### 3.2 OWUI 数据库（**真相源**，2026-08-20 约）

- **Pipe** `open_webui_openrouter_integration`：**content**（含图像/Seedream 等补丁）+ **valves**
- **Filter Functions**（约 38 个）：尤其  
  - 全局：`openrouter_image_tool_guard`、`openrouter_image_context_guard`、`openrouter_search_native_tool_guard`  
  - 已补丁：`openrouter_web_tools`、`openrouter_image_gen`（Sonar 早退）  
  - 已停用：`openrouter_web_tools`、`openrouter_image_gen`（`is_active=false`）
- **Model 表**：466 Pipe 模型 metadata（`filterIds`、`capabilities`、`access_grants`、`description`）
- **Config 表**：Banners、prompt_suggestions、`DEFAULT_PINNED_MODELS`、`DEFAULT_MODEL_METADATA` 等

### 3.3 仓库（**可复现逻辑**，当前 `scripts/`）

| 脚本 | 作用 |
|------|------|
| `scripts/apply_plan_a_hide_integrations.py` | 方案 A：关 auto-attach、停 Filter、剥 filterIds、关 Web Search |
| `scripts/fix_sonar_tool_guard.py` | 补丁 web_tools/image_gen + guard priority |
| `scripts/apply_ui_guidance_banners.py` | 英文 Banners + Description + Suggestions |

**缺口**：尚无 **一键 export**、**一键 rebuild**、Filter **源码快照** 入 git。

---

## 4. 预防策略（确认后执行）

### 4.1 备份（推荐节奏）

| 对象 | 方式 | 频率 | 保留 |
|------|------|------|------|
| OWUI DB | `sqlite` 或 PG dump | **每日** + 大改前 | 30 天 |
| `GET /api/v1/configs/export` | JSON 入 git-private 或 S3 | **每周** + 每次 Agent 大改后 | 90 天 |
| Pipe + 5 个关键 Filter **content** | API 导出到 `snapshots/functions/` | **每次补丁后** | 永久 git |
| Pipe valves（无 key 版） | JSON 快照 | 同上 | git |
| 用户上传文件 | OWUI data 目录 | 按业务需求 | — |

### 4.2 变更纪律（避免人为不可逆）

1. **Pipe valves**：只 `merge`，禁止空对象覆盖。  
2. **Pipe 更新**：更新前跑 `fix_sonar_tool_guard.py`；`AUTO_INSTALL_WEB_TOOLS_FILTER=false`。  
3. **大改前**：DB dump + `configs/export`。  
4. **Secrets**：变更后 24h 内验证 Sonar + 一张图像 smoke test。  
5. **文档**：Agent 每完成一类改动，更新本文件 §1 验收表或 continuity plan。

### 4.3 监控（轻量）

- HTTP `/health` + 登录 smoke（cron）  
- 每日探针：`sonar-pro-search` + `claude-opus-5` + `gemini-3-pro-image` 各 1 次 chat  
- 磁盘、内存、DB 大小告警  

---

## 5. 给其他 AI Agent 的「从零重建」Runbook（规划）

**前提环境变量**（Agent 不得写入 git）：

```bash
OPENWEBUI_URL=https://...
OPENWEBUI_USERNAME=...
OPENWEBUI_PASSWORD=...   # 或 OPENWEBUI_EMAIL
OPENROUTER_API_KEY=...   # 仅用于 merge 进 Pipe valves
```

### Phase 0 — 基础平台

1. 部署 Open WebUI **0.11.0**（与当前一致或兼容）。  
2. 创建 Admin；关闭 Direct Connections。  
3. 安装 Pipe：`open_webui_openrouter_integration`（OpenRouter for Open WebUI，与实例同版本）。  
4. **Merge** Pipe valves：写入 `API_KEY`，设 `ENABLE_DATETIME=false` 等（见 §6.1）。  
5. 等待 Pipe 同步模型目录（~466 模型）。

### Phase 1 — Filter 层（稳定性）

1. 确认/安装全局 Guards（若 Pipe 未自动创建，从 `snapshots/functions/` 恢复 content）。  
2. 运行 `python3 scripts/fix_sonar_tool_guard.py`（web_tools/image_gen Sonar 早退 + guard priority）。  
3. 运行 `python3 scripts/apply_plan_a_hide_integrations.py`（方案 A）。  
4. 验证 S1–S5（§1.2）。

### Phase 2 — 模型可见性与置顶

1. 对 §1.3 模型执行 `access_grants` public（脚本或 continuity plan §10 API）。  
2. `POST /api/v1/configs/models`：`DEFAULT_PINNED_MODELS`、`DEFAULT_MODEL_METADATA`（builtin_tools/web_search 等 false）。  
3. （可选）修正 `DEFAULT_MODELS` → Pipe Sol Pro id。  

### Phase 3 — 用户界面指引（英文）

1. 运行 `python3 scripts/apply_ui_guidance_banners.py`。  
2. 验证 E1–E3（§1.1）。

### Phase 4 — 端到端验收

运行 **§7 验收脚本**（待实现 `scripts/verify_stack.py`）：  
Sonar / Opus / Banana 各 1 chat；检查 banners、filterIds、无 tool 404。

### Phase 5 — 图像连续性（可选，未做则跳过）

按 `open-webui-openrouter-image-continuity-plan.md` §5 A–D。

---

## 6. 关键配置快照（Agent 照抄，密钥除外）

### 6.1 Pipe valves（merge 目标，2026-08-20 线上）

```json
{
  "AUTO_ATTACH_WEB_TOOLS_FILTER": false,
  "AUTO_ATTACH_IMAGE_GEN_FILTER": false,
  "AUTO_DEFAULT_WEB_TOOLS_FILTER": false,
  "AUTO_INSTALL_WEB_TOOLS_FILTER": false,
  "AUTO_INSTALL_IMAGE_GEN_FILTER": false,
  "ENABLE_DATETIME": false,
  "ENABLE_WEB_SEARCH": false,
  "UPDATE_MODEL_CAPABILITIES": false
}
```

### 6.2 置顶模型（`DEFAULT_PINNED_MODELS`）

```
open_webui_openrouter_integration.perplexity.sonar-pro-search
open_webui_openrouter_integration.perplexity.sonar-deep-research
open_webui_openrouter_integration.anthropic.claude-opus-5
open_webui_openrouter_integration.openai.gpt-5.6-sol-pro
```

### 6.3 全局 Filters（必须 active + is_global）

- `openrouter_image_tool_guard`
- `openrouter_image_context_guard`
- `openrouter_search_native_tool_guard`（priority 100）

### 6.4 应停用但保留的 Filters

- `openrouter_web_tools` → `is_active: false`
- `openrouter_image_gen` → `is_active: false`

### 6.5 典型模型 `filterIds`（方案 A 后）

- 文本 / Sonar：`["openrouter_direct_uploads"]`
- 图像（例 Banana Pro）：`["openrouter_direct_uploads", "openrouter_image_filter_generic", "openrouter_image_filter_gemini"]`

### 6.6 Banners（见 `scripts/apply_ui_guidance_banners.py` 内 `BANNERS` 常量）

- `usage-pick-model-v2`（info，non-dismissible）
- `usage-reasoning-depth-v2`（warning，non-dismissible）

---

## 7. 待实现的仓库工件（确认后开发）

| 工件 | 目的 |
|------|------|
| `scripts/export_instance_state.py` | 拉取 export、functions content、public 模型列表 → `snapshots/` |
| `scripts/rebuild_from_scratch.py` | 按 Phase 0–4 顺序调用现有脚本 + API |
| `scripts/verify_stack.py` | §1 验收表自动化 |
| `snapshots/functions/*.py` | Filter/Pipe 关键源码 **脱敏** 快照 |
| `snapshots/config/export-YYYYMMDD.json` | 周期性配置（**脱敏**后可选入 private repo） |
| `AGENTS.md` | Agent 入口：先读本文件 + 跑 verify |
| `.cursor/environment.json` 或部署说明 | OWUI 版本、数据目录、备份 cron |

**脱敏规则**：export 中剔除 API keys、Google PSE key、用户 PII；快照进 git 前自动扫描。

---

## 8. 重建时 Agent 易错点（必读）

1. **不要** 恢复 OR Web Tools / Image Gen 到 filterIds「为了方便」。  
2. **不要** 全量 POST valves（会清空 `API_KEY`）。  
3. **不要** 只装 Pipe 不跑三个 `scripts/` — 体验与稳定性会缺一半。  
4. **不要** 假设 git 里有 Pipe 补丁 — 必须先 export Function content 或跑 fix 脚本。  
5. **model/update** 需带 `access_grants` 才成功。  
6. 用户指引 **必须英文**（Banners / Description / Chips）。  
7. Deep Research 验收要 **≥2 分钟** 超时，不是 30s API 探针。

---

## 9. 分阶段落地建议（对你确认）

| 阶段 | 内容 | 风险 |
|------|------|------|
| **D1** | `export_instance_state.py` + 首次快照入 private 存储 | 低 |
| **D2** | `verify_stack.py` + 每日 cron smoke | 低 |
| **D3** | DB 自动备份 + 恢复演练（季度） | 中 |
| **D4** | `rebuild_from_scratch.py` 在 **空 OWUI** 上试跑 | 中 |
| **D5** | `AGENTS.md` + 修正 DEFAULT_MODELS | 低 |

**本规划确认前**：不自动改线上备份策略、不跑重建试炼。

---

## 10. 决策项

- [ ] 备份存放：本机 / S3 / 私有 git repo？  
- [ ] DB 类型与路径（sqlite vs Postgres）— Agent 需写入 §3.2  
- [ ] 是否允许 `snapshots/` 脱敏后进 **本仓库** 还是仅私有存储？  
- [ ] 重建验收：是否以 §1 全部 E+S 项为 **必须**？  
- [ ] 是否先做 **D1+D2**（export + verify）作为下一迭代？  

---

## 11. 文档地图（给 Agent 的阅读顺序）

1. **本文件** — 灾备 + 重建总览  
2. `open-webui-openrouter-image-continuity-plan.md` — 图像补丁细节、public 模型列表、勿重复操作  
3. `open-webui-user-guidance-plan.md` — 界面英文指引定义  
4. `scripts/*.py` — 可执行恢复步骤  
5. （待写）`AGENTS.md` — 单页入口  
