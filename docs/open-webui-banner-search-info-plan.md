# Banner info：五句 Search 指引 + 句首小图标

> **状态**：**待确认文案与图标档**。未确认不改实例 Banner / Description / `stack_contract`。  
> **日期**：2026-09-05  
> **现网**：一条 `usage-guide-v4`（`type: info`，不可 dismiss）；空 chips。

关联：`docs/SPEC.md` UX-2；`scripts/apply_ui_guidance_banners.py`。

---

## 0. 范围

只改顶栏 info。正文以你这次粘贴为准（五句）。相对现网：

- **删**：`Sonar remains Quick Search / Deep Research.`
- **改**：第一句改成 Grok / Sol / Claude / Gemini 会搜会读页
- **加**：`GitHub: use a github.com URL, not api.github.com.`
- **留**：图像只走图像模型；Valves；**System Prompt 会影响图像与 Perplexity sonar**
- **加**：每个句子开头一个小图标

不改：四格 Sonar、模型 Description、Filter / Pipe / chips。不写 Integrations。英文。换 id `usage-guide-v5`（否则已看过 v4 的人可能看不到更新）。

现网 apply 脚本会把源码里的换行收成 `<br>`。五句各占一行，图标才像清单，不会挤成一段。

现网 `verify()` 只允许粗体 HTML（禁 `style` / `div` / `span`）。图标必须能活在这个约束里。

---

## 1. 锁定正文（五句）

1. Grok, Sol, Claude, and Gemini can search the web and read pages.
2. GitHub: use a github.com URL, not api.github.com.
3. Images only on an image model.
4. Reasoning depth: Input box → Valves.
5. Settings → General → System Prompt may also affect image models and Perplexity sonar.

---

## 2. 图标两档

### 顶级 — 图床 / `<img>` 小图

每句前嵌 16px 图。看起来更「产品」。代价：Banner 契约要放行 `<img>`；图要稳定 HTTPS；暗色主题还要两套或 SVG；重建多一个依赖。**不建议**为这五句上图床。

### 简单稳 — Unicode 表情（建议）

不增 HTML 标签，暗色主题能用，现网 verify 只需改 needle、仍禁 `div`/`span`/`style`。

| 句 | 图标 | 含义 |
|----|------|------|
| 1 Search | 🔍 | 会搜会读页 |
| 2 GitHub | 🔗 | 用网页链接，不用 API |
| 3 Images | 🖼️ | 先切图像模型 |
| 4 Reasoning | 🎛️ | Valves |
| 5 System Prompt | 📝 | 设置里的系统提示 |

建议 HTML（换行 → `<br>`）：

```html
🔍 <b>Grok, Sol, Claude, and Gemini can search the web and read pages.</b>
🔗 GitHub: use a github.com URL, not api.github.com.
🖼️ Images only on an image model.
🎛️ <b>Reasoning depth</b>: Input box → <b>Valves</b>.
📝 <b>Settings → General → System Prompt</b> may also affect image models and Perplexity sonar.
```

图标与句子之间一个空格。不用 GitHub 官方 Logo。

---

## 3. 落地（确认后才跑）

1. `apply_ui_guidance_banners.py`：id `usage-guide-v5`；写入上面 HTML；`verify()` needle 改为五句 + 五个图标字符；断言 **没有** `Sonar remains Quick Search`；**保留** `Perplexity sonar`（第 5 句）。
2. `stack_contract.py`：`BANNER_IDS = ["usage-guide-v5"]`。
3. `python3 scripts/apply_ui_guidance_banners.py`（只 Banner + 空 chips + 现有 Description）。
4. `verify_stack.py` 全绿。
5. 改 SPEC UX-2、VERSIONS、rebuild-archive Banner 原文、AGENTS.md 的 v4。

回滚：写回 `usage-guide-v4` 再 apply。禁止空 `models/sync`、禁止改 Pipe valves。

---

## 4. 请确认

回复即可施工：

1. **五句 + 上表五个表情 + v5**（建议）
2. 换某几个表情（写出要换哪句）
3. 改走 `<img>` 小图（更重，须另定图源）

未点头不改 info。
