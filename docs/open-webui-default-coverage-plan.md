# 默认覆盖：能力 / 拒绝类，不是死名单

> **状态**：**C0 已确认**（2026-09-07）。原则锁定，**未执行**。不改实例 / Pipe / Filter / Banner / public。  
> **已锁**：覆盖 = 合格类 + 未来同类；压缩 T1 无模型名单；「所有」≠ 图像/Sonar/OR 全库；选品名单保留。C1（T1 按全请求设计）随 C0 **一并锁定**。  
> **未锁**：C2 搜索改 deny、C3 Banner、C4 写入 AGENTS、费用 T0。  
> **下一问**：费用 plan **D1**（是否跑 T0 只读探针）。

关联：`docs/open-webui-search-cost-plan.md`（压缩无名单）；`docs/SPEC.md` UX-3 / UX-4 / ST-1 / ST-14；`scripts/text_web_search_filter.py`（现网 = **allowlist 9 个** + deny markers）。

---

## 0. 结论先看

**原则对，范围要收一句。**

该默认覆盖的是：**所有适用这类能力的模型，以及以后新进 picker 的同类**。不是：

- OpenRouter / Pipe catalog 里每一条（会变成 466 public，宪法 Don't）；
- 图像 / 视频 / Sonar（灌 tools 会 404，ST-1）；
- 必须按家族特化的补丁（ST-11 只对 Anthropic thinking）。

「死名单」的害处已经发生过：Astra 一度不在 ST-14 allowlist → 不能搜；后来挂上又撞 runtime cache。**新模型默认漏掉**，比多写两行 deny 更伤顶级档。

| 档 | 做什么 | 复杂度 | 质量 |
|----|--------|--------|------|
| **顶级 C** | 功能按 **拒绝类 / capability** 覆盖；压缩在 Pipe **无名单**；搜索去掉 allowlist，合格文本（含中国三只、以后新 public 文本）自动挂；Banner 改成类描述 | 中：Filter + apply 脚本 + 契约从「9 个 id」改成「合格则挂」 | 自动搜索覆盖变完整；图像/Sonar 仍不灌 tools |
| **略简 C−** | **只**把费用压缩做成无名单（所有请求，没有 tool 页就 no-op）。搜索本波仍 9 个；apply catalog 时加一条「新 public 文本提醒挂 Search」，不自动改 Filter | 低：T1 设计约束，几乎不增复杂度 | 压缩对所有模型生效；新文本仍可能漏搜，直到有人跑 apply |

S1 关默认搜索、Filter 改 `is_global=true`（图像聊天也出现 Web Search 开关）：**不进主线**。

**C0 已同意。** 不等于批准改 Filter，也不等于批准 T0 探针。下一轮只问费用 **D1**。

---

## 1. 「所有模型」该怎么读

现网「模型库」有三层，混为一谈会施工错：

| 层 | 现在 | 能不能「全部覆盖某功能」 |
|----|------|--------------------------|
| **A. picker / public** | 23，含文本 + 图像 + 两档 Sonar | 覆盖 **合格类**，不是 23 个都搜 |
| **B. Pipe catalog** | 多于 23；未确认家族 inactive | 新家族 **未确认仍不 active**（UX-4）。一旦确认进 public，合格功能应自动跟上 |
| **C. OpenRouter 全库** | 几百条 | **不要**。不是本原则 |

用户说的「模型库里所有 + 后续新增」，正确落地是：

**A 里所有合格模型 + 以后新进 A 的合格模型。**  
不合格类永远拒绝。名单可以变（新图像家族加 deny / 靠 `image_output`），但规则是类，不是「Grok、Sol、Opus…」这种写死 id。

现网 public 文本里 **还没挂 Search** 的：DeepSeek V4 Pro、Kimi K3、Qwen 3.8 Max。按本原则，它们应被覆盖（另轮确认，先烟雾）。Ling / Muse / GLM 等 **未确认不 active**，不因为本原则偷偷 public。

---

## 2. 现网哪些是死名单，哪些已经是类

| 功能 | 现在 | 漏新模型？ | 不明显加复杂就能改成类？ |
|------|------|------------|--------------------------|
| ST-14 薄 Search | Filter **allowlist 9 id** + 每模型 `filterIds` | **会。** Astra 已漏过一次 | 能。inlet 已有 deny；再删 allowlist + apply 时按类挂 |
| 费用压缩 T1（未做） | 若写成 9 个 id 就会再漏 | 会 | **应一开始就无名单**（有旧 Search/Fetch 页就压） |
| 跨轮预算 T2（未做） | 若按模型开 | 会 | 有 `server_tools` 就记账 |
| 图像 / Sonar Guard | global + 类 / capability | 新图像靠 marker + `image_output` | 已是类；新家族名要进 deny 或靠 capability |
| ST-10 跨模型密文重试 | Pipe 按错误文案 | 否 | 保持全请求 |
| `middle-out` | `/chat/completions` 全路径 | 否 | 保持 |
| ST-11 Fable thinking | Anthropic 形态 | 故意只打这一家 | **保持特化**，不是名单病 |
| Banner v6 | 点名 Grok/Sol/Claude/Gemini/Astra | 新文本不在句子里 | 改成 “Text models can search…” |
| picker / public | `PUBLIC_MODEL_IDS` | 这是 **选品**，不是功能开关 | 保持名单。新家族仍要确认才 active |
| Code Interpreter 只留 Sol Pro / Opus | 产品选择 | 是 | **不要**自动给所有文本（Sonar/图像必须关） |

死名单只该留在 **选品**（谁进 picker）和 **家族特化 bugfix**（ST-11）。功能通道用死 id，是 Astra 漏搜的同类结构。

---

## 3. 为什么搜索不能「global 给每一个模型」

薄 Filter 改 `is_global=true` 最省事：新模型不用挂 `filterIds`。代价：

- 图像 / Sonar 聊天的 Integrations 可能出现 **Web Search** 开关（ST-14 当初做成非 global，就是为了这个）；
- inlet 必须 100% deny，稍漏一个新图像 id 就会灌 tools → 404（ST-1）；
- 和「不重开 broad Web Tools」的观感叠在一起。

**略简且稳：Filter 保持非 global。** 两处同时改：

1. **inlet 删 allowlist**，只认 deny 类（id marker + `image_output` / `video_generation`）。挂上的模型即使不在旧 9 个 suffix 里也会搜。
2. **每次 catalog apply / public 恢复** 按类挂：`public ∩ 非 deny ∩ 非 Sonar` → attach + default-on + `refresh=true`。新进 public 的文本自动有 Search。

复杂度：改 Filter 十几行 + `attach_models` 的 wanted 从常数列表改成「算合格集」。比维护 9 个 id 还简单。

顶级补强（可后做）：Pipe 在 `pipes()` / 模型同步后也按类补 `filterIds`，避免有人只改 Admin、没跑脚本。这比 Filter global 重，**D 轮再选**。

---

## 4. 质量不降

1. 图像 / Sonar / 视频 **永远不**收到 Search tools（ST-1）。这是拒绝类，不是「歧视新模型」。
2. 合格文本 **默认仍会搜**，误搜不升。中国三只、以后新文本：先 **Search+Fetch 烟雾**，不过全套 EVAL-B（账单和复杂度不划算）。烟雾红则那只先不 default-on，仍 attach。
3. 压缩：没有旧工具页 = no-op，不影响出图 / Sonar / 短闲聊。
4. 不把「全覆盖」理解成全 public 图像也能搜。
5. ST-11 继续只打 Anthropic。把 Fable 补丁套到 Grok 是加复杂度、降稳定性。

---

## 5. 和其他功能怎么套同一原则

以后加能力时，默认问一句：**不做名单，新模型会不会自动有？**

| 决策 | 默认 |
|------|------|
| 变换的是请求体 / 工具结果 / 错误重试 | **全请求**，用拒绝类早退 |
| 变换依赖某家协议（Anthropic thinking、Images API 路由） | **特化留下**，写清家族探针 |
| 谁出现在 picker | **仍要确认名单**（UX-4） |
| 谁出现在聊天 Integrations 开关 | **非 global** + 按类 attach，避免图像条上多一个 Search |

费用压缩属于第一行：一开始就不要 `if model in TEXT_WEB_SEARCH_MODEL_IDS`。

---

## 6. 分轮确认

| 轮 | 只问 | 点头之后 | 不点头 |
|----|------|----------|--------|
| **C0** | 原则：覆盖 = **合格类 + 未来同类**；压缩无名单；「所有」≠ 图像/Sonar/OR 全库；选品名单保留 | **已确认 2026-09-07** | — |
| **C1** | T1 是否按「全请求、无名单」设计 | **随 C0 锁定：是** | — |
| **C2** | 搜索是否本波从 allowlist → **deny + apply 按类挂**（含 DeepSeek/Kimi/Qwen） | 另开 Filter 改动；中国三只先烟雾 | 搜索仍 9 个；只保证压缩全覆盖 |
| **C3** | Banner 是否改成类描述（不点名家族） | v7 文案另确认 | Banner 可暂留 v6 |
| **C4** | 是否写进 SPEC / `AGENTS.md` 作以后功能默认 | 改契约条文 | 只留本 plan |

C0 **不等于** C2，也不等于费用 T0。下一问见费用 plan **D1**。中国三只未排除，仍等 C2。

---

## 7. 落地（仅 C2 通过后才动 Filter；C1 约束 T1）

### 压缩（费用 plan T1）

- Pipe 出站：见到旧 `web_search` / `web_fetch` 整页就压，**不读模型 id 名单**。
- 图像 / Sonar 无此类 item → no-op。
- 新文本以后若挂上 Search，自动吃压缩。

### 搜索改类覆盖（C2）

1. Filter inlet：删 `ALLOWLIST_SUFFIXES` 判断；deny 保留并补测。
2. `attach_models` 的 wanted = 现网 public 里非 deny 的文本（含中国三只，除非 C0 声明排除）。
3. 必 `GET /api/models?refresh=true`。
4. 中国三只 + 任一新合格模型：各 1 条 Search、1 条 Fetch 烟雾；红则那只 default-off。
5. `TEXT_WEB_SEARCH_MODEL_IDS` 改成「推导合格集」或 verify 时现场算，不再手写 9 个当唯一真相。
6. 不改 Filter `is_global`。不重开 `openrouter_web_tools`。

回滚：allowlist 加回；挂载回到 9 个；中国三只剥 Filter。

---

## 8. 明确不做

- 未确认改实例。
- 466 / 全 catalog public。
- 给 Sonar / 图像 / 视频挂 Search 或 broad tools。
- Filter `is_global=true` 当本波方案。
- 未确认把 Ling / Muse / GLM 等新家族变 active。
- 把 ST-11 改成「所有模型」。
- 用死 id 名单实现 T1 压缩。

---

## 9. 验收（相应轮落地后）

1. 新加一只合格 public 文本（或用中国三只当「以前漏掉的」）：不改 Filter 源码里的 id 列表，只跑 apply，即可搜。
2. 新图像 / Sonar：无 Search tools，无 404。
3. 压缩：Grok 续聊和 Astra 续聊同样压旧页；出图请求体积不明显变。
4. `verify_stack` / `verify_text_web_search` 断言跟「合格集」走，不写死 9。
