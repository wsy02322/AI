# GitHub 瘦身 — 分析与方案（未确认不删）

> **状态**：v1 **仅分析 / plan**。未确认不删文件、不改实例、不改 Pipe。  
> **原则**：GitHub **几乎仅用于灾后重建**（规格 + 可重放脚本 + 现网钉子）。不是演示集，不是调查笔记本。  
> **验收**：瘦身后，新 Agent 只读入口清单就能按 `rebuild-archive` §5 把站点救回来；`verify_stack.py` 仍是客观门。  
> **日期**：2026-09-03

关联：`AGENTS.md`（GitHub 定位）、`docs/open-webui-rebuild-archive.md`、`docs/SPEC.md`

---

## 0. 结论先看

**现在不必为了原则大卸仓库。** 树里已经没有截屏/录屏；主体是文档 + `scripts/`。

要瘦的是 **重复与过期叙述**：同一套 21 public / Banner / L0 写了 4～6 遍，且有的副本还停在「19 public / extra 非 public / ComfyUI+蒙版 Don't」。灾后读错文件会按旧数字施工。

| 判定 | 含义 |
|------|------|
| **必留** | 删了就不能按规格重建，或会误施工 |
| **并入后可删** | 独特句先搬进必留文件，再删副本 |
| **可出树** | 结论已进 SPEC / VERSIONS；全文只在 git history |
| **另议** | 不是 OWUI 重建物（独立 Gemini Live）；未确认不搬 |

未确认前：**零删除**。本文件就是请你选档。

---

## 1. 现网仓库盘点（本工作树）

约 16 份 `docs/*.md` + `AGENTS.md` + `README.md` + `scripts/` 22 个 py + `handoff/gemini-live-standalone/` 14 个 md。无图片/视频。

### 1.1 必留（灾后核心）

| 工件 | 为什么不能删 |
|------|----------------|
| `AGENTS.md` | 禁令、Pipe merge、空 sync、脚本表、Cloud 验收习惯 |
| `docs/SPEC.md` | 产品契约（UX / ST / P0 / Later / Don't） |
| `docs/open-webui-rebuild-archive.md` | 钉子 + 从零顺序 §5 |
| `docs/VERSIONS.md` | 上次 verify 指纹；Pipe 更新对照 |
| `scripts/stack_contract.py` | 21 public / Guard / Banner / Task **机器真相** |
| `scripts/apply_*.py` + `restore_public_grants.py` + `ops_l0_common.py` | 重放 |
| `scripts/patch_pipe_*.py` + 对应 `test_patch_*.py` | Pipe 更新后补 ST-10 / ST-11 |
| `scripts/verify_*.py`（stack / ops / live / compare / fable / notebook） | 重建门 |
| `scripts/ingest_youtube_notebook.py` | N1 重放 |
| `README.md` | 薄索引（可再削） |

未合入本树、但 **合入后也是必留**（不要当瘦身对象）：

- `deploy/owui-ui/`（助手 CSS；重建要热补两条路径）
- ST-13 图像 data URI 落盘脚本 + plan（现网 Pipe sha 已是 `f797e92d6d3f`）

### 1.2 专题 plan：必留，可截短

这些防止重建时「顺便做」或丢掉未完成 P0。正文里的竞品长表 / 旧 Review 可以后砍，**文件先留**。

| 文件 | 重建真正需要的 |
|------|----------------|
| `open-webui-secret-key-persist-plan.md` | §2 容器重建 SOP + K1/K2 冻结。其余可并进 archive |
| `open-webui-live-voice-screen-plan.md` | L1 已落地 vs L2/L3 未确认；rbb 不能冒充屏享达标 |
| `open-webui-notebook-youtube-plan.md` | NL-A ≠ 达标；N2+ 未确认；口播风控 |
| `open-webui-file-ingest-plan.md` | T0 未确认；不要装 Tika / 扩 MIME |
| `open-webui-openrouter-image-continuity-plan.md` | 错误**模式**（tools 404、Images API、131072）；按模式补，不盲贴 content |

`optimized-plan.md`：路线 S 论证 + Wave 1/2 必做。论证可压进 SPEC UX-6 一段；波次表可并进 SPEC Later。

### 1.3 并入后可删（重复主战场）

| 文件 | 与必留的重叠 | 并入前必须搬走的独特句 |
|------|----------------|------------------------|
| `open-webui-disaster-recovery-rebuild-plan.md`（14KB） | 策略已由 archive 实行；§2 草稿还写 **19 public** / 双条 v2 | §3 错误目录（与 continuity 有交叉）；§4 难发现 API 形状（banners 包一层）；§5 决策日志 |
| `open-webui-delta-vs-stock.md`（22KB） | Admin 表 ≈ archive §3.2；public 名单 ≈ `stack_contract` | §9 坑映射（部分已在错误目录）；历史 gptsapi 槽「不要复活」 |
| `open-webui-user-guidance-plan.md`（2KB） | 文案已在 archive §3.3 **和** `apply_ui_guidance_banners.py` | 设计规则 1～5（英文、一条 Banner、改 id 会再弹出）→ 并进 apply 脚本头或 archive §3.3 |
| `open-webui-optimized-plan.md`（16KB） | Now/Later/Don't ≈ SPEC | §2 路线 S **为何不走同会话作图**（约 1 屏）；Wave 1/2 成功标准 |

### 1.4 可出树（结论已落地）

| 文件 / 脚本 | 出树后靠什么重建 |
|-------------|------------------|
| `open-webui-compare-first-class-plan.md`（18KB） | SPEC ST-10 + `patch_pipe_cross_model_reasoning.py` + `verify_compare_cross_model.py`。S3 真分栏未做：SPEC Later 留一句即可 |
| `open-webui-gpt-audio-trial-plan.md`（6KB） | VERSIONS 一行 + Live plan「不要用 gpt-audio 冒充 Call S2S」 |
| `scripts/run_ga_a_trial.py` | 同上；重跑试验可从 git history 取回 |
| `handoff/gemini-live-standalone/HANDOFF_BUNDLE.md`（16KB） | 同目录拆分文件的打包快照，README 已写「不要只改 BUNDLE」 |

`scripts/fix_sonar_tool_guard.py`：**不要出树。** 现网靠 Guard + 停用 web_tools；若有人误启用，这份是补丁参考（AGENTS 表已列）。

### 1.5 另议（不是本 OWUI 重建）

`handoff/gemini-live-standalone/`（去掉 BUNDLE 后仍约 12 个 md）。根 `AGENTS.md` 已写 **不要并进 OWUI 文档**。

| 档 | 做法 |
|----|------|
| 稳 | **留在子目录**，OWUI 入口只留一行指针 |
| 顶 | **迁到独立仓库**，本仓删目录（须你点头；交接链会断） |

未确认不搬。

---

## 2. 过期数字（瘦身时顺手修，或不瘦也该修）

灾后危害 **大于** 文件个数。副本之间已经打架：

| 位置 | 过期说法 | 现行 |
|------|----------|------|
| disaster-recovery §2.1 | 19 public | 21 public = picker |
| optimized-plan §5 | 「维持 19」 | 同上 |
| archive §3.4 / VERSIONS Pipe sha | `7415c2e4347a` | 现网探针过 `f797e92d6d3f`（ST-13，另一 PR） |
| archive §7 Don't | ComfyUI / **蒙版** | SPEC：蒙版随独立画图 Studio 为 Later；ComfyUI 仍 Don't |
| 多份「extra Gemini 非 public」 | 已作废 | 两条 Gemini **也是 public** |

瘦身波次应 **先合并再删**，避免只删新文件、留下旧数字。

---

## 3. 两档（请选一档再执行）

都不改实例。都不动 `stack_contract` / apply / verify 行为。

### 档 A — 略降级、简单稳定（推荐先做）

目标：少读错文件，少删错独特句。

1. 把 §1.3 的独特句并进 `rebuild-archive`（错误目录 + 难发现 API）和 SPEC（Later 波次一句、路线 S 一段）。  
2. 从树删除：disaster-recovery、delta-vs-stock、user-guidance、optimized-plan、compare 长文、gpt-audio 试验文、`run_ga_a_trial.py`、`HANDOFF_BUNDLE.md`。  
3. 改 README / archive §8 地图：入口 = `AGENTS` → archive → SPEC → VERSIONS → 四个未完成专题 plan。  
4. 顺手修 §2 过期数字（含 archive Don't / Pipe sha 指针：sha 以合入的 ST-13 为准，不在本波次改 Pipe）。  
5. Gemini Live 目录 **不动**。

删完后 OWUI 文档大约：**入口 4 份 + 专题 5 份 + 本 slim plan（执行完可删或改成「已执行」）**。

风险：并入时漏一句（例如 banners POST 包一层）。缓解：并入用对照表，删前 `git grep` 文件名。

### 档 B — 顶级（一次收成「四件套」）

目标：新 Agent 只读四份就能重建。

| 留下 | 吃进什么 |
|------|----------|
| `AGENTS.md` | 操作 + 脚本表（已是） |
| `SPEC.md` | 契约 + Later/Don't + 路线 S 一段 + 未完成 P0 **约束摘要** |
| `rebuild-archive.md` | 钉子 + §5 顺序 + 错误目录 + L0 SOP 精简 |
| `VERSIONS.md` | 指纹 |

专题 plan（Live / Notebook / 文件 / 图像 / 密钥）**压成 SPEC 附录或 archive 短节**，原文出树。脚本一个不删（除 GA-A）。Gemini Live **仍另议**。

风险：未完成 P0 的细节（L2 不能冒充屏享、Tika 3 vs 4、NL-A≠达标）被压丢，下次施工靠记忆。档 A 更稳。

---

## 4. 明确不做（两档都禁止）

- 不改生产实例、不改 Pipe valves、不跑 `models/sync`  
- 不删任何 `verify_*.py` / `apply_*.py` / `patch_pipe_*.py` / `stack_contract.py`  
- 不把 walkthrough 媒体补进仓库  
- 不把 Gemini Live 并进 OWUI SPEC  
- 不把「文档变少」写成能力完成  

---

## 5. 建议执行顺序（确认档位之后）

1. 你点 **档 A** 或 **档 B**（或「先只修过期数字、先不删」）。  
2. 开独立分支，**先并入、跑 `git grep`、再删**。  
3. 更新 README / archive 地图。  
4. 不跑浏览器；用文档内链和脚本 `--help` / `verify_stack` 仍可导入 `stack_contract` 即可。  
5. 本文件标记已执行；档 A 执行后本文件也可出树（git history 在）。

---

## 6. 请你拍板

1. **档 A**（先并后删重复/试验文，专题 plan 留下）  
2. **档 B**（收到四件套）  
3. **只修过期数字**，文件一个不删  
4. Gemini Live：`handoff/` 继续隔离 / 迁独立仓库 / 以后再说  

默认建议：**3 或 A**。B 等 A 用过一次灾后阅读再考虑。
