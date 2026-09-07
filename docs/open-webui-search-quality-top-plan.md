# 即时搜顶级档：地图 + X + 平均 spike ≤ `$0.2`

> **状态**：用户已选 **顶级档**。**W0 已跑**（2026-09-07）：`max_tool_calls=3` 能转发；Flash / Sol 两轮都刹在 4 次搜；Grok「继续」漏到 11。生产 Filter/Pipe **已还原 Exa**。W1+ 未点头不执行。  
> **取代** `docs/open-webui-search-metered-quality-plan.md` 里的旧硬约束「`$19` 概率必须为零 / 生产永远禁止 OpenAI·Google·xAI native」。那份仍可作 T1 根因备忘。  
> **已确认（本波）**：深调研 **继续只用 Sonar**；普通气泡不当 Deep Research。  
> **W6**：仍关。Sol 刹住 **不是** Astra Pro 绿灯；`$19` 形态未用 Astra Pro 复测。

关联：`docs/open-webui-search-cost-plan.md`（`$19` / T1）；`docs/SPEC.md` ST-14；`docs/open-webui-text-web-search-plan.md`。

---

## 0. 结论先看

用户要同时：

1. **地图**：地点坐标 + 路网 + 路线 API + 路况；**1 公里精度够**；不要评分、电话。默认 **不画地图 UI**（数据进正文）。  
2. **X 上的内容**。  
3. **`$19` 类 spike**：把这类超额摊进「会搜的回复」后，平均成本抬升大约 **≤ `$0.2`**（分母若要改成天/月，执行前再钉）。  
4. **即时搜** 答案质量：几乎达到或超过 **各家官网即时搜**（不是 Deep Research）。

最大权重：**成本、复杂度、稳定性**。质量用分步换源，不用一次改三家 `engine`。

| 能力 | 顶级做法 | 和 spike |
|------|----------|----------|
| 中国怎么走 | **高德驾车路径 + 交通**，每轮次数顶，返回压缩 JSON（总长、时长、路况、约 1km 途经点） | 结果短，不是 495 万 token 的主因 |
| 海外怎么走 | **Google Routes**（第二把钥匙，可后做） | 同上 |
| Grok 即时搜 + X | **xAI 类 `engine=native`**（网页+X 绑定） | 单价低于 Astra；仍要看 W0 能否转发次数顶 |
| Gemini 即时搜 | **Google 类 `engine=native`**（Google 索引） | 同左；**不**用 Gemini native 冒充高德路网 |
| ChatGPT 即时搜 | **先留 Exa**；仅当 W0 证明 `max_tool_calls`（或等价硬顶）对 OpenAI 原厂内循环有效，才 native | 已知 `$19` 形态出在 Astra Pro |
| 非 Grok 也要读 X | **可计数 X 工具**（X API 或 xAI 只挂 `x_search`），第二步 | 次数我们数 |
| 深调研 | **只用 Sonar** | 不把普通气泡当无限调研 |
| 跨轮旧页 | **T1 已有**；T2 可选，利于平均 +`$0.2` | T2 改 Pipe，另步 |

**略简档（未选）**：只高德、只 Grok native、Gemini/OpenAI 不动。本文不施工略简。

---

## 1. 口径（执行前可改一句，不改默认为下）

### 1.1 Spike 平均 +`$0.2`

默认分母 = **每一次会搜的助手回复**。  
超额 ≈ 该发相对正常调研多付的钱（`$19` 那次大约多 **`$18`**）。

`P(spike) × 超额 ≈ $0.2` → 若超额仍是 `$18`，大约 **90 次会搜回复里最多 1 次** 这种炸。  
若单发硬顶把炸截成 `$5`，同样 `$0.2` 允许更高概率。

已知：Astra Pro + 原厂循环 +「你继续」+ 长调研 **已经发生过**，不是 1/90 的未知风险。所以 **OpenAI 类在没有有效硬顶之前保持 Exa**，不是「永远禁止 native」，是 **W6 过门前不开**。

### 1.2 即时搜 vs 深调研

| | 本 plan |
|--|---------|
| 气泡即时搜 | ST-14 Search+Fetch ± 各家 native ± 地图/X 工具 |
| 深调研 | **只用** `perplexity.sonar-deep-research`（及 Quick Search 档）。不上 ChatGPT Deep Research 仿品，不把「你继续」当 Deep Research |

### 1.3 地图范围

要：坐标、路网、路线、路况、约 1km 点距。  
不要：评分、电话、地图瓦片/嵌入 UI（未另点头不加）。  
禁止：把完整 polyline 塞进模型（会抬 token，违背成本权重）。

### 1.4 「各自官网即时搜」

- ChatGPT.com 即时搜 ≠ Deep Research。  
- Gemini 即时搜 ≈ Google 网页 grounding；中国路网仍弱于高德。  
- Grok.com 即时搜 ≈ 网页 + X。  
验收看 **正文**（事实、来源、该搜就搜），不爬官网 UI。

---

## 2. 现网（不动也能读）

- OWUI 0.11.3；薄 Filter ST-14 deny 类，12 个 public 文本 default-on。  
- OpenAI / Google / xAI：**Exa**；Anthropic：`auto`；中国三只：`auto`→Exa。  
- T1 `SEARCH_PAGE_COMPACT_V1`；`$0.05` / `step_count=8`；OpenRouter 写明 `max_uses` **只转 Anthropic**。  
- 无地图工具、无 X 原厂、无 T2、无单发 token 顶。  
- 钥匙：不入库；**不** `enable` `openai.api_configs`；不写新的非空 `WEBUI_SECRET_KEY`。

---

## 3. 架构（确认执行后才落地）

### 3.1 网页即时搜（ST-14 引擎按类）

| 类 | 目标 engine | 条件 |
|----|-------------|------|
| Anthropic | `auto`（原厂） | 已是；认 `max_uses` |
| Google | `native` | W2；W0 至少证明 Gemini 短问不会单发爆炸 |
| xAI | `native` | W3；换 X+网页 |
| OpenAI | **暂 `exa`** → 可能 `native` | 仅 W6 过门 |
| 中国三只 / 其他无原厂 | `auto` 或与 Q1 网页引擎一致 | 无原厂搜 |

不重开 `openrouter_web_tools`。Filter 非 global。deny 图像/Sonar 不变。

### 3.2 地图（可计数，与 native 解耦）

独立薄工具（OWUI Tool 或 Filter 注入的 function tool），**不是** Gemini `google_maps`。

- 中国：高德 **驾车路径 + 交通**。坐标系 GCJ-02。  
- 海外：Google **Routes API**（W4）。WGS84。  
- 每轮最多 2～3 次；返回：距离、预计时间、路况摘要、稀疏途经点（约 1km）。  
- 无 Place Details（评分/电话）。  
- 挂载：合格 public 文本；Sonar/图像/视频不挂。  
- 失败：正文说明「路线接口不可用」，禁止瞎编精确分钟数冒充路况。

### 3.3 X

- **W3**：Grok native 自带 X（与网页绑定）。  
- **W5**（可后做）：全模型可计数 X（官方 X API 或直连 xAI 仅 `x_search`）。配额/ToS/第二上游 → 单独过门。  
- 推文只回摘要 + 链接，不全文墙。

### 3.4 硬顶（服务 `$0.2`）

| 层 | 作用 |
|----|------|
| T1 | 已有；砍跨轮旧整页 |
| ST-14 `$0.05` / 8 步 | **只对可计数引擎有效** |
| 地图/X 自管工具次数 | 我们数 |
| 单发上游 `$` 或 token 顶 | W0 先探 OpenRouter 是否把 `max_tool_calls` 转进 OpenAI/Google/xAI 原厂循环；有效则 W6 可开 OpenAI native |
| T2 | 可选；「继续」累计，降 spike 频率 |

---

## 4. 分步（一步一个确认；可停在任一步）

未确认的步不执行。每步后 `verify_stack`；改模型带 `access_grants`；Pipe **只 merge** valves。

| 步 | 做什么 | 过门 | 回滚 |
|----|--------|------|------|
| **W0** 只读探针 | **已做**。脚本 `scripts/run_search_quality_w0.py`：带标记的消息才 native + `max_tool_calls=3` 且去掉 `stop_server_tools_when`；未标记生产流量仍 Exa。Flash / Grok / Sol 各 1 条十主题诱搜 +「你继续」。预算 ≤ `$10` | 见 **§10**：转发成功；Flash/Sol 刹在 4；Grok 续轮 11。生产已还原 | 已还原 |
| **W1** 高德路线 | 工具 + 钥匙 env + 挂合格文本 + 短 JSON + 次数顶。无 UI | 中国路线题：有坐标级距离/时长/路况大意，误差目标约 1km；误搜不升；无评分/电话字段 | 卸工具、剥 filterIds |
| **W2** Gemini native | Google 类 Search+Fetch `engine=native` | 短问仍会搜；单发 `$` 与次数可接受；中国路况仍走高德不是 Google | 改回 `exa` |
| **W3** Grok native | xAI 类 `native` | 能引用 X；网页即时搜不差于现网 Exa 烟雾；Grok「继续」超额符合 §1.1 | 改回 `exa` |
| **W4** Google Routes | 海外路线，同上压缩 | 海外题有路网级时长；国内仍高德 | 卸海外分支 |
| **W5** 全模型 X | 可计数 X 工具 | 非 Grok 也能引帖；配额不打穿；次数能刹 | 卸工具 |
| **W6** OpenAI native | **W0 未开绿灯**（Sol 能刹，Astra Pro 未测；Grok 续轮已证明 native 可越过 `max_tool_calls`） | Astra Pro「你继续」不得再出现无顶 46 次/上百万 input；超额期望仍 ≤ `$0.2` | 改回 `exa` |
| **W7** T2 | 单次用户消息内轮累计 | 「继续」叠 spike 变稀 | 去 Pipe marker |

**建议执行顺序（稳、简单优先）：W0 → W1 → W3 → W2 → W4 →（W0 若绿）W6 → W5 → W7。**  
W1 不依赖 native。W3 用最低复杂度换 X。W6 故意靠后。W5 最重，可长期停在 Grok-only X。

---

## 5. 成本 / 复杂度 / 稳定性

| 步 | 成本 | 复杂度 | 稳定性 |
|----|------|--------|--------|
| W0 | 探针几美元 | 低 | 只读 |
| W1 | 高德调用 ≪ 旗舰 token | 中：新钥匙、GCJ-02、工具挂载 | 图商稳；须防折线灌模型 |
| W2 | 平均仍应是短问几美分级 | 低：改类引擎 | 原厂循环数不一定到；靠 W0 与观察 |
| W3 | Grok 同体积远低于 Astra | 低 | 网页+X 绑定；Grok 狠搜可数美元 |
| W4 | 同 W1 量级 | 中：第二钥匙、坐标系 | 海外稳、国内弱（国内不走它） |
| W5 | X API 月费或 xAI 按次 | **高** | ToS/配额 |
| W6 | 质量接近 ChatGPT 即时搜 | 低（一行）但 **spike 风险最高** | 无硬顶则与 §1.1 冲突 |
| W7 | 降尾部 | 中：Pipe 记账 | 须单测，勿伤 ST-10/11 |

钥匙：高德 Key、Google Maps Platform（Routes）、可选 X/xAI。只进 env，**不进 git**，不进 Pipe `API_KEY` 覆盖，不开 OpenRouter 直连槽。

---

## 6. 明确不做

- 未点头的步。  
- 用 Sonar 冒充旗舰即时搜写作；用即时搜冒充 Deep Research。  
- 重开 broad Web Tools / OWUI native Web Search。  
- Filter `is_global`。  
- 地图 UI、评分、电话。  
- 为地图改 Gemini native（路网不走那条）。  
- 未 W0 就开 OpenAI native。  
- 爬 ChatGPT/Gemini/Grok.com 做评测。  
- 空 `models/sync`、全量 valves、新非空 `WEBUI_SECRET_KEY`。  
- 把 Ling / Muse / GLM 顺便 public。

---

## 7. 验收（相应步落地后）

1. 中国路线：正文有可用的距离/时长/路况大意，精度约 1km，无电话/评分堆砌。  
2. Grok：即时答案能用 X 内容（W3 后）。  
3. Gemini：隐含时效仍会搜；来源不像只靠 Exa（W2 后，人工抽检）。  
4. OpenAI：W6 未做则仍 Exa；W6 后 Astra「继续」有硬顶，期望超额 ≤ `$0.2`。  
5. Sonar 深研入口不变。  
6. `verify_stack` 绿；三 Guard；23 public。  
7. 不宣称「已超过官网」除非该步有对照题（公开 oracle + 人工，不爬官网）。

---

## 8. 建议 ST 号

- **ST-14** 仍是薄 Search+Fetch。  
- **ST-16**：出行路线工具（高德 / Google Routes）。  
- **ST-17**：xAI 类 native（X+网页）及可选全模型 X 工具。  
- 不写成 ST-11 / ST-12。OpenAI 是否 native 记在 ST-14 引擎表，不另起「永远禁止」条。

---

## 9. 请你确认后才执行

本文件 = 已选顶级档的施工单。  
**W0 已做**（§10）。**下一执行步默认 W1**（高德路线工具）。回 `W1：同意` 才改实例。  
若改做 W3 Grok native：须接受「继续」可能 >4 次搜（本次 11 次 / `$0.06`），回 `W3：同意`。

---

## 10. W0 结果（2026-09-07）

探针：`scripts/run_search_quality_w0.py`。带 `W0_MAX_TOOL_CALLS_PROBE_V1` 的消息才把 OpenAI / Google / xAI 改 `engine=native`、写入 `max_tool_calls=3`、去掉 `stop_server_tools_when`。未标记流量仍走生产 Exa。跑完 Filter `f2fe14388726`、Pipe `9c4836ace251` **已还原**；`verify_text_web_search.py --mode final` 14 ok。

全部 6 次请求的 Pipe 戳都是 `eng=native mtc=3 stop=False`，说明字段**确实转到了** `/responses`。诱搜题要 10 个独立 `web_search`；OpenRouter 文档允许 cap 触发后再执行 inflight 一次，所以 **3～4 次算刹住**。

| 模型 | 轮 | `web_search_requests` | input tokens | `$` | 判定 |
|------|----|----------------------|--------------|-----|------|
| Gemini 3.8 Flash | 十主题 | 4 | 14,665 | 0.036 | 刹住 |
| Gemini 3.8 Flash | 你继续 | 4 | 51,153 | 0.054 | 刹住 |
| Grok 4.6 | 十主题 | 4 | 23,547 | 0.067 | 刹住 |
| Grok 4.6 | 你继续 | **11** | 30,127 | 0.064 | **越过 cap**（戳仍是 mtc=3） |
| GPT 5.6 Sol | 十主题 | 4 | 15,535 | 0.046 | 刹住 |
| GPT 5.6 Sol | 你继续 | 4 | 36,217 | 0.069 | 刹住 |

合计 **`$0.336`**（预算 `$10`）。没有出现 `$19` / 百万 input；最大 input 约 5.1 万。完整 JSON：`docs/open-webui-search-quality-w0-results.json`。

含义：

1. **Google**：Flash 两轮都停在 4。支持稍后 W2，**不是**已经改生产引擎。  
2. **xAI**：首轮 4，续轮 11。`max_tool_calls` **不是** Grok native 的硬顶。W3 仍可做（11 次 / `$0.06` 远低于 spike 口径），但不能声称次数门牢。  
3. **OpenAI / W6**：**仍关**。Sol 两轮 4 只证明这一只模型的外环能刹；`$19` 出在 Astra Pro 原厂内循环，本波**故意没测** Astra Pro。Grok 续轮已经证明 native 可以无视 `mtc=3`。  
4. 生产搜索路径未变：OpenAI / Google / xAI 仍是 **Exa** + `$0.05` / 8 步。

