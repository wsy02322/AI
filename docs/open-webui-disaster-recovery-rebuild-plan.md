# Open WebUI 灾备与重建 — 重规划（规格驱动）

> **状态**：重规划已记录，待确认后落地  
> **最后更新**：2026-08-20（v2，替代 v1「全量快照」思路）  
> **核心转变**：不追求复刻某一天的 **代码与配置字节**，而追求在任何合理新版本上 **复现同一套能力与体验**。  
> **关联**：`open-webui-openrouter-image-continuity-plan.md`（错误与补丁历史）、`open-webui-user-guidance-plan.md`（界面指引意图）

---

## 0. 真正要保护的是什么？

| 类别 | 是否重要 | 说明 |
|------|----------|------|
| **用户体验契约**（用哪个模型、界面说什么、Integrations 长什么样） | ✅ **最重要** | 可写成验收表，与版本无关 |
| **稳定性约束**（什么不能做、为何会 404） | ✅ **最重要** | 错误目录 + 根因模式 |
| **难以发现的工程细节**（merge valves、filter 顺序、API 字段） | ✅ **重要** | 文档化「为什么」，不是贴代码 |
| **自动验收 / 冒烟探针** | ✅ **重要** | 证明「当前仍达标」的唯一客观依据 |
| **用户聊天与上传文件** | ✅ **重要**（若业务需要） | 仅此类数据 **真正不可逆** |
| OpenRouter / Admin **密钥** | ⚪ 低 | 重新填入即可 |
| **某一版 Function 源码全文** | ⚪ 低 | Pipe 常更新；Agent 可按规格重写 Filter |
| **466 个模型的完整 metadata** | ⚪ 低 | Pipe 同步会再生；只需 **public 名单 + 置顶** |
| **完整 configs/export JSON** | ⚪ 中低 | 参考用；版本一变字段即变 |
| **锁死 OWUI + Pipe 某一版本** | ⚠️ 次要 | 可作 **应急回滚**，不宜作唯一策略 |

**结论**：防崩的重点不是「存档一切」，而是 **写清要什么 + 什么会坏 + 怎么验**。

---

## 1. 三种策略对比

### 方案一：锁死版本 + 全量配置快照

| 优点 | 缺点 |
|------|------|
| 恢复最快、字节级一致 | Pipe/OWUI **安全更新、新模型** 被锁死 |
| 适合「博物馆式」冻结 | 快照 **不含** OpenRouter 侧变化；仍会悄悄失效 |
| | Function 表 + DB 备份 **体积大、难 diff** |
| | 其他 Agent 只学会「还原文件」，不懂 **为何** |

**适用**：短期应急回滚（「昨天还能用」），**不适合** 作为长期主策略。

### 方案二：明晰功能 + 错误 + 关键细节（规格驱动）

| 优点 | 缺点 |
|------|------|
| **跨版本可重建** | 需要写得准；依赖验收脚本兜底 |
| Agent 理解 **目的**，可换实现路径 | 首次重建比快照慢 |
| 新 Pipe 版本可 **迁移** 而非整体报废 | 极隐蔽回归需靠探针发现 |

**适用**：本项目的 **主策略**（OpenRouter Pipe 高频更替）。

### 方案三（推荐）：规格 + 验收 + 轻量快照

```
┌─────────────────────────────────────────┐
│  Layer 1: 能力规格 + 决策日志 + 错误目录   │  ← 真相源（git）
├─────────────────────────────────────────┤
│  Layer 2: verify_stack.py 自动验收        │  ← 是否达标（git）
├─────────────────────────────────────────┤
│  Layer 3: 现有 scripts（可选加速器）      │  ← 非真相源（git）
├─────────────────────────────────────────┤
│  Layer 4: 轻量快照（仅应急）              │  ← 私有存储，可选
│           DB 周备 + 用户数据日备          │
└─────────────────────────────────────────┘
```

**比方案二更棒之处**：规格写人话，**验收写机器**；快照只防「连规格都来不及读」的灾难。

---

## 2. 能力规格（Agent 的「目标清晰」应清晰到什么程度）

重建成功 = **§2.1 体验** + **§2.2 约束** 全部通过 `verify_stack.py`（待写），而非与 2026-08-19 字节一致。

### 2.1 用户体验（What users should see）

| ID | 规格 |
|----|------|
| UX-1 | **四格能力**：Chat（Sol Pro / Opus）、Quick search（Sonar Pro Search）、Deep report（Sonar Deep Research）、Images（Banana Pro / GPT Image 2）— **换模型即换能力** |
| UX-2 | **英文指引**：两条常驻 Banner（pick model + Reasoning depth）+ 关键模型 Description +（可选）空对话 chips 带 “Select … first” |
| UX-3 | **Integrations 简约**：日常聊天 **不出现** OR Web Tools、OR Image Gen、OWUI Web Search；保留 Direct Uploads；图像模型保留 native image filter |
| UX-4 | **Reasoning depth** 在 UI 有可见说明：难题 high/xhigh，简单题 low/medium |
| UX-5 | Deep Research：**2–10 分钟** 等待写在 Deep 模型说明或 Banner 中 |

### 2.2 稳定性约束（What must NOT happen）

| ID | 规格 |
|----|------|
| ST-1 | Sonar / 纯图像模型：**不得** 向 OpenRouter 发送 tool calling（含 `get_current_timestamp`）→ 无 404 |
| ST-2 | **不得** 依赖 per-model Web Tools 做搜索（Sonar 自带搜索；双搜易坏） |
| ST-3 | `gpt-image-*`、`seedream-5*`：**必须** 走 Images API，非 chat/completions |
| ST-4 | Pipe valves 更新：**必须 merge**，禁止空覆盖（防 API_KEY 丢失） |
| ST-5 | Pipe auto-install web_tools/image_gen：**应关闭**，防更新覆盖补丁 |
| ST-6 | `UPDATE_MODEL_CAPABILITIES`：**应 false**，防 catalog 把 `web_search` 写回 |

### 2.3 能力范围（What we intentionally do NOT promise）

- 同一对话内无感「聊完再画」（需换模型；路线 S）
- 图像像素级锁定 / 蒙版 inpainting（未实现）
- Reve 2.1 等 OpenRouter 未上架模型

---

## 3. 错误目录（Agent 按「现象 → 根因 → 修复模式」重建）

**不要** 死记某次补丁的 diff；记 **模式**。详细历史见 `open-webui-openrouter-image-continuity-plan.md` §2。

| 现象 | 根因模式 | 修复模式（版本无关） |
|------|----------|----------------------|
| `No endpoints found that support tool use` + `get_current_timestamp` | 向 **不支持 tools** 的模型注入了 OWUI builtin / OR server tools | 全局 Guard 剥离 tools；Sonar 上 web_tools/image_gen **早退或停用**；`builtin_tools` 默认 false |
| Sonar 上开了 Web Tools 仍 404 | Perplexity **不支持** chat completions tools | **不要** 引导用户开 Web Tools；方案 A 隐藏 |
| `gpt-image-*` chat endpoint 错误 | 图像模型走错 API | Pipe 或等价逻辑：**Images API 路由** |
| `seedream-5` OpenRouter 500 | 同左 | `_is_openrouter_images_api_model` 类逻辑 + resolution 映射 |
| 多轮图像 131072 token | 历史多图整段进上下文 | image **context guard** + chat 路径 context compression |
| Pipe 更新后 Sonar 又坏 | auto-install 覆盖 Filter | `AUTO_INSTALL_*=false` + 重跑 guard 逻辑 |
| `model/update` 500 | 缺 `access_grants` 等字段 | 带完整 payload 或 Admin UI |
| valves 更新后全站断 | **全量覆盖** valves | **仅 merge** 变更字段 |
| picker / `/api/models` 空、聊天 `Model not found` | Pipe `API_KEY` 解密失败（`WEBUI_SECRET_KEY` 变了）或误调 **空** `POST /api/v1/models/sync`（会删光 DB 模型行） | **禁止空 sync**。用仍明文的 OpenRouter 密钥 merge 回 Pipe valves → `GET /api/models?refresh=true` → `scripts/restore_public_grants.py` → wave0 / plan A / banners |

**Agent 重建时**：先读错误表 → 实现 **等价约束** → 跑验收，而非找旧 `content` 粘贴。

---

## 4. 难以发现的细节（ worth documenting, not freezing code）

| 细节 | 为何难发现 |
|------|------------|
| Filter **priority 越低越先执行**（inlet）；Guard 要 **最后** 剥 tools | per-model Filter 会在 Guard 之后 **再注入** server_tools |
| `POST /api/v1/configs/banners` body 是 `{"banners":[...]}` | 不是裸数组 |
| `POST /api/v1/configs/suggestions` body 是 `{"suggestions":[...]}` | |
| Prompt chips **不会** 自动切换模型 | chip 文案必须写 “Select X first” |
| Banner 仅 **HTML**，无 Markdown | |
| 登录用 `OPENWEBUI_USERNAME` 未必等于 email | 本实例 username 更稳 |
| Public 模型：`access_grants` principal `*` | Pipe 默认图像模型仅 admin |
| OpenRouter Pipe 模型 id 前缀 `open_webui_openrouter_integration.` | |

这些应进 **`AGENTS.md` + 错误目录**，不必进 Function 源码快照。

---

## 5. 决策日志（为何这样设计 — Agent 勿擅自改回）

| 决策 | 原因 | 若回退会怎样 |
|------|------|--------------|
| **方案 A**：隐藏 Web Tools / Image Gen / Web Search | 简约 + Sonar/图像 tool 404 | 用户误开 → 404；双搜 |
| **两档 Sonar** 负责搜索，不用 Workspace 包装 | 同家族换模型即深度 | 多余入口 |
| **不装** 第二套 Pipe / admirito | 冲突与维护成本 | |
| 界面指引 **英文** | 用户要求 | |
| Banners **non-dismissible**（当前） | 彰显 game changer | 用户关掉后仍误用 |
| `scripts/` 是加速器，**非** 唯一真相源 | Pipe 版本变仍可重写 | |

---

## 6. 什么值得备份（缩小后的「不可逆」清单）

| 资产 | 频率 | 说明 |
|------|------|------|
| **用户 chats / 上传文件** | 日备 | 真正难再现 |
| **OWUI DB** | 周备 + 大改前 | 恢复「昨天状态」应急；**非** 重建主路径 |
| **git：规格 + verify + scripts** | 每次合并 | 主重建路径 |
| configs/export **脱敏摘要**（非全量） | 可选月备 | 仅当 diff 规格是否漂移 |
| Function 源码全量 | **一般不备** | 除非做法一应急包 |

**密钥**：不入库；重建时人工或 Secret 注入即可。

---

## 7. 给其他 Agent 的重建流程（规格驱动，非抄快照）

### Step 1 — 读规格（15 min）

1. 本文件 §2–§5  
2. `open-webui-openrouter-image-continuity-plan.md`（图像错误与测试列表）  
3. `open-webui-user-guidance-plan.md`（界面英文意图）

### Step 2 — 搭平台（版本可新）

1. 安装 OWUI + 安装 **当前** OpenRouter Pipe（记录版本号入 `docs/VERSIONS.md`）  
2. **Merge** Pipe valves：API_KEY + §2.2 约束相关 false  
3. 关闭 Direct Connections  

### Step 3 — 实现稳定性（按模式，非按旧代码）

1. 全局 Guards：剥 tools / 图像 context / Sonar search-native  
2. web_tools & image_gen：Sonar/图像 **inlet 早退** 或停用 + 不 attach  
3. 方案 A：剥 filterIds、关 OWUI Web Search、`UPDATE_MODEL_CAPABILITIES=false`  
4. 图像：Images API 路由（gpt-image、seedream-5）— 若新 Pipe 未内置则补  

**可用** `scripts/*.py` **若仍兼容**；不兼容则按 §3 重写。

### Step 4 — 产品与指引

1. Public + 置顶（§2.1 四格 + 已测图像列表）  
2. 英文 Banners / Description / Chips（§2.1 UX-2；可复制 `apply_ui_guidance_banners.py` 内 **文案常量**，非依赖其代码结构）  

### Step 5 — 验收

运行 `verify_stack.py`（待实现）：  
- ST-1～ST-6 探针  
- UX-1～UX-5 抽样（API + 可选 UI）  
- 全绿 = 重建完成；**不必** 与历史快照 diff  

---

## 8. 仓库待建设（确认后优先级）

| 优先级 | 工件 | 作用 |
|--------|------|------|
| **P0** | `docs/SPEC.md`（或本文件 §2 独立化） | 能力规格单一页 |
| **P0** | `scripts/verify_stack.py` | 机器验收 = 防崩核心 |
| **P1** | `AGENTS.md` | Agent 入口：读 SPEC → verify → 按需跑 scripts |
| **P1** | `docs/VERSIONS.md` | 记录「上次验通过的 OWUI / Pipe 版本」；**不锁死** |
| **P2** | `scripts/*.py` 改为「实现参考」，头部注明 **规格见 SPEC** | |
| **P3** | 周备 DB + 用户数据（运维，非 Agent 文档重点） | 应急 only |
| **弃用倾向** | 全量 `export` 入 git、`snapshots/functions` 全文 | 除非做法一应急包 |

---

## 9. 方案一 vs 方案二 vs 推荐混合（一句话）

- **只锁版本（方案一）**：像备份一台 **特定日期的整机** — 快，但很快过期。  
- **只写文档（方案二）**：像 **建筑图纸** — 耐久，但需 **验收** 防止图纸与现场不符。  
- **推荐混合（方案三）**：**图纸 + 自动巡检 + 用户数据备份**；代码与密钥随时可再填。

对本项目（Pipe 高频更新、大量 Filter 补丁），**方案三 > 方案二 > 方案一**。

---

## 10. 待你确认

- [ ] 采纳 **方案三** 为正式策略，弱化 v1 全量快照思路  
- [ ] 下一迭代先做 **P0**：`verify_stack.py` + `AGENTS.md`  
- [ ] 应急 DB 周备：是否由你运维侧做（不进 Agent 主路径）  
- [ ] `scripts/` 定位改为「可选加速器」，规格以 §2 为准  

**确认前**：不扩大快照范围、不锁 Pipe 版本。

---

## 11. 文档地图（v2）

| 读者 | 读什么 |
|------|--------|
| Agent 重建 | 本文件 §2–§7 → `AGENTS.md`（待写）→ `verify_stack.py` |
| 图像细节 | `open-webui-openrouter-image-continuity-plan.md` |
| 界面文案意图 | `open-webui-user-guidance-plan.md` |
| 运维应急恢复 | §6 备份表 + DB restore（非 Agent 主路径） |
