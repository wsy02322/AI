# gpt-audio 体验对照 — 最小实验（GA-A 已执行）

> **状态**：v1 **已执行（2026-08-21）**。结论：**Pipe/OWUI 未接通 `output_audio`**；维持 L1、不改 Call、不 public。  
> **日期**：2026-08-21  
> **已探针**：catalog 含 `open_webui_openrouter_integration.openai.gpt-audio` 与 `…gpt-audio-mini`（**非** 19 public）  
> **脚本**：`scripts/run_ga_a_trial.py`（`verify_stack` 须先全绿）

关联：`docs/open-webui-live-voice-screen-plan.md`（gpt-audio **不做** Call 捷径）

---

## 0. 值不值得试（本实验的结论前提）

| 试法 | 值得？ | 原因 |
|------|--------|------|
| **GA-A**：聊天/API 对照音色与一轮延迟 | **值得（信息量）** | 模型已在 catalog；不改架构；用实测替换猜测 |
| **GA-B**：改 Call overlay 走 gpt-audio | **不值得** | 前端分叉；仍无 barge-in；锁 OpenAI；SPEC Don't |

本文件 **只批准 GA-A**。GA-B 维持 Don't。

---

## 1. 实验要回答的问题（写死，避免漂成「上了 Voice」）

1. 同一句中文短句：MiniMax Read Aloud vs `gpt-audio` / `gpt-audio-mini` 音频，**听感**是否明显更好？  
2. 一轮「用户短语音 → 模型口头回答」：相对 L1（Whisper → Grok → MiniMax），**首响/整段耗时**差多少？（秒，记墙钟，不编百分比）  
3. Pipe 是否真能返回可播音频（`output_audio` / 文件），还是只回文本？  
4. 费用：同一次短请求的 OpenRouter usage，对比 L1 三段。

**不回答**：能否打断、能否持续屏享、能否替代 Grok/Opus 聊天。

---

## 2. 允许改什么 / 禁止改什么

**允许**

- Admin 用已有模型 id 发 **非 public** 聊天或 API 烟测  
- 临时日志：延迟、status、是否含 audio blob（**不**把密钥/音频全文入库）  
- 结束后把数字写入本文件 §5；不扩 19 public

**禁止**

- 改 Call overlay / STT / TTS 全局配置  
- `model/update` 把 gpt-audio 设 public  
- 换镜像、开 Realtime、改 `openai.api_configs`  
- 空 `models/sync`、覆盖 Pipe valves  

---

## 3. 步骤（约一次会话内完成）

1. `verify_stack.py` 基线（须仍全绿）。  
2. API：`gpt-audio-mini` 优先（更便宜），失败再 `gpt-audio`。  
   - 文本进：请模型用一句话口头说「OK，这是音频测试。」  
   - 若 Pipe 不返回 audio：记 **失败模式**（只文本 / 400 / 无 modalities），**停止加码改 Call**。  
3. 对照：同一句走现有 `/audio/speech` MiniMax。  
4. 可选：一段 3s 用户音频（自己录）→ gpt-audio 理解并口头答；对照 L1 Call 同句（手工计时即可）。  
5. 记表：模型、HTTP、有无音频、墙钟秒、听感（明显更好 / 差不多 / 更差）、是否值得再投入。

---

## 4. 通过 / 停手

| 结果 | 下一步 |
|------|--------|
| 无音频或 4xx/5xx | **停**。文档记「Pipe/OWUI 未接通 output_audio」；不改 Call |
| 有音频，听感不明显好于 MiniMax | **停**。维持 L1 |
| 听感明显好，但仍回合制 | **仅记录**；不自动 public、不改 Call；Voice 顶级仍走 Realtime 或 L-park |
| 想改 Call | **新 plan + 再确认**（本实验授权不够） |

---

## 5. 实测（2026-08-21）

**基线**：`verify_stack.py` **24 ok / 0 err**（同会话先跑）。  
**测试句**：`OK，这是音频测试。`  
**gpt-audio 请求**：`modalities=["text","audio"]`，`audio={voice:alloy,format:wav}`，`stream=true`（OpenRouter 文档要求）。

**§1 四问覆盖**

| 问题 | 状态 |
|------|------|
| 1 听感 vs MiniMax | **未答**（gpt-audio 无音频样本，无法 A/B） |
| 2 一轮语音延迟 vs L1 | **未答**（步骤 4 可选；文本出音频已失败，未做 Call 对照） |
| 3 Pipe 能否返回可播音频 | **已答：不能**（见下表） |
| 4 usage / 费用 | **未答**（三列 `usage` 均为 null） |

**墙钟说明**：MiniMax 列为 **整段下载**（`/audio/speech` 完整 MP3）。gpt-audio 列为 **N/A（不可与 MiniMax 比整段生成）**；脚本 `wall_s` 为 **SSE 读完**（仅错误 Markdown，无音频），复跑约 **~1.1s / ~0.6s**，只说明错误卡片到达/读完速度，**不是**语音生成耗时。

| 项 | MiniMax L1 | gpt-audio-mini | gpt-audio |
|----|------------|----------------|-----------|
| 有可播音频 | **是**（MP3 31149 B） | **否** | **否** |
| HTTP | 200 | 200（流内错误文案） | 200（流内错误文案） |
| 墙钟（s） | **1.62**（整段） | **N/A**（TTFB/SSE ~0.49） | **N/A**（TTFB/SSE ~0.46） |
| 听感 | **基线** | 无样本 | 无样本 |
| usage | — | null | null |
| 备注 | `/api/v1/audio/speech` → `minimax/speech-2.8-turbo` | Pipe **`/responses`** 路径：`modalities[1]` 只允许 `text\|image`，**拒 `audio`** → OpenRouter `Invalid Responses API request` | 同 mini |

**失败模式（写死）**：非 4xx/5xx，而是 **HTTP 200 + SSE 错误 Markdown**（非成功纯文本）；**零** `delta.audio` / 文件 blob。OpenRouter raw：`invalid_value` on `modalities` → expected `text|image`。

**根因范围（写死）**：证据支持 **Pipe `/responses` 不接受 `modalities.audio`** → 经 OWUI 聊天 API **无 `output_audio`**。**未**证明 OpenRouter 直连 chat/completions 不可出音频；**未**做去 `modalities` 纯文本对照。

**GA-A 结论（§4 第一行）**：**停**。不在 OWUI/Pipe 上为 gpt-audio 加码改 Call；Voice 顶级仍 L-park / Realtime 路线。GA-B 维持 Don't。

**产物**：`/opt/cursor/artifacts/ga_a_minimax_l1.mp3`、`ga_a_results.json`（密钥/全文音频未入库）。

---

## 6. 请确认

- [x] 执行 **GA-A**（不改 Call、不 public）  
- [x] 不执行 GA-B  
