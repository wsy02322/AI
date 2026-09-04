# 文件录入 / 解析 — 方案（封存）

> **状态**：v1 **已封存**（2026-08-29）。**T0 未确认，不改实例 / 不装 Tika / 不改 Pipe。**  
> **产品目标（2026-09-03）**：文件上传对标 ChatGPT / Grok / Claude **官网最高档**。实现仍须单独确认。  
> **日期**：2026-08-29  
> **优先级**：Later（须单独确认）。**不是** P0 四条之一，也**不是** P0-D Notebook/YouTube。  
> **宪法**：（1）顶级与略降级一并提案、确认再选；（2）简单稳定易维护；（3）重大改动主动 plan/提案，确认后再执行（讨论≠执行）。

关联：`docs/SPEC.md`、`docs/open-webui-notebook-youtube-plan.md`（Knowledge ≠ 本方案）

---

## 0. 这不是什么

| 易混项 | 本方案 |
|--------|--------|
| 把 Direct Uploads 默认全开 / 扩 MIME 到 docx/xlsx/pptx | **Don't**。多数上游拒或当乱码；fail-open 会假装「原生吃 Office」 |
| OpenRouter Files API + sandbox | Later（T2）。beta，要改 Pipe，不是拧阀门 |
| P0-D Knowledge / YouTube | 资料库与视频理解。本方案是 **聊天附件怎么进模型** |
| Wave 1 视频生成 / Wave 2 slides | 创作。本方案是读已有文件 |
| 换 OWUI 镜像上 Tika 4 | **Don't（T0）**。见 §6 |
| 第二前端 / 直连 OpenAI Files | Don't |

**结论（写死）**：不要把 Direct Uploads 撑成「官网级文件录入」。默认走更好的文字抽取 + Knowledge；Direct Native 只留给「这一份带图 PDF 要模型亲眼看」。

---

## 1. 官网实际在做什么（2026-08 核对）

官网「什么文件丢进去都会」是**几条流水线**，不是一条 Native 直传。

| 产品 | 日常 Office / 数字 PDF | 带图 PDF | Excel 真算 | 资料库 |
|------|------------------------|----------|------------|--------|
| ChatGPT Plus | **抽文本**再问答 | **丢内嵌图**（Visual Retrieval 只在 Enterprise 对话上传） | Code Interpreter | Library + 检索 |
| Gemini 应用 | 多数格式；约 100MB、每轮约 10 个 | 常当页来看 | 弱于 ChatGPT 沙盒 | Drive / Notebook 另线 |
| Grok 官网 | 消费者面窄于 API；xlsx/pptx 常要先转 | API 侧 PDF 更完整 | 无官网级透视验算 | 弱 |

Direct 只覆盖「原件 base64 进模型文件槽」。ChatGPT Plus 日常 Office **本来就不是**视觉直传。本栈用配置做同样的分流，不改 Pipe。

---

## 2. 本实例探针（2026-08-29）

`GET /api/v1/retrieval/config` + `GET /api/version`：

| 项 | 值 |
|----|-----|
| OWUI | **0.11.0**（当时镜像 `e97bf9531916`）。**2026-09-04** 起现网为 **0.11.3**（`129f4038ec70`）；本表抽取探针未重跑，引擎仍空 |
| `CONTENT_EXTRACTION_ENGINE` | **空** → 内置 `PyPDF` / `Docx2txt` / `PptxLoader`（幻灯片只抽文本框） |
| `TIKA_SERVER_URL` | 默认占位 `http://tika:9998`（引擎未开，**没有在用 Tika**） |
| `PDF_EXTRACT_IMAGES` | `false` |
| `RAG_FULL_CONTEXT` | `false`（默认切块） |
| Direct Uploads Filter | `is_active=true`，**非 global**；UserValves 默认关 |
| Direct 白名单 | PDF / txt / md / json / csv；单文件/合计 **50MB**；默认解析器 Native |
| `TIKA_SERVER_VERSION` | **无**（0.11.1 才有） |

Office 空内容、表格散、旧 `.doc/.xls` 抽失败，是**默认引擎**短板，不是 Direct 没开满。

---

## 3. 双轨（人分流，不要自动全开）

| 用户丢进来的东西 | 走哪条 | 不要走哪条 |
|------------------|--------|------------|
| 一份带图 / 签章 / 分栏的 PDF | Direct + Native + Grok / Opus / Gemini | Knowledge 纯抽文本 |
| 扫描件 / 照片 PDF | Direct + Mistral OCR，或 T0 之后 Tika + OCR | Native 硬啃糊扫描 |
| 干净数字 PDF、说明书、合同库 | Knowledge + RAG；特别短再用 Full Context | 每轮 Direct Native |
| Word / PPT 原件，只求读懂 | **T0：Tika 抽取**，聊天或 Knowledge | 把 Direct MIME 撑开塞 `type:file` |
| 小 CSV | Tika 或 CSV 进上下文 | 指望口算大表 |
| 要验算透视 / 出图 | T1 Open Terminal（须另确认）；短期导出 CSV | Direct 或 Files API |
| 音视频 | Direct 音频/视频阀，或 P0-D Notebook | 和文档录入混成一条产品 |

默认便宜、可检索、可复用；贵的视觉直传只当开关。

---

## 4. 档位（确认再选）

| 档 | 做什么 | 复杂度 | 状态 |
|----|--------|--------|------|
| **T0** | 同网络钉死 **Tika 3.x-full**；Documents 引擎改 Tika；Direct 默认关；分流说明 | 新 JVM 容器 + 改 `rag.*` | **封存，未确认** |
| **T1** | Open Terminal：附件进容器，pandas/shell 真算 | 4GB 级镜像；0.11.1 才有聊天上传进文件系统；多用户生产要 Enterprise Terminals | Later |
| **T2** | Pipe 接 OpenRouter Files API + sandbox | beta；改 Pipe/Filter；全球端；100MB / 10GiB | Later |
| Don't | 扩 Direct MIME；Docling/Marker/LlamaParse 当第一刀；为 Tika 4 换 OWUI 镜像；第二前端 | — | 默认不做 |

**T0 是略降级、简单稳定特别多的方案**：接近 ChatGPT Plus「抽文本再问」，不接近 Library / 512MB / Enterprise 视觉检索 / Code Interpreter。  
**T2 是更接近官网产品壳的顶级路径**，代价是 beta + 改 Pipe。未确认不得当 T0 的替代执行。

Docling 表/版式优于 Tika，运维（worker、超时）更重，不作为第一刀。

---

## 5. T0（确认后才执行）

### 5.1 允许

- 与 `open-webui` **同一 Docker 网络**加 Tika 容器  
- 镜像钉死 **`apache/tika:3.3.0.0-full`**（或 `3.2.3.0-full`）。**禁止** `latest` / `latest-full`  
- Admin → Documents：`CONTENT_EXTRACTION_ENGINE=tika`（**不是**旧名 `TEXT_EXTRACTION_ENGINE`）  
- URL：**`http://tika:9998`**（不要加 `/tika`；OWUI 自拼 `/tika/text`）  
- `PDF_EXTRACT_IMAGES` **先保持 false**  
- Direct **默认关**；不改 MIME、不改 Pipe valves（只 merge 的纪律仍适用，本步不应碰 Pipe）  
- 验收：新传一份 docx / pptx / xlsx / 数字 PDF，能抽出正文  
- 已有 Knowledge **不会**自动重解析；要新引擎效果须再传  

### 5.2 禁止

- 把 Tika **9998 打到公网**（只内部或 `127.0.0.1`）  
- 从 OWUI 容器填 `localhost:9998`（那是 OWUI 自己）  
- 换 OWUI 镜像、开 `openai.api_configs`、空 `models/sync`、覆盖 Pipe `API_KEY`  
- 默认打开 Direct / 扩白名单  
- 把 Tika 写成「Markdown 表引擎」或「省 80% token」（过誉；Tika 抽的是文本/XHTML，表不如 Docling）  
- 为 T0 全量 `verify_stack` 四次 live smoke；Documents 改完用抽取烟测即可  

### 5.3 验收（T0）

1. Tika 容器健康：`GET http://tika:9998/tika` 从 **OWUI 所在网络**可达  
2. `retrieval/config`：`CONTENT_EXTRACTION_ENGINE=tika`，`TIKA_SERVER_URL=http://tika:9998`  
3. 上传 docx / pptx / xlsx / 数字 PDF 各一，聊天里能问到正文（Direct 关）  
4. Direct 仍默认关；开 Direct + Native 仍只对 PDF 白名单生效  

---

## 6. 为什么 T0 不用 Tika 4、不换 OWUI 镜像

两面「镜像」不要混：

| 镜像 | T0 |
|------|-----|
| `apache/tika:…` | 钉 **3.x-full** |
| OWUI `129f4038ec70`（0.11.3） | **T0 仍不动镜像**（升级已另做） |

0.11.0 的 `TikaLoader`：`PUT /tika/text` + `r.json()` + `X-TIKA:content`。  
Tika 4 的 `/tika/text` 改为纯文本；JSON 键改为 `tk:`。对上 4 → `JSONDecodeError`。  
`TIKA_SERVER_VERSION`（3→`/tika/text`，4→`/tika/json/text` + `tk:content`）是 **OWUI 0.11.1** 才有的。升 OWUI 会带走 BetterUI entrypoint、L0、Pipe 补丁、19 public。无 Realtime 钥匙时本来就不换镜像。

[Tika 4.0.0](https://tika.apache.org/4.0.0/) 相对 3.x：默认 Markdown、解析进 fork（坏文件不拖死 server）、配置 XML→JSON、Java 17+、每个 worker 单独堆。3.x 仍受支持。  
OWUI 0.11.1 接 4 时走 **`/tika/json/text`**，不是 `/tika/json/md`，**默认 Markdown 进不了 RAG**。fork 隔离还要按核数留内存。  
T0 要的「Office 读全」，3.x 已够。Tika 4 不值「换整站」；表/版式要明显好一档应另评 Docling，不是 Tika 4。

今日 Docker `latest-full` 仍指向 3.3 线，4.x 以版本 tag 发预览；仍禁止 `latest`，避免以后漂到 4。

---

## 7. T1 / T2（只记录，不施工）

**T1 Open Terminal**：对标官网 Code Interpreter。OWUI 文档已把它标成正式代码执行路径；Pyodide 遗留。聊天附件自动进终端文件系统是 **0.11.1**。单容器 `OPEN_TERMINAL_MULTI_USER` 只适合受信任小团队；生产隔离要 **Terminals + Enterprise**。ST-7：Sonar / 纯图像不得开 terminal。比 Tika 重一档。

**T2 Files API**：上传一次、`file_id` 复用、可挂 sandbox。仍 beta；只走 `openrouter.ai` 全球端；单文件 100MB、工作区约 10GiB；上传件不能按原件再下载。等于新 Pipe 能力。

---

## 8. 规划 ID（封存即约束 Agent；T0 未确认不改实例）

| ID | 必须 |
|----|------|
| ST-FILE-1 | 不把 Direct 默认全开或扩 MIME 冒充官网录入 |
| ST-FILE-2 | T0 只用钉死的 Tika **3.x-full**；OWUI 0.11.x 不对 Tika 4 |
| ST-FILE-3 | Tika URL 为 `http://tika:9998`；不发布公网 9998 |
| ST-FILE-4 | 未确认不装 Tika、不改 `CONTENT_EXTRACTION_ENGINE`、不改 Pipe |
| ST-FILE-5 | T1/T2 / Docling / 换 OWUI 镜像 **另确认**；不得塞进 T0 |
| ST-FILE-6 | 本方案 ≠ P0-D YouTube ingest ≠ Wave 1 视频生成 |

---

## 9. 请你拍板

| | 选项 |
|--|------|
| **E0** | 只保持本文件；实例不动（**当前**） |
| **E1** | 执行 T0（钉 Tika 3.x-full + Documents 改引擎 + 抽取烟测） |
| **E2** | 另开 T1（Open Terminal）plan，不与 T0 绑死 |
| **E3** | 另开 T2（Files API）plan，仍须再确认才改 Pipe |

**现在不做：** 装 Tika、改 Documents、改 Direct、改 Pipe、换镜像。

---

## 10. 参考

- OpenAI File Uploads FAQ：https://help.openai.com/en/articles/8555545  
- ChatGPT Visual Retrieval（Enterprise）：https://help.openai.com/en/articles/10416312-visual-retrieval-with-pdfs-faq  
- Gemini Apps 上传：https://support.google.com/gemini/answer/14903178  
- OpenRouter PDF Inputs：https://openrouter.ai/docs/guides/overview/multimodal/pdfs  
- OpenRouter Files API（beta）：https://openrouter.ai/docs/guides/features/files-api  
- rbb Direct Uploads：https://github.com/rbb-dev/Open-WebUI-OpenRouter-pipe/blob/main/docs/openrouter_direct_uploads.md  
- OWUI Tika 文档：https://docs.openwebui.com/features/chat-conversations/rag/document-extraction/apachetika/  
- Tika 4.0.0：https://tika.apache.org/4.0.0/  
- OWUI 0.11.1 Tika 4 开关：https://github.com/open-webui/open-webui/releases/tag/v0.11.1  
- Open Terminal / Code Execution：https://docs.openwebui.com/features/chat-conversations/chat-features/code-execution/  

*未确认执行步之前不改实例。*
