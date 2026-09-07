# 即时搜顶级档：地图 + X + 平均 spike ≤ `$0.2`

> **状态**：用户已选 **顶级档**。**W0 / W1 / W2 / W3 / W4 已过门**。xAI / Google 类 Search+Fetch = `native`。OpenAI 仍 Exa。W6 仍关。  
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
- OpenAI：**Exa**；**Google：`native`**（W2）；**xAI：`native`**（W3）；Anthropic：`auto`；中国三只：`auto`→Exa。  
- T1 `SEARCH_PAGE_COMPACT_V1`；`$0.05` / `step_count=8`；OpenRouter 写明 `max_uses` **只转 Anthropic**。  
- 无 X 原厂、无 T2、无单发 token 顶。  
- **ST-16**：`amap_drive_route` + `google_drive_route` 已挂 12 个 public 文本；高德 / Google Maps Key **已注入** Valves（不进 git）。  
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
| **W1** 高德路线 | **已过门**。Tool `amap_drive_route` 挂 12 个 public 文本；Key 在 Valves。压缩 JSON、次数顶=3、无 UI。见 **§11** | Flash 正文有距离/时长/路况大意，无「路线接口不可用」、无电话/评分 | `scripts/rollback_amap_drive_route.py` |
| **W2** Gemini native | **已过门**。Google 类 Search+Fetch `engine=native`。OpenAI 仍 Exa。见 **§14** | Flash 短问 4 次搜 / `$0.056`；北京南站→首都机场走高德 36.7km / 41 分钟，0 次网页搜 | 改回 `exa` |
| **W3** Grok native | **已过门**。xAI 类 Search+Fetch `engine=native`。见 **§13** | 能引用 X；网页即时搜仍出活链；Grok「继续」超额符合 §1.1 | 把 xAI 改回 `exa` 后 `apply_search_quality_w3.py` 的逆操作（Filter content） |
| **W4** Google Routes | **已过门**。Tool `google_drive_route` 挂 12 个 public 文本；Key 在 Valves。见 **§16** | Flash 海外 27km / 57 分钟；国内仍高德 36.7km / 41 分钟 | `scripts/rollback_google_drive_route.py` |
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

**W0 / W1 / W2 / W3 / W4 已过门**（§10–§11、§13–§14、§16）。**不要自行开 W5 / W6。** W5 见 **§17**（先选上游或明确不做）。W6 仍关。


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

W0 已接受 Grok 续轮可 >4 次搜。**W2 Gemini native 已过门**（§14）。W5 全模型 X、W6 OpenAI native **未做**。

---

## 14. W2 结果（2026-09-07）

薄 Filter content-only：Google 类 `web_search` / `web_fetch` **`engine=native`**（marker `TEXT_WEB_SEARCH_GOOGLE_NATIVE_V1`）。OpenAI 仍 Exa（W6 关）；xAI 仍 native；Anthropic 仍 auto。Pipe **未改**（`9c4836ace251`）。OWUI native Web Search **仍关**。未重开 broad Web Tools。

Flash 3.8 烟雾（`$0.059`）：

- 短问（OpenAI 本周产品新闻）：4 次搜 / `$0.056`，正文有活链。
- 中国路线（北京南站→首都机场）：`function_call_count=1`，**0 次网页搜**，正文 **36.7 公里 / 约 41 分钟 / 畅通为主**。无「路线接口不可用」，无电话/评分。

`verify_text_web_search.py --mode final` 17 ok；`verify_stack.py` `VERIFY_SMOKE=0` 24 ok。JSON：`docs/open-webui-search-quality-w2-results.json`。

**过门通过。** 中国路况仍走高德，不是 Google 网页搜。W5 / W6 **未做**。

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

**过门通过。** W5 见 **§17**（未确认）。W6 **未做**。

---

## 17. W5 沟通：其他模型读 X，相对 Grok 差在哪（未确认，不施工）

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

回 `W5：X API 按次` / `W5：xAI 侧车` / `W5：不做`。需要数字再回 `W5：先对照`。

### 17.3 非 Grok 最高性价比（2026-09-07 沟通，未施工）

OpenRouter **不会**把 Grok 的 `x_search` 分给 Gemini / OpenAI / Claude。W2 Google native 仍是网页，不是 X。

xAI 文档里的 `x_search` 是 **Grok 身上的 server tool**（`$5` / 1k 次 = 每次搜 `$0.005`，另加 Grok token）。不能直接挂到 Flash/Opus。要给别的模型用，只能再包一层「让 Grok 只搜 X → 压缩卡片」，多一跳、多 token，还可能触发 ToS。

官方 X API 2026 新号是 **按次**（旧 Basic `$200`/月已不对新用户开）：第三方帖大约 **`$0.005` / 条返回**，按返回条数计，不是按请求。无月租底板。

| 方案 | 非 Grok 拿到什么 | 大约 `$` | 复杂度 | 性价比 |
|------|------------------|----------|--------|--------|
| **不做**（X 题用 Grok） | 无 | `$0` | 零 | 问 X 少时最优 |
| **官方 X API 按次 + 薄工具** | 近 7 天关键词真帖 + `x.com/status` | 每问 5～8 条 ≈ `$0.025`～`$0.04`；顶 3 次 ≈ `$0.12` | 中（和路线工具同形） | **要真帖时最优** |
| xAI 侧车（便宜 Grok + 只 `x_search`） | 接近 Grok 同源（语义/线程） | `$0.005`/搜 + Grok token；Grok 可能连搜几次 | 高 | 质量更好，`$` 和复杂度都更差 |
| 继续网页搜 | 新闻转述 / 旧帖 / 易编链 | 已付网页搜 | 零 | 便宜但经常不是 X |

**性价比主推（若一定要非 Grok 读 X）**：官方 X 按次 + 与高德同形的薄 Tool；`max_results=5～8`；每轮最多 2～3 次；只回作者/时间/摘要/链接。不挂 Sonar/图像。失败说「X 接口不可用」。

不采用：Nitter、为 X 去开 OpenAI native、把网页搜写成已接 X。

