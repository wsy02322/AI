# Banner info：五句 Search 指引 + 句首小图标

> **状态**：**已确认并执行**（2026-09-05）。现网一条 `usage-guide-v5`。  
> **现网**：`type: info`，不可 dismiss；空 chips；五句同一段。

关联：`docs/SPEC.md` UX-2；`scripts/apply_ui_guidance_banners.py`。

锁定正文（句首图标，不分行）：

`🔍 Grok, Sol, Claude, and Gemini can search the web and read pages. 🔗 GitHub: use a github.com URL, not api.github.com. 🖼️ Images only on an image model. 🧠 Reasoning depth: Input box → Valves. 📝 Settings → General → System Prompt may also affect image models and Perplexity sonar.`

Reasoning 用 🧠。回滚：把脚本改回 `usage-guide-v4` 再 apply。
