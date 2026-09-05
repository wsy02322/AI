# Banner info：去掉 Perplexity，精简补 Search

> **状态**：**待确认**。未确认不改实例 Banner / Description / `stack_contract`。  
> **日期**：2026-09-05  
> **现网**：一条 `usage-guide-v4`（`type: info`，不可 dismiss）；空 chips；ST-14 质量已收口。

关联：`docs/SPEC.md` UX-2；`scripts/apply_ui_guidance_banners.py`；`docs/open-webui-text-web-search-eval-b-results.md`。

---

## 0. 改什么、不改什么

**只改顶栏 info Banner**（用户说的 info）。现网原文：

> Selected chat models can search the web automatically. **Sonar remains Quick Search / Deep Research.** Images only on an image model. Reasoning depth: Input box → Valves. Settings → General → System Prompt may also affect image models and **Perplexity sonar**.

要去掉的就是加粗两句 Perplexity / Sonar。要补的是已收口的 Search 用法（谁能搜、GitHub 怎么贴链接）。

**不改（除非你另点）：**

- 置顶四格仍有 Sonar Pro / Deep Research（UX-1）
- 两档 Sonar 的 **模型 Description**（那是 picker 卡片，不是 info 条）
- 薄 Filter / 挂载 / `$0.05` / Pipe / chips
- 不写 Integrations（控件对用户仍偏藏）
- 不写中文（Banner 契约：英文）

---

## 1. 两档文案（先选再施工）

换 id → `usage-guide-v5`，用户会再看到一次顶栏。继续用 v4 只改字，已看过的人可能看不到更新。

### 顶级 — 把 Search 讲清楚（仍无 Perplexity）

```html
<b>Grok, Sol, Claude, and Gemini search the web and can open pages.</b>
GitHub: paste a <b>github.com</b> page. Do not paste <b>api.github.com</b> into Claude — it cannot read that API; Grok, Sol, and Gemini can.
Images only on an image model.
<b>Reasoning depth</b>: Input box → <b>Valves</b>.
```

长处：GitHub API 这条实测缺口写进主路径，Claude 用户少踩坑。  
短处：比现在长；点名家族，以后加模型要改 Banner。

### 简单稳 — 更短（建议，若你要「精简」）

```html
<b>Grok, Sol, Claude, and Gemini can search the web and read pages.</b>
GitHub: use a github.com URL, not api.github.com.
Images only on an image model.
<b>Reasoning depth</b>: Input box → <b>Valves</b>.
```

长处：去掉全部 Perplexity；Search 一句 + GitHub 一句；Valves / 图像保留。  
短处：没写「Claude 才读不了 API」——用户可能以为所有模型都不能贴 API。

System Prompt 那句（图像 + Perplexity）两档都删。图像模型 Description 已在说「先切图像模型」。

---

## 2. 落地（确认后才跑）

1. `scripts/apply_ui_guidance_banners.py`：`BANNERS[0].id = usage-guide-v5`，写入选定英文；`verify()` 的 needle 改成新句子，**删除** `Sonar remains…` / `Perplexity sonar` 断言。
2. `scripts/stack_contract.py`：`BANNER_IDS = ["usage-guide-v5"]`。
3. `python3 scripts/apply_ui_guidance_banners.py`（只写 Banner + 空 chips + 现有 Description；**不**动 Filter）。
4. `python3 scripts/verify_stack.py` 全绿。
5. 更新 `docs/SPEC.md` UX-2、`docs/VERSIONS.md`、`docs/open-webui-rebuild-archive.md` Banner 原文、`AGENTS.md` 里的 v4 字样。

回滚：脚本改回 `usage-guide-v4` 旧文案再 apply。禁止空 `models/sync`、禁止改 Pipe valves。

---

## 3. 请确认

回复三选一即可：

1. **简单稳文案 + v5**（建议）
2. **顶级文案 + v5**
3. 只要去 Perplexity、**不写 GitHub**（最短，不教 API 坑）

未点头不改 info。
