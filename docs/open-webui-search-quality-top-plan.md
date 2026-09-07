# 即时搜顶级档：地图 + X + 平均 spike ≤ `$0.2`

> **状态**：用户已选 **顶级档**。**W0–W6 已过门**。OpenAI / Google / xAI 类 Search+Fetch = `native`。OpenAI 常驻 `max_tool_calls=3`。W7 未做。  
> **取代** `docs/open-webui-search-metered-quality-plan.md` 里的旧硬约束「`$19` 概率必须为零 / 生产永远禁止 OpenAI·Google·xAI native」。那份仍可作 T1 根因备忘。  
> **已确认（本波）**：深调研 **继续只用 Sonar**；普通气泡不当 Deep Research。  
> **W6**：**已过门**。Astra Pro 两轮 4 次搜。生产 OpenAI native + `max_tool_calls=3`。  
> **W7**：决策点见 **§21**。未确认不施工。  
> **M1a（自驾多站）**：**已过门**。`via` + `legs[]`。见 **§22–§23**。M1b 未做。不与 W7 混号。

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
- **OpenAI：`native`** + `max_tool_calls=3`（W6）；**Google：`native`**（W2）；**xAI：`native`**（W3）；Anthropic：`auto`；中国三只：`auto`→Exa。  
- T1 `SEARCH_PAGE_COMPACT_V1`；`$0.05` / `step_count=8`；OpenRouter 写明 `max_uses` **只转 Anthropic**。  
- 无 X 原厂、无 T2、无单发 token 顶。  
- **ST-16**：`amap_drive_route` + `google_drive_route` 已挂 12 个 public 文本；高德 / Google Maps Key **已注入** Valves（不进 git）。  
- **ST-17 / W5**：`x_recent_search`（显示名 X Recent Posts）已挂同一批 12 个 public 文本；Bearer **已注入** Valves。Grok native X 仍在。  
- 钥匙：不入库；**不** `enable` `openai.api_configs`；不写新的非空 `WEBUI_SECRET_KEY`。

---

## 3. 架构（确认执行后才落地）

### 3.1 网页即时搜（ST-14 引擎按类）

| 类 | 目标 engine | 条件 |
|----|-------------|------|
| Anthropic | `auto`（原厂） | 已是；认 `max_uses` |
| Google | `native` | W2；W0 至少证明 Gemini 短问不会单发爆炸 |
| xAI | `native` | W3；换 X+网页 |
| OpenAI | **`native`** + `max_tool_calls=3` | W6 已过门 |
| 中国三只 / 其他无原厂 | `auto` 或与 Q1 网页引擎一致 | 无原厂搜 |

不重开 `openrouter_web_tools`。Filter 非 global。deny 图像/Sonar 不变。

### 3.2 地图（可计数，与 native 解耦）

独立薄工具（OWUI Tool 或 Filter 注入的 function tool），**不是** Gemini `google_maps`。

- 中国：高德 **驾车路径 + 交通**。坐标系 GCJ-02。  
- 海外：Google **Routes API**（W4）。WGS84。  
- 每轮最多 2～3 次；返回：距离、预计时间、路况摘要、稀疏途经点（约 1km）。**M1a**：可选 `via`（最多 6）回 `legs[]` + `totals`。  
- 无 Place Details（评分/电话）。  
- 挂载：合格 public 文本；Sonar/图像/视频不挂。  
- 失败：正文说明「路线接口不可用」，禁止瞎编精确分钟数冒充路况。

### 3.3 X

- **W3**：Grok native 自带 X（与网页绑定）。  
- **W5**（已过门）：薄 Tool `x_recent_search` 已挂 12 个 public 文本。近 7 天关键词真帖 + `x.com/status`。API `max_results` 下限 **10**。每轮最多 3 次。失败说「X 接口不可用」。  
- 推文只回摘要 + 链接，不全文墙。不采用 Nitter / xAI 侧车。

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
| **W1** 高德路线 | **已过门**。Tool `amap_drive_route` 挂 12 个 public 文本；Key 在 Valves。压缩 JSON、次数顶=3、无 UI。见 **§11** | Flash 正文有距离/时长/路况大意，无「路线接口不可用」、无电话/评分 | `scripts/rollback_amap_drive_route.py` |
| **W2** Gemini native | **已过门**。Google 类 Search+Fetch `engine=native`。OpenAI 仍 Exa。见 **§14** | Flash 短问 4 次搜 / `$0.056`；北京南站→首都机场走高德 36.7km / 41 分钟，0 次网页搜 | 改回 `exa` |
| **W3** Grok native | **已过门**。xAI 类 Search+Fetch `engine=native`。见 **§13** | 能引用 X；网页即时搜仍出活链；Grok「继续」超额符合 §1.1 | 把 xAI 改回 `exa` 后 `apply_search_quality_w3.py` 的逆操作（Filter content） |
| **W4** Google Routes | **已过门**。Tool `google_drive_route` 挂 12 个 public 文本；Key 在 Valves。见 **§16** | Flash 海外 27km / 57 分钟；国内仍高德 36.7km / 41 分钟 | `scripts/rollback_google_drive_route.py` |
| **W5** 全模型 X | **已过门**。官方 X API 按次 Tool `x_recent_search`；Key 在 Valves。见 **§19** | Flash 调工具并引活链；Grok 回归仍能引 X；纯网页题未狂调 X | `scripts/rollback_x_recent_search.py` |
| **W6** OpenAI native | **已过门**。Astra Pro 两轮 4 次搜。生产 OpenAI native + `max_tool_calls=3`（去掉会被覆盖的 stop）。见 **§20** | Astra Pro「继续」有硬顶；短问仍搜；中国路线仍高德 | 改回 `exa` |
| **W7** T2 | **未做**。决策见 **§21** | 「继续」叠搜变稀；首轮次数仍够 | 去 Pipe marker |

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
| W5 | 官方 X 按次（约 `$0.005`/条，默认 10 条） | 中（与路线工具同形） | ToS/配额；无 Key 则说接口不可用 |
| W6 | 质量接近 ChatGPT 即时搜 | 低（一行）但 **spike 风险最高** | 无硬顶则与 §1.1 冲突 |
| W7 | 降尾部 | 中：Pipe 记账 | 须单测，勿伤 ST-10/11 |

钥匙：高德 Key、Google Maps Platform（Routes）、X Bearer。只进 Tool Valves，**不进 git**，不进 Pipe `API_KEY` 覆盖，不开 OpenRouter 直连槽。

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

**W0–W6 已过门**。**M1a 已过门**（§23）。**不要自行开 W7**（§21）。**不要自行开 M1b**。


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

---

## 11. W1 结果（2026-09-07）

落地：OWUI Tool `amap_drive_route`（`AMAP_DRIVE_ROUTE_V1`），public `*` read；挂在与 ST-14 相同的 **12** 个 public 文本；Sonar / 图像未挂。返回压缩 JSON（`km` / `minutes` / `traffic` / `via` 约 1km，最长 24 点）。每 chat 120s 窗口最多 3 次。无地图 UI。Pipe / 搜索引擎 **未改**。Key 在 Tool Valves，不进 git。

上游（北京南站 → 首都机场）：`status=1`，36.7 km / 45 分钟，路况「畅通为主，局部缓行」，24 个途经点，无电话。

Flash 烟雾（`AMAP_EXPECT_LIVE=1`，`$0.003`）：`function_call_count=1`，正文 **36.7 公里 / 约 44 分钟 / 畅通为主**，途经南二环、东三环、机场高速等。无「路线接口不可用」，无电话/评分。导数控制题 0 次工具。`verify_amap_drive_route.py --require-key` 16 ok；`verify_stack.py` `VERIFY_SMOKE=0` 24 ok。

**过门通过。** JSON：`docs/open-webui-search-quality-w1-results.json`。

---

## 12. W1 高德 Web 服务 Key：申请 + 注入

现网 Tool 调这两条（必须是 **Web 服务** Key）：

- `https://restapi.amap.com/v3/geocode/geo`
- `https://restapi.amap.com/v5/direction/driving`（`strategy=32`，`show_fields=cost,tmcs,polyline`）

### 12.1 申请（已完成即可跳过）

1. [高德开放平台](https://lbs.amap.com/) 注册登录并**实名认证**（未认证不能新增 Key）。
2. 控制台 → 应用管理 → 创建应用 → **添加 Key**，服务平台选 **Web 服务**（不要选 JS API）。
3. **数字签名关掉**。IP 白名单可空（能用，但更不安全）；若填，用 VPS `78.47.152.85`。
4. 要复制的是 Key 列表里那一**长串**，不是名称 `micropigeon`。设置弹窗里通常看不到这串。
5. 不要把 Key 写进 git、聊天、Pipe `API_KEY`，也不要改 `WEBUI_SECRET_KEY`。

### 12.2 注入（用网站，不要 SSH）

1. 高德控制台 **应用管理** → 找到 Key `micropigeon` → **复制**那一长串。
2. 打开 [https://micropigeon.com/workspace/tools](https://micropigeon.com/workspace/tools)（Admin 登录）。
3. 找到 **China Drive Route**，鼠标放上去，点 **Valves**（齿轮旁边）。
4. 在 **Amap Key** 框粘贴 → **Save**。Max Calls 保持 3，Max Via Points 保持 24。
5. 回 `W1 Key 已注入`。**不要**把 Key 贴进聊天。

### 12.3 可选：VPS 脚本

不需要。只有在网站填不进去时才用 `scripts/inject_amap_key_vps.sh`。不要改 `/root/open-webui.env`，不要重启容器。

注入后 agent 跑 `verify_amap_drive_route.py --require-key` 和 `AMAP_EXPECT_LIVE=1 python3 scripts/run_amap_drive_route_smoke.py`。

---

## 13. W3 结果（2026-09-07）

薄 Filter content-only：xAI 类 `web_search` / `web_fetch` **`engine=native`**（marker `TEXT_WEB_SEARCH_XAI_NATIVE_V1`）。OpenAI / Google 仍 Exa；Anthropic 仍 auto。Pipe **未改**（`9c4836ace251`）。OWUI native Web Search **仍关**。未重开 broad Web Tools。

Grok 4.6 烟雾（`$0.25`）：

- X 题：4 次搜，正文引用 `https://x.com/elonmusk/status/2093794565274669068`。
- 网页题：1 次搜，仍出活链（OpenAI 本周产品新闻）。
- Flash 回归：仍会搜（Google 仍 Exa，4 次 / `$0.04`）。

`verify_text_web_search.py --mode final` 15 ok；`verify_stack.py` `VERIFY_SMOKE=0` 24 ok。JSON：`docs/open-webui-search-quality-w3-results.json`。

W0 已接受 Grok 续轮可 >4 次搜。**W2 Gemini native 已过门**（§14）。**W5 已过门**（§19）。W6 OpenAI native **未做**。

---

## 14. W2 结果（2026-09-07）

薄 Filter content-only：Google 类 `web_search` / `web_fetch` **`engine=native`**（marker `TEXT_WEB_SEARCH_GOOGLE_NATIVE_V1`）。OpenAI 仍 Exa（W6 关）；xAI 仍 native；Anthropic 仍 auto。Pipe **未改**（`9c4836ace251`）。OWUI native Web Search **仍关**。未重开 broad Web Tools。

Flash 3.8 烟雾（`$0.059`）：

- 短问（OpenAI 本周产品新闻）：4 次搜 / `$0.056`，正文有活链。
- 中国路线（北京南站→首都机场）：`function_call_count=1`，**0 次网页搜**，正文 **36.7 公里 / 约 41 分钟 / 畅通为主**。无「路线接口不可用」，无电话/评分。

`verify_text_web_search.py --mode final` 17 ok；`verify_stack.py` `VERIFY_SMOKE=0` 24 ok。JSON：`docs/open-webui-search-quality-w2-results.json`。

**过门通过。** 中国路况仍走高德，不是 Google 网页搜。**W5 已过门**（§19）。W6 **未做**。

---

## 15. W4 Google Routes Key：申请 + 注入

现网 Tool 调这一条（必须是 **Routes API** Key，不要用 Maps JavaScript / 静态图 Key）：

- `POST https://routes.googleapis.com/directions/v2:computeRoutes`（`TRAFFIC_AWARE`，只要时长/距离/折线/路况间隔）

Tool 已挂 12 个 public 文本。Key **已注入**（2026-09-07），过门见 **§16**。中国路线仍走高德。

### 15.1 申请

1. 打开 [Google Cloud Console](https://console.cloud.google.com/) 并登录。
2. 选一个项目（没有就新建）。**要开通结算**，否则 Routes API 调不通。
3. 「API 和服务」→「库」→ 搜 **Routes API** → **启用**。
4. 「API 和服务」→「凭据」→ **创建凭据** → **API 密钥**。
5. 复制那一**长串**（一般以 `AIza` 开头）。不要复制项目名。
6. 可选：把密钥限制为 **Routes API**。IP 白名单可空。
7. 不要把 Key 写进 git、聊天、Pipe `API_KEY`，也不要改 `WEBUI_SECRET_KEY`。

### 15.2 注入（用网站，不要 SSH）

1. 打开 [https://micropigeon.com/workspace/tools](https://micropigeon.com/workspace/tools)（Admin 登录）。
2. 找到 **Overseas Drive Route**，鼠标放上去，点 **Valves**。
3. 在 **Google Maps Key** 框粘贴 → **Save**。Max Calls 保持 3，Max Via Points 保持 24。
4. 回 `W4 Key 已注入`。**不要**把 Key 贴进聊天。

注入后 agent 跑 `verify_google_drive_route.py --require-key` 和 `GOOGLE_EXPECT_LIVE=1 python3 scripts/run_google_drive_route_smoke.py`。

---

## 16. W4 结果（2026-09-07）

落地：OWUI Tool `google_drive_route`（`GOOGLE_DRIVE_ROUTE_V1`），显示名 Overseas Drive Route；挂在与高德相同的 **12** 个 public 文本。WGS84。压缩 JSON（`km` / `minutes` / `traffic` / `via`）。每 chat 120s 最多 3 次。无 Place Details、无地图 UI。Pipe / 搜索引擎 **未改**。Key 在 Tool Valves，不进 git。

上游（JFK → Times Square）：`http 200`，27.0 km / 3394 秒，13 段路况间隔。

Flash 烟雾（`GOOGLE_EXPECT_LIVE=1`，约 `$0.005`）：

- 海外：`function_call_count=1`，正文 **27 公里 / 约 57 分钟 / 路况一般**，途经 Van Wyck、Grand Central、Queens-Midtown Tunnel。无电话/评分。
- 中国回归：`function_call_count=1`，正文 **36.7 公里 / 约 41 分钟 / 畅通为主**（高德，不是 Google）。

`verify_google_drive_route.py --require-key` 17 ok；`verify_stack.py` `VERIFY_SMOKE=0` 24 ok。JSON：`docs/open-webui-search-quality-w4-results.json`。

**过门通过。** **W5 已过门**（§19）。W6 **未做**。

---

## 17. W5 沟通：其他模型读 X，相对 Grok 差在哪（已确认：官方 X API 按次）

现网只有 **Grok 4.6** 的 Search+Fetch 是 `native`，网页和 X **绑在一起**。W3 烟雾：同一道「最近 Tesla/SpaceX 帖」能引出活的 `x.com/.../status/...`。

其余 11 个 public 文本 **没有 X 原厂索引**：

| 类 | 现网搜 | 遇到「X 上怎么说」时实际拿到什么 |
|----|--------|--------------------------------|
| Grok | native | 推文正文 + 状态链接 + 作者/时间；接近 Grok.com |
| Gemini | Google native | 多为新闻转述、镜像、旧帖；新帖和低粉帖经常没有 |
| OpenAI | Exa | 同上，且更偏网页摘要；少见活的 status URL |
| Anthropic / 中国三只 | auto→Exa | 最容易变成「据报道有人在推上说」，或编链接 |

**数据差（W5 能补的）**

- **时效**：Grok 能到分钟级；网页索引常见小时～天，突发帖经常搜不到。
- **覆盖**：Grok 能按账号/关键词在 X 里搜；其他模型只能搜「已经被网页编进索引的那一小截」。
- **正文**：Grok 直接读推文；其他模型常只拿到标题、转载、或 Fetch 被 X 登录墙挡住。
- **引用**：Grok 能给 `x.com/user/status/id`；其他模型容易给新闻稿、Nitter 残页，或编一条。

**W5 也补不齐的（同一把 X 工具挂上去之后仍在）**

- **写法**：Grok 更会串线程、引用链、社区语气；Opus/Flash/Sol 更像「读了几张卡片再写纪要」。
- **混搜**：Grok 网页+X 是一家引擎；其他模型要自己决定何时调 X 工具，可能先网页搜再漏调。
- **失败时**：工具空结果时，非 Grok 更爱编。工具必须失败说「X 接口不可用」，禁止编 status URL。

所以：W5 能把「有没有真帖」拉近；**不能**把 Flash/Opus 的 X 写作做成 Grok.com。说明书仍应写「要最像 Grok 官网上刷 X，用 Grok」。

### 17.1 两档（先选再做）

**顶级**：可计数 X 工具挂 12 个 public 文本（与 ST-14 同一批；Sonar/图像不挂）。每轮最多 2～3 次。只回：作者、时间、摘要、`x.com` 链接。不全文墙、不做嵌入 UI。

| 上游 | 质量 | 成本 / 复杂度 | 风险 |
|------|------|----------------|------|
| 官方 X API | 稳、可计数、ToS 干净 | **高**（月费档 + 配额） | 申请/账单；超配额要刹 |
| 直连 xAI 只挂 `x_search` | 最接近 Grok 同源 | 按次；第二上游 | ToS/钥匙；给竞品模型喂 xAI 搜 |

**略简（可长期停）**：不做 W5。X 只保证 Grok。Banner/说明书写清。其他模型继续网页搜，接受上面那张表的差距。复杂度最低、无新钥匙。

不采用：Nitter / 非官方爬、用网页搜冒充「已接 X」、把 Sonar 当全模型 X。

### 17.2 若做顶级，过门怎么验

同一道 X 题（最近 7 天真帖 + 必须 `x.com/status`）：

1. Grok：回归仍能引活链（W3 已有）。
2. 非 Grok 至少 1 个旗舰（Flash 或 Opus）：必须调 X 工具，正文有活链，不编。
3. 对照题（纯网页新闻）：不得无故狂调 X。
4. 次数顶有效；单发 `$` 可接受。

用户已回 **`W5：X API 按次`**。xAI 侧车不做。

### 17.3 非 Grok 最高性价比（2026-09-07 沟通；已选官方 X 按次）

OpenRouter **不会**把 Grok 的 `x_search` 分给 Gemini / OpenAI / Claude。W2 Google native 仍是网页，不是 X。

xAI 文档里的 `x_search` 是 **Grok 身上的 server tool**（`$5` / 1k 次 = 每次搜 `$0.005`，另加 Grok token）。不能直接挂到 Flash/Opus。要给别的模型用，只能再包一层「让 Grok 只搜 X → 压缩卡片」，多一跳、多 token，还可能触发 ToS。

官方 X API 2026 新号是 **按次**（旧 Basic `$200`/月已不对新用户开）：第三方帖大约 **`$0.005` / 条返回**，按返回条数计，不是按请求。无月租底板。

| 方案 | 非 Grok 拿到什么 | 大约 `$` | 复杂度 | 性价比 |
|------|------------------|----------|--------|--------|
| **不做**（X 题用 Grok） | 无 | `$0` | 零 | 问 X 少时最优 |
| **官方 X API 按次 + 薄工具** | 近 7 天关键词真帖 + `x.com/status` | 每问 **10** 条（API 下限）≈ `$0.05`；顶 3 次 ≈ `$0.15` | 中（和路线工具同形） | **要真帖时最优** |
| xAI 侧车（便宜 Grok + 只 `x_search`） | 接近 Grok 同源（语义/线程） | `$0.005`/搜 + Grok token；Grok 可能连搜几次 | 高 | 质量更好，`$` 和复杂度都更差 |
| 继续网页搜 | 新闻转述 / 旧帖 / 易编链 | 已付网页搜 | 零 | 便宜但经常不是 X |

**性价比主推（已选）**：官方 X 按次 + 与高德同形的薄 Tool。X Recent Search 的 `max_results` **下限 10**（不是计划初稿的 5～8）；Valves 默认 10、上限 20。每轮最多 3 次。只回作者/时间/摘要/链接。不挂 Sonar/图像。失败说「X 接口不可用」。不请求 `public_metrics`。

不采用：Nitter、为 X 去开 OpenAI native、把网页搜写成已接 X、xAI 侧车。

---

## 18. W5 X Bearer：申请 + 注入

现网 Tool 调这一条（只要 Recent Search，不要 Embed / 全文墙）：

- `GET https://api.x.com/2/tweets/search/recent`（`tweet.fields=created_at,author_id`；`expansions=author_id`；`user.fields=username`）

Tool **已挂** 12 个 public 文本。Key **已注入**（2026-09-07），过门见 **§19**。Grok native X 仍可用。

### 18.1 申请

1. 打开 [developer.x.com](https://developer.x.com/) 并登录。
2. 进 **Developer Portal** → 建一个 **Project** 和 **App**（已有就用现成的）。
3. **开通结算 / pay-per-use**（2026 新号按次；旧 Basic `$200`/月不对新用户开）。没结算时 Recent Search 常 403。
4. App → **Keys and tokens** → 生成或复制 **Bearer Token**（一长串）。不要复制 API Key / API Secret / Client ID。
5. 不要把 Token 写进 git、聊天、Pipe `API_KEY`，也不要改 `WEBUI_SECRET_KEY`。

### 18.2 注入（用网站，不要 SSH）

1. 打开 [https://micropigeon.com/workspace/tools](https://micropigeon.com/workspace/tools)（Admin 登录）。
2. 找到 **X Recent Posts**，鼠标放上去，点 **Valves**。
3. 在 **X Bearer Token** / `X_BEARER_TOKEN` 框粘贴 → **Save**。Max Calls 保持 3，Max Results 保持 **10**（不要改成 5，上游会拒）。
4. 回 `W5 Key 已注入`。**不要**把 Token 贴进聊天。

注入后 agent 跑 `verify_x_recent_search.py --require-key` 和 `X_EXPECT_LIVE=1 python3 scripts/run_x_recent_search_smoke.py`。

---

## 19. W5 结果（2026-09-07）

落地：OWUI Tool `x_recent_search`（`X_RECENT_SEARCH_V1`），显示名 X Recent Posts；挂在与 ST-14 相同的 **12** 个 public 文本。Sonar / 图像未挂。压缩 JSON（`author` / `time` / 短 `text` / `x.com/.../status/...`）。每 chat 120s 最多 3 次。`max_results` 默认 10（API 下限）。不请求 `public_metrics`。无嵌入 UI。当时 Pipe / 搜索引擎 **未改**（OpenAI 仍 Exa）。Token 在 Tool Valves，不进 git。

上游（`Tesla OR SpaceX`）：10 条，首条 `https://x.com/KayoteWyley420/status/2097037068740518329`。

烟雾（`X_EXPECT_LIVE=1`）：

- Flash：`function_call_count=1`，正文引 `https://x.com/SpaceX/status/2096625304009597207`（X API 核对：`SpaceX`，2026-09-06）。`$0.0022`。未说「X 接口不可用」。
- Grok 回归（W3 口径，不逼它点名工具）：4 次搜，正文引 `https://x.com/elonmusk/status/2093794675660378441`（X API 核对：`elonmusk`）。`$0.092`。强制「用 X 最近帖工具」时 Grok 可能改走网页、不引帖；native X 仍在。
- Flash 网页对照：4 次网页搜，**未**调 X 工具。`$0.044`。

`verify_x_recent_search.py --require-key` 17 ok；`verify_stack.py` `VERIFY_SMOKE=0` 24 ok。Pipe 仍 `9c4836ace251`。JSON：`docs/open-webui-search-quality-w5-results.json`。

**过门通过。** **W6 已过门**（§20）。

---

## 20. W6 结果（2026-09-07）

先探针、再生产。探针复用 W0 消息级 inject：带标记才 native + `max_tool_calls=3` 并去掉 `stop_server_tools_when`。未标记生产当时仍 Exa。跑完 Filter/Pipe **已还原**，再 apply。

Astra Pro（`$19` 那只）十主题 +「你继续」：

| 轮 | `web_search_requests` | input tokens | `$` | 判定 |
|----|----------------------|--------------|-----|------|
| 十主题 | 4 | 72,819 | 0.426 | 刹住 |
| 你继续 | 4 | 95,046 | 0.522 | 刹住 |

戳：`eng=native mtc=3 stop=False`。合计 **`$0.95`**。没有 46 次搜 / 百万 input。

生产落地：OpenAI 类 Search+Fetch **`engine=native`**；OpenAI **常驻** `max_tool_calls=3`，并 **去掉** `stop_server_tools_when`（OpenRouter 的 stop 会盖掉 mtc，探针只有去掉 stop 才刹住）。Pipe content-only `MAX_TOOL_CALLS_FORWARD_V1` 把字段抄进 `/responses`。Google / xAI 仍 native（各自仍带 `$0.05` / 8 步 stop）。Anthropic / 中国三只仍 `auto`。未抬 `$0.05`。

烟雾：

- Sol 短问：4 次搜 / `$0.053`
- Astra Pro 短问：3 次搜 / `$0.444`
- Sol 中国路线：高德 36.7 km / 41 分钟，0 次网页搜

`verify_text_web_search.py --mode final` 17 ok；`verify_stack.py` `VERIFY_SMOKE=0` 24 ok。Pipe `7242967443d4`。JSON：`docs/open-webui-search-quality-w6-results.json`。

**过门通过。** W7 决策见 **§21**。

---

## 21. W7 决策点（2026-09-07，未确认，不施工）

问的是：**还要不要做 T2（单次用户消息内轮累计预算）**。不是施工说明书。

### 21.1 W7 是什么、不是什么

费用 plan 里的 **T2**。Pipe 给「这一次用户发送」记 Search / Fetch / 工具账，**内轮不重置**。到顶停工具，模型用已有材料写完。

**不是**质量滤镜、降采样、换弱模型、关默认搜索。没有「质量 × 系数」算法。D3 **从未**定 `$` 或次数。弱多少 = 顶定多紧 ×「继续」时还剩多少没搜的题。没有实测。

S4（「继续」就剥 tools）**不是** W7，会漏新事实，本版不进主线。

### 21.2 `$19` 那条，W7 还剩多少要修

当时：Astra Pro **一次点击**里原厂连搜 9 轮、46 次搜、495 万 input。`$0.05` 每轮清零。46 次搜约 `$0.46`；约 `$15` 是旧整页回放。

| 层 | 状态 | 挡住什么 |
|----|------|----------|
| T1 压旧页 | **已落地** | `$15` 那截 token 雪球 |
| W6 OpenAI `max_tool_calls=3` | **已过门** | Astra Pro **一次发送**内轮（探针续轮 4 次 / 9.5 万 token / `$0.52`） |
| `$0.05` / 8 步 | Google / xAI / Anthropic / 中国三只仍按请求清零 | 对 OpenAI 原厂内循环本来就无效；W6 已改走次数顶 |
| W7 / T2 | **未做** | 「继续」再买一轮新额度；Grok 续轮仍可 11 次 |

**同一形态再出一键 `$19`：现网应接近零**（前提：Pipe 还带着 `MAX_TOOL_CALLS_FORWARD_V1` + T1）。W7 修的是**尾巴**，不是同一颗地雷。

### 21.3 不做 W7（现网，略简 T−）

继续可以再搜。OpenAI 每次点击仍约 3～4 次；Grok 续轮可到 11。T1 让每轮上下文小一个数量级。

- **质量**：首轮即时搜不变。「继续」补搜、复核、补主题 **更完整**。无未测弱化。
- **费用**：连点「继续」是多次点击累加，不是一键 46 次。Astra Pro 单发探针约 `$0.5`；九次点击量级是数美元，不是 `$19`。
- **复杂度**：零。不改 Pipe 记账，不碰 ST-10/11。
- **和 §1.1**：超额若从 `$18` 收到约 `$1` 内，平均 `≤ $0.2` 已经松很多。

这就是费用 plan 的 **T−**：T0 + T1（+ 已有 W6），先不做 T2。

### 21.4 做 W7（顶级 T 的最后一块）

**档 A（对症、范围小）**：只把「内轮不重置」补到 **还在用 `$0.05` stop 的类**（尤其 Grok 续轮 11）。OpenAI 已有 W6，不再叠一层。数字建议：与 W6 同形，每用户发送最多 3～4 次搜（`max_tool_calls` 或等价累计）。首轮 EVAL-B 形态不动。

**档 B（更顶、伤补搜）**：把账记到 **跨「你继续」多次用户消息**（同一条对话线程一段时间内）。连点继续也不能再买新搜。补搜明显变弱；弱多少仍无公式。预算须 D3 另定，不能猜。

不采用：会话终身总顶（新问题也会饿死）；S4 剥 tools；全局拧 `max_uses`；把 `$0.05` 解释成整段对话上限。

| | 复杂度 | 质量 | 稳定性 |
|--|--------|------|--------|
| A | 中：Pipe content-only + 单测；勿伤 ST-10/11 | 首轮不变；Grok「继续」少补搜 | 须防 Pipe 更新丢 marker |
| B | 更高：要定义「同一轮意图」跨消息 | 「继续」复核变弱，无量化 | 记账边界易错（新问题 vs 继续） |

过门（若做 A）：Grok「继续」不得再 11 次；Sol/Astra 短问仍搜；`verify_stack` + ST-10/11 回归。回滚：去 Pipe marker。

### 21.5 建议

**默认选不做 W7（§21.3）。** `$19` 主因 T1+W6 已覆盖。W7 没有预算数字、没有质量实测、还要改 Pipe 记账。宪法上「略简单、稳定特别多」就是 T−，不是关搜索。

若仍要顶级收尾：先 **档 A**（Grok / 非 OpenAI 内轮），不要一上来做档 B。

回 `W7：不做` / `W7：档 A` / `W7：档 B`。未回不施工。

---

## 22. 自驾游路线：顶级加宽（2026-09-07，未确认，不施工）

问的是：**「制定自驾路线」要不要把 ST-16 从 A→B 加宽成一次多站。** 不是施工说明书。不与 W7 混号。仍记 **ST-16**，不新开 ST。

### 22.1 现网对自驾差在哪

现网两把工具（中国高德 / 海外 Google）只会 **一段 A→B**，每 chat 120 秒最多 **3** 次。核「北京南站→机场」合适。

「西安出发 8 天：西宁、青海湖、张掖、敦煌」要的是 **每一段开车多久**，让模型排每天开几小时。现网一次发送最多核 3 段，后面靠记忆或网页搜，分钟数会飘。

查店、评分、画地图 **不是** 这个缺口。景点开门、封路、住宿、天气继续走网页搜 / 知识。

### 22.2 顶级 M1（建议终态）

**一句话**：模型一次调用，传入有序城市/景点列表；工具回 **每一段** 的公里、分钟、路况大意 + 全程合计。聊天里仍是正文行程，不画地图。

| 项 | 定法 | 为什么这样定 |
|----|------|----------------|
| 形态 | 扩现有两把 Tool，不新挂第三把 | 12 个 public 已挂；模型少选一把 |
| 入参 | `origin` + `destination` + 可选 `via[]` | 单段旧题零改；自驾把中间站放 `via` |
| 站数 | 最多 **8 站**（起点 + ≤6 个 via + 终点）= **7 段** | 覆盖 8 日西北环线；高德最多 16 途经、Google 最多 25，我们主动收。Google **11+ 途经加价**，6 个 via 躲过 |
| 出参 | `legs[]`（每段 `from/to/km/minutes/traffic/roads`）+ `totals` | 自驾要的是「每天开多久」，不要一条总时间 |
| 路况 | 仍是 **此刻**；JSON 带 `traffic_as_of=now` | 第 5 天的「堵」不能当直播；分钟数仍是路网尺子 |
| 折线 | 每段最多约 **8** 个 1km 点（比现在单段 24 更稀） | 7 段 × 24 点会把 JSON 喂肥 |
| 次数顶 | **仍 3 次 / 120s**（一次多站算 1 次） | 够：一条环线 + 一条对比 + 一次改道。不靠把 3 改成 8 来硬凑 |
| 偏好 | 可选 `prefer`：`default` / `prefer_highway` / `avoid_highway` / `avoid_toll` | 自驾常要「走国道看风景」vs 高速；**第二刀**，可先不做 |
| 钥匙 | 仍用现有 Valves，不新申请 | 高德已有 `waypoints`；Google `intermediates` + `legs` |
| 失败 | 任一站地理失败、中外混站、超 8 站 →「路线接口不可用」，禁止编分钟数 | 与 W1/W4 同一失败句 |

**实现（对模型仍是一次 function call）**

- **海外**：一次 `computeRoutes`，`intermediates` 为经停（不要 `via:true`，否则没有分段 `legs`）。Field mask 加 `routes.legs.duration`、`routes.legs.distanceMeters`。
- **中国**：先试高德 v5 `waypoints`（`;` 分隔，最多 16）。若只回全程、切不出段，则 **内部** 对相邻站打 A→B（最多 7 次图商），拼成 `legs[]`。内部扇出不算模型的第 2、第 3 次工具。
- **地理**：先全部 geocode；中外混用（大陆高德 + 海外 Google）直接失败，提示拆成两次、换对应工具。
- **港澳台**：按海外（Google），写进 docstring。不在这一刀做精细归属。
- **不优化站序**：不打开 Google `optimizeWaypointOrder`。自驾站序由用户/模型定，工具不重排成「最短配送」。

**模型说明书（docstring）要改的一句**

多日自驾把城市按顺序放进 `via`，**不要**一城打一次。单段「怎么开」仍只填 origin/destination。

**示例 JSON（形状，不是现网回包）**

```json
{
  "ok": true,
  "provider": "amap",
  "traffic_as_of": "now",
  "note": "分钟数是路网估算；实时路况只代表现在",
  "stops": ["西安", "西宁", "青海湖", "张掖"],
  "legs": [
    {"from": "西安", "to": "西宁", "km": 890.0, "minutes": 720, "traffic": "畅通为主", "roads": ["G30"]},
    {"from": "西宁", "to": "青海湖", "km": 150.0, "minutes": 150, "traffic": "畅通为主", "roads": ["G109"]}
  ],
  "totals": {"km": 1400.0, "minutes": 1200}
}
```

### 22.3 顶级里明确不做

| 不做 | 原因 |
|------|------|
| 查店 / 评分 / 电话 | 与已确认「不要 Place Details」冲突；住宿点评走网页搜 |
| 地图 UI / 瓦片 / 行程图 | 另产品；正文行程不依赖它 |
| 步行 / 公交 / 地铁 | 不是自驾；另刀 |
| 一次返回 3 条备选路线 | JSON ×3，token 与「压页」方向反 |
| 会话级无限途经 | 图商配额 + 模型乱堆 20 站 |
| 新 ST / 新 Banner / 新入口 | 仍是 ST-16 两把工具 |
| 和 W7 绑在一起 | W7 是搜索内轮记账 |

### 22.4 略简档（质量仍明显好一截）

**只把 `MAX_CALLS` 3→8**，入参仍是 A→B。工程最小。

代价：模型必须连打 7 次；Sol 已经出现过「说没有路线工具」。自驾一问仍可能只核前 3 段。宪法要求一并写出；**默认不推荐当终态**。

### 22.5 分两刀（仍属顶级，可停）

| 刀 | 做什么 | 过门 |
|----|--------|------|
| **M1a（先做）** | `via` + `legs[]` + totals；`prefer` 固定现网 default（高德 32 / Google `TRAFFIC_AWARE`）；次数顶仍 3 | 西安→西宁→青海湖→张掖：**一次**调用、≥3 段、每段有 km/分钟；北京南站→机场仍约 36.7km / 1 段；JFK→Times Square 回归；中外混站失败；`verify_stack` + 高德/Google 旧 verify |
| **M1b（可选）** | 加 `prefer` 四值 | 同一条线 `avoid_highway` 与 default 的道路名或公里数可区分；短问回归不坏 |

回滚：工具 content 回到只收 origin/destination；Valves Key 不动。

### 22.6 建议

**默认选 M1a。** 这是「制定自驾路线」相对官网即时搜真正缺的那一截：一次多站、按段出尺子。次数顶不用动。M1b、画地图、查店都另点头。

略简「只加次数」能缓解，但赌模型会连打 7 次，不如一次 `via`。

**已确认：`M1：M1a`。** 落地见 **§23**。

---

## 23. M1a 结果（2026-09-07）

用户确认 M1a。扩现有两把 ST-16 工具：`via`（逗号/分号，最多 6）+ `legs[]` + `totals`。次数顶仍 3。无 Place 评分、无地图 UI、不改 Pipe。地理：先无偏置；景点名跳太远且不是行政区匹配时，才用 `place/text`（`extensions=base`）回退。

直接上游（西安 → 西宁 → 青海湖 → 张掖）：**3 段** / **865.8 + 146.7 + 521.3 km** / 合计 **1533.8 km**。西宁→青海湖 **146.7 km**（不是新疆误匹配）。

Flash 烟雾（`M1A_EXPECT_LIVE=1`）：

- 北京南站→机场：1 次调用，**36.9 km / ~36 分钟 / 畅通为主**
- 西安→西宁→青海湖→张掖：1 次调用，按段写出 865.8 / 146.7 / 521.3 km
- JFK→Times Square：1 次调用，**27 km / ~60 分钟**

`verify_amap --require-key` 17 ok；`verify_google --require-key` 18 ok；`verify_stack` `VERIFY_SMOKE=0` 24 ok。JSON：`docs/open-webui-search-quality-m1a-results.json`。

**过门通过。** M1b / 画地图 / 查店 **未做**。W7 仍见 **§21**。

