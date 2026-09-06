# Astra 进 ST-14 薄 Web Search

> **状态**：**已确认执行**（2026-09-06）。public 已 23；本波只补搜索。  
> **现网**：OWUI 0.11.3；Pipe `f797e92d6d3f`；Banner 起点 `usage-guide-v5`。  
> **确认**：先 23 public 已落地；现补 Astra / Astra Pro 挂薄 Web Search。不上 Controller、不加 Filter 指引、不抬 `$0.05`。

关联：`docs/open-webui-text-web-search-plan.md`（ST-14 机制）、`docs/SPEC.md` UX-3 / ST-14。

---

## 0. 目标

Astra 与 Astra Pro 和现有 7 个文本模型同一套体验：Integrations 有 **Web Search**、新对话 default-on、模型可 Search + Fetch。Banner 第一句带上 Astra，避免能搜却不写、或没挂上却宣传。

**不是**：EVAL-B 全量重跑、Search Controller、改 public 名单、重开 broad Web Tools。

## 1. 两档（本波选简单档）

| 档 | 做什么 | 不做什么 |
|----|--------|----------|
| **简单稳定（本波）** | 扩 allowlist → apply final → Astra 各 1 次 Search + 1 次 Fetch 烟雾 → Banner v6 | 不上 Controller / 指引 / 抬价门 |
| **顶级（Later，另确认）** | 对 Astra 跑一小截 EVAL-B（隐含时效 / 误搜 / HTML Fetch） | 不绑进本波；不过不阻塞挂上 |

OpenRouter 页：Astra / Astra Pro **支持 `tools`**，并标了 Web Search 计价。机制与现网 7 模型相同（Pipe `server_tools`）。若烟雾出现 `No endpoints found that support tool use`，**剥回 Astra 附件、Banner 不改**，再另报。

## 2. 分步

| 步 | 动作 | 过门 |
|----|------|------|
| **A1** | `TEXT_WEB_SEARCH_MODEL_IDS` + Filter `ALLOWLIST_SUFFIXES` 加入两个 Astra id；单测 | `python3 scripts/test_text_web_search_filter.py` 绿 |
| **A2** | `python3 scripts/apply_text_web_search.py --mode final`（upsert Filter + 9 模型 default-on） | `verify_text_web_search.py --mode final`：9 挂、其余不挂 |
| **A3** | **只**对 Astra / Astra Pro 跑现有 Search + Fetch 烟雾（不重跑原 7，省账单） | 各 200；有 `web_search` / Fetch 证据；无 tool-use 404 |
| **A4** | Banner → **一条** `usage-guide-v6`：第一句改为 `Grok, Sol, Claude, Gemini, and Astra can search the web and read pages`；其余四句不动。补 Astra Description | `apply_ui_guidance_banners.py` + `verify_stack.py` 全绿 |
| **B** | EVAL-B 子集 | **另确认**，本波不做 |

A3 失败则停在 A2 回滚 Astra 附件，不进 A4。

## 3. 不改

- Pipe valves / `WEBUI_SECRET_KEY` / `openai.api_configs`
- public 23、ST-14 循环门 `$0.05` / `step_count=8`
- 原 7 个文本的挂载与 default-on
- Controller、Filter 内指引

## 4. 回滚

把两个 Astra id 移出 `TEXT_WEB_SEARCH_MODEL_IDS` 与 `ALLOWLIST_SUFFIXES`，再 `apply_text_web_search.py --mode final`，Banner 留 v5。
