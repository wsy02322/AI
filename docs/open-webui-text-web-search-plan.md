# 指定文本模型联网搜索（Agentic Search）

> **状态**：**待确认，未实施**。本文件和 readiness 探针是前提工作；生产仍只用两档 Sonar 搜索。  
> **日期**：2026-09-05  
> **现网**：OWUI 0.11.3；Pipe SHA `f797e92d6d3f`；OWUI Web Search 关闭；`openrouter_web_tools` 停用。  
> **推荐档位**：WS-A——复用现有 Pipe 的 OpenRouter server-tools 通道，增加一个只含 Search + Fetch 的薄 Filter，只挂指定文本模型；Sonar Deep Research 保留。  
> **确认门**：未收到明确确认前，不激活/新建 Filter，不改 Pipe valves、模型 metadata、Banner、SPEC 或实例。

关联：`docs/SPEC.md` UX-1/UX-3、ST-1/ST-2；`docs/open-webui-rebuild-archive.md` §3.4/§8；图像错误模式见 `docs/open-webui-openrouter-image-continuity-plan.md`。

---

## 0. 目标与结论

### 本波目标

1. Grok、Sol、Claude、Gemini 的指定文本模型保持原模型身份，同时能自动决定是否搜索、可多次搜索并读取完整页面。
2. 用户可在聊天 Integrations 中开关一个简洁的 **Web Search**；指定模型的新对话默认开，模型可选择 0～N 次调用。
3. Sonar Quick Search / Deep Research 原样保留，不扩/缩 21 public，不新增模型家族。
4. Sonar、9 个纯图像模型、视频模型永远不收到该 Filter 的 tools。
5. 不启用 OWUI 原生 Web Search，不用已废弃的 `:online` / `plugins.web`，不启用广义 `openrouter_web_tools`。

### 能力边界

WS-A 可接近 ChatGPT 的即时 Search：模型自主查找、追问、抓整页、引用来源。它**不是**完整 ChatGPT Deep Research：没有独立后台研究任务、进度侧栏、证据账本、文件+代码联合分析和长报告恢复。深度报告继续由现有 Sonar Deep Research 承担。

若 WS-A + Sonar Deep Research 实测仍明显落后，下一档才是单独确认的 WS-R：GPT Researcher（较稳）或 LangChain Open Deep Research（上限高、复杂）作为后端，仍接进现有 OWUI，不安装第二前端。本波不搭车部署。

---

## 1. 非变更前提核查（2026-09-05）

已执行 `VERIFY_SMOKE=0 python3 scripts/verify_stack.py` 与管理 API 检查，未发模型推理请求、未提交任何配置更新。第一次检查调用了 runtime model catalog；该入口可能触发 manifold `pipes()`，所以后续 readiness 探针不再枚举任何 model catalog，只按 id 读取本计划涉及的具体模型记录。不能把“HTTP GET”错误等同于“绝无间接行为”。

| 检查 | 结果 | 含义 |
|------|------|------|
| OWUI / Pipe | 0.11.3；Pipe `f797e92d6d3f` | 不换镜像、不升级 Pipe |
| 当前搜索 | OWUI native off；`openrouter_web_tools` inactive / non-global | 生产仍是旧基线 |
| Pipe server tools | 有 `openrouter:web_search`、`openrouter:web_fetch`、citation card、`stop_server_tools_when` | 无需第二套 Pipe / 搜索服务 / key |
| 已安装 broad Filter | 新式 `server_tools`，支持 Search + Fetch；Datetime 已移除；Web Fetch 默认 off | 可作为接口参考，不直接激活 |
| 图像 Guard | active + global；web Filter priority 0，image guard priority 1；会剥 `tools`、`server_tools`、cost stop | 数字更大、后执行；当前顺序能兜底 |
| Sonar Guard | active + global；priority 100 | Sonar 最后剥工具 |
| 模型 metadata | 拟定文本模型只挂 `openrouter_direct_uploads`；Sonar/图像无 Web Tools | 无历史 attachment 要清 |
| public | 21 个 public 权限正确 | 不改 public |
| runtime catalog | 首次 28，复验 26；契约应为 21 | catalog 正在漂移；实施前须先处理 retained-family 换代并恢复 21 |

最后一项不是搜索施工造成的，但 `verify_stack.py` 当前因此为 `22 ok / 1 err`。第二次检查还发现旧 `qwen.qwen3.8-max` 从 runtime picker 消失、同家族出现 `qwen.qwen3.8-max-0902`；按“保留家族跟最新 id”原则，不能只运行旧契约的 visibility 脚本硬压。落地时先核实该 replacement，必要时在一个独立提交里把 Qwen id、public grants 和契约同步到新 id，且把旧 id 加进 `RETIRED_MODEL_IDS` 以剥除遗留 `* read`；同时排除 GPT-6 Astra / Ling 等新家族。复验恰好 21 后再开始 WS-A。禁止空 `models/sync`。

可重跑的只读前置探针：

```bash
python3 scripts/probe_text_web_search_readiness.py
```

它用 POST 登录；之后只按 id 读取 Function/模型记录，不枚举 runtime 或存储 catalog，不读取 Pipe valves（避免让 `API_KEY` 进入探针内存），不激活 Function、不改 valves/模型、不发推理请求。它会报告源码接口 markers、Guard 顺序和候选模型；markers 只证明接口候选存在，不能替代 canary 的真实工具事件/引用验收。catalog 是否恰好 21 仍由确认后的 W0 `verify_stack.py` 阻断检查，readiness 不假装能无副作用地证明这点。

---

## 2. 方案审查

### WS-A — 薄 Web Search Filter（推荐）

新增一个受仓库管理的非 global、toggleable Filter：

- Function id：`openrouter_text_web_search`
- 用户名：`Web Search`
- priority：0；canary 前必须验证它早于 image guard（1）和 Sonar guard（100）执行。
- 只写现有 Pipe 接口：
  - `__metadata__["openrouter_pipe"]["server_tools"]["web_search"]`
  - `__metadata__["openrouter_pipe"]["server_tools"]["web_fetch"]`
  - `__metadata__["openrouter_pipe"]["stop_server_tools_when"]`
- 不包含 Datetime、Advisor、Subagent、Model Search、Image Generation。
- Filter 内置模型 allowlist；即使 metadata 误挂到别的模型，也会早退。
- 明确 deny Sonar、image-output、video-generation；全局 Guard 再做第二层剥离。
- `body.features.web_search=False`，防止未来误开 OWUI native 后双搜。
- 保持 `openrouter_web_tools` inactive；Pipe 的 `AUTO_INSTALL_*` / `AUTO_ATTACH_*` / `AUTO_DEFAULT_*` 全 false，避免上游刷新覆盖薄 Filter。

为什么不直接激活现成 broad Filter：它还暴露 Advisor/Subagent/Model Search，Web Fetch 默认关闭，也没有 Filter 自身 allowlist。WS-A 多一个约百行薄 Function，但搜索面更小、重建确定、不会把无关工具重新带回聊天。

### WS-B — 直接激活 broad Web Tools（略简单、明显降级）

把已有 `openrouter_web_tools` 挂到白名单并默认开，用户再手动把 Web Fetch 打开。少一个 Function，但：

- UI 暴露无关工具；
- Filter 没有自身 allowlist；
- 用户不打开 Fetch 时只拿搜索结果摘要；
- 上游 Pipe 更新可能重写 Filter；
- 更容易重现“工具灌到不支持模型”的事故。

不推荐选 WS-B。

### WS-R — 开源 Deep Research 后端（更高上限，另确认）

GPT Researcher 或 LangChain Open Deep Research 可做规划、并行子问题、反思和长报告。要达到官网级产品，还要异步任务、进度流、证据账本、抓取防注入、恢复/导出和专门验收。这是独立后端与入口行为变更，不是本波 Search Filter 的附赠项。

不做 WS-R 的代价：Deep Research 继续依赖 Sonar，指定文本模型只能做一次请求内的 agentic browsing。做 WS-R 的代价：新增容器/检索后端/成本治理，维护面明显扩大。

---

## 3. 首波模型 allowlist

首波只挂 OpenRouter `engine=auto` 可优先走厂商原生搜索的文本模型：

| 用户模型 | 完整 OWUI id |
|----------|--------------|
| Grok 4.6 | `open_webui_openrouter_integration.x-ai.grok-4.6` |
| GPT-5.6 Sol Pro | `open_webui_openrouter_integration.openai.gpt-5.6-sol-pro` |
| GPT-5.6 Sol | `open_webui_openrouter_integration.openai.gpt-5.6-sol` |
| Claude Opus 5 | `open_webui_openrouter_integration.anthropic.claude-opus-5` |
| Claude Fable 5.1 | `open_webui_openrouter_integration.anthropic.claude-fable-5.1` |
| Gemini 3.1 Pro Preview | `open_webui_openrouter_integration.google.gemini-3.1-pro-preview` |
| Gemini 3.8 Flash | `open_webui_openrouter_integration.google.gemini-3.8-flash` |

首波不挂：

- DeepSeek V4 Pro、Kimi K3、Qwen 3.8 Max：OpenRouter `auto` 会回落到 Exa；等首波稳定后可单独做兼容波，不影响它们普通聊天。
- 两档 Sonar：自身即搜索模型，额外 tools 会重复并曾 404。
- 9 个纯图像模型和全部视频模型：硬禁止。

这不改变 picker/public，只改变 7 个现有文本模型的 `filterIds` / `defaultFilterIds`。

---

## 4. 默认参数

| 项 | 拟定值 | 理由 |
|----|--------|------|
| Filter | 指定 7 模型 attached + default-on；用户可关 | 最接近 ChatGPT 自动搜索；普通问题模型可选择 0 次 |
| Search engine | `auto` | 优先厂商原生；不支持才回落 Exa |
| Search results | 每次 5；`max_uses=3`；总计最多 15 | Anthropic 可硬限 3 次；其他 native provider 可能忽略 `max_uses` |
| Search context | `medium` | 质量/成本中点 |
| Web Fetch | **默认开** | 能读整页，不把摘要注入冒充浏览 |
| Fetch engine | `auto` | 能原生则原生，否则 OpenRouter 选择 |
| Fetch uses | 最多 5 | 防无限追链接 |
| Fetch content | 每页最多约 12k tokens | 足够文档/PDF主体，避免撑爆上下文 |
| Loop stop | `step_count_is=8` 或 server-tools 成本达 `$0.05` | 两条件 OR；任一触发即停止工具循环 |
| OWUI native | off | 防双搜、双计费、引用来源混杂 |
| Datetime/Advisor/Subagent | 不提供 | 本波只做搜索 |

本方案不同时发送 `max_tool_calls`：OpenRouter 的 `stop_server_tools_when` 会覆盖它。`web_search.max_uses=3` 保留为工具级辅助限制，但 native Search 只有 Anthropic 保证接受，OpenAI/Google/xAI 可能忽略。跨 provider 的硬上限由 Filter 写入：

```json
[
  {"type": "step_count_is", "step_count": 8},
  {"type": "max_cost", "max_cost_in_dollars": 0.05}
]
```

两个条件按 OR 生效；触发后由 OpenRouter 关闭工具并完成最终自然语言回答。

---

## 5. 落地波次（确认后才执行）

### W0 — 恢复可判定基线

1. `python3 scripts/verify_stack.py` 记录现状。
2. 若 `qwen3.8-max-0902` 仍是旧 Qwen 的 catalog replacement：先更新 retained-family 最新 id 契约和 grants，再运行 `apply_model_catalog_visibility.py`；GPT-6 Astra / Ling 等新家族保持排除。若不是 replacement，则保留旧 id并查清 runtime 缺失原因。禁止 sync。
3. 再跑 `verify_stack.py`，必须全绿后才进 W1。
4. 导出/记录：
   - 本次会修改的 Function/模型/Banner 字段（Pipe valves 本方案不改）
   - `openrouter_web_tools` / 三 Guard 状态与指纹
   - 21 模型 metadata + `access_grants`
5. `fix_sonar_tool_guard.py` 不是本方案执行/回滚入口；其旧版 partial model update 已在本计划分支修成完整保留 `access_grants`/metadata，但本波仍只使用新的幂等 apply/rollback。

### W1 — 先备齐实现、验证和回滚

1. 新增仓库脚本 `apply_text_web_search.py`、`rollback_text_web_search.py`、`verify_text_web_search.py` 和 Filter 源码/模板；脚本必须可重复执行。
2. 创建/更新 `openrouter_text_web_search`，先 `is_active=false`、`is_global=false`。
3. Filter 静态单测：
   - allowlist 文本模型产生且只产生 Search + Fetch；
   - Sonar/图像/视频/未知模型原样早退；
   - 输入已有 metadata 时 merge，不覆盖其它合法字段；
   - 明确清理本 Filter 自己的 server-tools 时不误删别的 Filter。
4. 只读重新拉取 Function，确认源码 marker 和 valves。
5. `verify_text_web_search.py` 在 canary/final 两种模式下精确验证 Filter active/global/priority、allowlist attachment/default、所有排除模型和真实 tool events；先有 verifier，再改生产。

### W2 — 单模型 canary

1. 将薄 Filter 切为 `active=true`、`global=false`，重新读取并确认 priority=0，且 image guard=1、Sonar guard=100。
2. 先只挂 **Gemini 3.8 Flash**，不 default-on；手动打开 Filter。
3. 打四类探针：
   - 新鲜事实：必须真实调用搜索且含可点来源；
   - 指定 URL：必须调用 Fetch 并引用页面；
   - 普通知识/闲聊：原始 hosted-tool events/usage 必须是 0 次搜索；
   - 多轮追问：保留上下文，不重复无意义搜索。
4. 验证响应里的 hosted-tool events、usage、tool cards 和 citation annotations，不只检查回答正文“自称搜过”；确认实际 engine/回落行为，不能由 provider 名猜测。
5. 成本和调用数不越界；任何 400/404、空引用、无限循环即回滚 canary。
6. 对全量模型 metadata 做排除扫描；同时对一个图像模型发正常出图请求，抓响应事件确认没有 tool-use 404。

### W3 — 扩到 7 个文本模型

1. 逐个 attach，每次更新模型都带原 `access_grants`，保留全部 metadata/filterIds。
2. 首轮每个模型不 default-on，分别跑 Search + Fetch smoke。
3. 全部通过后，先把最终 SPEC/contract/main verifier 和幂等 apply/rollback 在仓库准备好并通过静态测试；再由一次 apply 原子地加入 `defaultFilterIds`，只影响新对话，已有对话不强改。
4. `openrouter_web_tools` 继续 inactive；Sonar/图像确认无新 Filter。
5. 同一次 final apply 更新一条英文 `usage-guide-v4`（替换 v3，不叠第二条），明确：
   - selected chat models can search automatically；
   - Sonar remains Quick Search / Deep Research；
   - Images only on image models。

### W4 — 验收后记录现网指纹

下列文件必须在 W3 final apply 前已包含目标契约和 verifier；W3 全绿后只补现网日期/指纹：

- `docs/SPEC.md`：新增 ST-14；修改 UX-1/UX-3/ST-2，不动 ST-11/ST-12/ST-13。
- `scripts/stack_contract.py`：Filter id、allowlist、默认 attachment、Banner id。
- `scripts/verify_stack.py`：精确验证 7 个文本、Sonar/图像排除、broad Filter inactive。
- `AGENTS.md` / rebuild archive：重建顺序和禁令。
- `docs/VERSIONS.md`：W3 后填写日期、Filter SHA、最后验收。

---

## 6. 验收门

### 功能题库

每个白名单模型至少通过：

1. **时效**：查询当天可核验的官方发布，引用至少两个来源。
2. **一手来源**：要求仅使用指定官方域名，结果不得引用聚合站代替。
3. **整页读取**：给出文档 URL，回答页面深处而非搜索摘要中的细节。
4. **交叉验证**：两个来源有冲突时明确指出，不强行合并。
5. **无需搜索**：简单改写/数学题的 hosted-tool events/usage 必须为 0。
6. **中文问答**：中文提问、英文来源，中文综合并保留来源。

不能只以 HTTP 200 验收。必须验证 response events/annotations 中确有 `openrouter:web_search` / `openrouter:web_fetch` 与 URL citations。

### 零回归

- `verify_stack.py` 全绿。
- 两档 Sonar smoke 200，出站无额外 tools。
- Filter 单测逐个覆盖 9 个 `IMAGE_MODEL_IDS`，再覆盖 Sonar、未知模型和 synthetic video model，必须原样早退且不产生 metadata server tools。
- 生产 metadata 全量扫描：Filter 只存在于 7 个 allowlist 模型；所有 image/video capability 模型、Sonar 和未知模型均无 attachment/default。
- 真实出图按三条不同路由抽测：
  - GPT Image 2（Images API）
  - Gemini 3.1 Flash Image（chat/image）
  - Seedream 5 Pro（Images API）
  三条均真实出图且无 `No endpoints found that support tool use`。这是路由代表性抽测，不虚称已逐个真实生成 9 张。
- `verify_compare_cross_model.py`、`verify_fable_thinking_replay.py` 全绿。
- 21 public = picker；无新家族、无额外 `*` read。
- Follow-up 仍关，Image Generation 仍关，`openai.api_configs` 仍全 disable。

---

## 7. 回滚

任何异常按最小范围回滚，不重建容器：

1. 从 7 个模型的 `defaultFilterIds` / `filterIds` 移除 `openrouter_text_web_search`，每次更新保留 `access_grants`。
2. 将薄 Filter 设 inactive；不删除，便于查因。
3. Banner 回 `usage-guide-v3`。
4. `verify_stack.py` + Sonar/图像 smoke。

禁止用空 `models/sync`、全量 valves 覆盖、新的非空 `WEBUI_SECRET_KEY` 或启用 `openai.api_configs` 作为“修复”。

---

## 8. 等待确认的唯一决策

建议确认以下整包，不拆开造成半上线：

> **确认 WS-A**：先恢复 21 active 绿基线；创建薄 `Web Search` Filter；首波挂 Grok 4.6、两条 Sol、Opus 5、Fable 5.1、两条 Gemini；Search + Fetch 默认开；Sonar/图像/视频排除；保留 Sonar Deep Research；不部署 GPT Researcher/Open Deep Research；通过 canary 和零回归后才 default-on 并更新 Banner/契约。

若不确认，生产保持当前 Sonar-only，不发生任何变化。
