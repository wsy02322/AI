# Open WebUI 界面内使用指引 — 规划稿

> **状态**：规划已记录，待用户确认后落地到 **Admin 界面配置**（非仓库长文档）  
> **最后更新**：2026-08-19  
> **用户意图**：指引要出现在 **使用界面**（General UI Banners 等），让普通用户 **不用读文档** 也能选对模型、调 Reasoning。  
> **关联技术文档**：`docs/open-webui-openrouter-image-continuity-plan.md`

---

## 1. 目标与原则

| 原则 | 说明 |
|------|------|
| **界面优先** | Banners、首页示例、模型描述 > Markdown 文档 |
| **短、可扫** | 每条 banner 一行标题 + 一两句；可折叠详情 |
| **与方案 A 一致** | 不引导用户寻找已隐藏的 OR Web Tools / Image Gen / Web Search |
| **可关闭** | 除「常驻简版」外，其余 `dismissible: true` |
| **中文为主** | HTML 内容；模型名保留界面英文 |

---

## 2. Open WebUI 可用的「界面载体」（按优先级）

### 2.1 General UI Banners（**主战场**）

- **位置**：Admin Panel → **Settings → Admin → System → General → Banners**  
- **API**：`GET/POST /api/v1/configs/banners`，body：`{"banners": [ ... ]}`  
- **展示**：登录后全局顶部色条，所有页面可见（含聊天）  
- **格式**：**仅 HTML**（无 Markdown）；支持 `&lt;br&gt;`、`&lt;b&gt;`、`&lt;a&gt;`、`&lt;details&gt;`  
- **当前实例**：已有 1 条 info banner（英文、仅写 reasoning xhigh），**需替换为成套中文指引**

**局限**：不能按「当前选中模型」切换内容；适合 **总览 + 常驻提醒**，不适合「仅选 Deep Research 时显示」。

### 2.2 Prompt Suggestions（首页空对话示例）

- **配置**：同一 General 区域或 `ui.prompt_suggestions`（当前实例 **为空**）  
- **API 导出字段**：`ui.prompt_suggestions`（via `GET /api/v1/configs/export`）  
- **展示**：新对话空状态下的 **可点示例**（如「查今日 AI 新闻」「画一张产品图」）  
- **价值**：用 **示例隐式教**「快搜用 Sonar」「作图换模型」

### 2.3 模型 Description（模型下拉旁）

- **配置**：Admin → Models → 单模型 **Description**，或 `meta.description`  
- **展示**：选模型时/模型列表副文案  
- **价值**：**按模型**写「快搜 / 深度 / 作图 / 聊天」专用一句话（含 Deep 等待时间）  
- **注意**：`POST /api/v1/models/model/update` 部分字段曾 500；**Admin UI 手改** 为退路

### 2.4 Pending User Overlay（仅待审核用户）

- **字段**：`ui.pending_user_overlay_title` / `content`  
- **当前**：`DEFAULT_USER_ROLE=pending` 时可用；正式用户 **看不到**  
- **用途**：新用户首次登录的 **全屏指引**（可选）

### 2.5 其他（次优先 / 不首选）

| 载体 | 说明 |
|------|------|
| Response watermark | 每条回复底部小字，易烦，仅放一句极短提示 |
| 置顶模型显示名 | 把「Sonar Pro Search」改成「快搜 · Sonar」等（rename API 若不可用则 Admin UI） |
| Filter / 自定义前端 | 过重，违背简约 |

---

## 3. 建议的 Banner 套装（草案 HTML，确认后可 POST）

**策略**：2 条 **常驻简版**（可关闭）+ 0～1 条 **详情**（`details` 折叠）。  
替换现有 reasoning 单条英文 banner（`id` 换新以免用户已 dismiss 的旧条仍残留逻辑混乱）。

### Banner A — 总览（`info`，dismissible）

- **id**：`usage-guide-overview-v1`  
- **title**：`用哪个模型？`  
- **content**（HTML 草案）：

```html
<b>聊天</b> Sol Pro / Opus · <b>快搜</b> Sonar Pro Search · <b>深度研报</b> Sonar Deep Research · <b>作图</b> 先换 Banana Pro / GPT Image 2<br>
日常闲聊不要用 Sonar；画图不要在聊天模型里描述画面。
```

### Banner B — Reasoning（`warning`，dismissible）— **替换现有 xhigh 条**

- **id**：`usage-reasoning-v1`  
- **title**：`复杂问题请提高推理强度`  
- **content**：

```html
输入框旁 <b>设置（滑块）</b> → <b>Valves</b> → <b>Reasoning depth</b>：简单题用 low/medium，多步逻辑、长代码、难题用 <b>high / xhigh</b>。低档更快，高档更深。
```

### Banner C — 深度研报（`warning`，dismissible）

- **id**：`usage-deep-research-v1`  
- **title**：`深度研报需要等待`  
- **content**：

```html
选择 <b>Sonar Deep Research</b> 后，通常需 <b>2～10 分钟</b> 联网整理。请保持页面打开，勿刷新或换模型。
```

### Banner D — 可选折叠详情（`info`，dismissible）

- **id**：`usage-details-v1`  
- **content**：

```html
<b>快速对照</b><br>
<details><summary>展开</summary>
聊天：GPT-5.6 Sol Pro 或 Claude Opus 5<br>
快搜：Perplexity Sonar Pro Search<br>
深度：Perplexity Sonar Deep Research（2～10 分钟）<br>
作图：Google Nano Banana Pro（主）/ OpenAI GPT Image 2<br>
连续改图可能轻微漂移；附件分析可开 Direct Uploads。
</details>
```

**不建议** 再开第四条常驻 error 级 banner，避免告警疲劳。

---

## 4. Prompt Suggestions 草案（首页可点示例）

| title（数组，OWUI 格式） | content（发送内容） | 教会用户 |
|--------------------------|---------------------|----------|
| `["快搜","今日 AI 要闻"]` | 用一句话总结今天 AI 领域最重要的一条新闻，并附来源。 | 快搜场景 |
| `["深度研报","行业分析"]` | 写一份关于 ___ 的行业简报，含数据与引用来源。 | 深度档 |
| `["作图","产品渲染"]` | （用户先手动选 Banana Pro）一张极简风格的产品渲染图… | 换模型作画 |
| `["聊天","复杂推理"]` | （用户选 Sol Pro + high reasoning）… | 推理档 |

格式以 OWUI `prompt_suggestions` 为准（通常为 `title: string[]`, `content: string`）。

---

## 5. 模型 Description 一行文案（Admin Models）

| 模型显示名 | description 草案 |
|------------|------------------|
| Perplexity: Sonar Pro Search | 快搜：最新资讯与短答，带引用。日常聊天请用 Sol Pro / Opus。 |
| Perplexity: Sonar Deep Research | 深度研报：多源长文，约 2～10 分钟，请勿刷新。 |
| OpenAI: GPT-5.6 Sol Pro | 默认对话与复杂推理。难题请在设置里提高 Reasoning depth。 |
| Anthropic: Claude Opus 5 | 强推理与长文；不联网，查新闻请用 Sonar Pro Search。 |
| Google: Nano Banana Pro | 作图主入口；连续编辑可能轻微漂移。 |
| OpenAI: GPT Image 2 | 作图备选；适合 OpenAI 图像风格。 |

---

## 6. 落地步骤（确认后执行）

### 阶段 UI-1 — Banners（**建议先做**）

1. Admin → General → Banners：**删除/替换** 现有英文 reasoning 条  
2. 按 §3 写入 A+B+C（+ 可选 D）  
3. 或 API：`POST /api/v1/configs/banners` with `{"banners": [...]}`  
4. 普通账号登录目测：顶部是否过长、手机窄屏是否可读  

### 阶段 UI-2 — Prompt Suggestions

1. 在 General 或 configs export/import 写入 `ui.prompt_suggestions`  
2. 空对话首页点示例，确认跳到正确用法  

### 阶段 UI-3 — 模型 Description

1. Admin Models 为置顶 6 个模型填 description（§5）  
2. 模型下拉检查副文案是否显示  

### 阶段 UI-4 — 可选

- Pending overlay：待审核用户 onboarding  
- 默认新对话模型改为 Sol Pro（与指引一致，另项配置）  

**脚本化**：可新增 `scripts/apply_ui_guidance_banners.py`（只改 banners，不动 Pipe valves）。

---

## 7. 与现有实例状态

| 项 | 当前 | 目标 |
|----|------|------|
| Banners | 1 条英文 reasoning 提示 | §3 中文套装 |
| prompt_suggestions | 空 | §4 四条示例 |
| 模型 description | 多为 null | §5 置顶模型 |
| Integrations | 方案 A 已隐藏 Web Tools 等 | Banners **不写** 引导打开 |

---

## 8. 待用户确认

- [ ] Banner 套装：A+B+C 是否足够？是否要 D 折叠详情？  
- [ ] Banner B 是否保留 **xhigh** 字样（与当前 UI 一致）？  
- [ ] Prompt Suggestions 是否一起做（UI-2）？  
- [ ] 模型 description 是否一起做（UI-3）？  
- [ ] 确认后是否 **由我直接 POST API 写入**（无需你手抄 Admin）？  

**确认前不修改实例 Banners / Suggestions / Description。**

---

## 9. 附录：仓库文档的定位

`docs/` 内文稿仅供 **Admin 维护者** 备份与 PR 记录；**普通用户应以界面 Banners + 首页示例为准**。
