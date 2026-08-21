# WEBUI_SECRET_KEY 持久化 + Pipe API Key 正规加密 — 方案

> **状态**：v1 **规划，未执行**。确认前不改实例、不改 VPS 容器。  
> **日期**：2026-08-21  
> **触发**：VPS 维护摘要（13:37–16:05 UTC）建议两项后续：持久化 `.webui_secret_key`；用 Admin 重填 Pipe API Key，而不是长期 DB 明文。  
> **宪法**：（1）能力不降；（2）务必简单稳定、易维护；（3）重大改动先 plan、确认后再执行。

关联：`docs/SPEC.md`、`AGENTS.md`、`docs/open-webui-disaster-recovery-rebuild-plan.md`、`docs/open-webui-delta-vs-stock.md`

---

## 0. 这不是什么

| 易混项 | 本方案 |
|--------|--------|
| 再生成一把新的 `WEBUI_SECRET_KEY` | **禁止**。那会让已重新登录的用户再掉一次线，且与即将加密的 Pipe key 再次错位 |
| 启用 `openai.api_configs` | **禁止**。模型只走 Pipe |
| 换 OWUI 镜像 / 拆 custom entrypoint | **禁止** |
| 修 P0-B/C Live 或 N2 Notebook | 无关；本方案只修运维稳定性 |
| 把密钥写入本 Git 仓库 | **禁止** |

---

## 1. 当前现场（验收仍绿，但运维脆弱）

截至 2026-08-21 本 agent 探针：`verify_stack` 24 ok、catalog **473**、N1 / Live L1 仍绿。

| 项 | 现状 | 风险 |
|----|------|------|
| `/root/open-webui.env` `WEBUI_SECRET_KEY` | `""` | `start.sh` 从容器内文件加载 |
| 运行时密钥文件 | `/app/backend/.webui_secret_key`（15:35 生成） | **不在** data volume `open-webui` → **下次容器重建会再生成** → 全员掉线 |
| Pipe `API_KEY` | DB **明文** `sk-or-v1-…` | catalog 能活，是因为明文不走 Fernet |
| `openai.api_configs` | 5 条全 `enable: false` | 刻意；勿改 |
| 本 agent SSH | **无** | K1 必须 VPS 侧执行 |

官方 `start.sh` 行为（与现场一致）：

1. env **非空** → 直接用 env，**忽略** `.webui_secret_key`
2. env **空** → 读 `WEBUI_SECRET_KEY_FILE`（默认 WORKDIR 下 `.webui_secret_key`）；没有则 **新生成**
3. 再 `exec env WEBUI_SECRET_KEY=… uvicorn`，所以 Python 进程里始终有密钥

Pipe `EncryptedStr`：有运行时 `WEBUI_SECRET_KEY` 时，Admin/API **保存** valves 会写成 `encrypted:gAAAAA…`。下次启动若密钥变了 → `Failed to decrypt` → **模型列表空**。这就是 15:09 写入**新** env 密钥后的故障。

**明文是陷阱，不是稳态：** 任何人在 Admin 点一次 Pipe Valves「保存」，就会用**当时**运行时密钥加密。若密钥仍不持久，下一次重建容器 = 再次 catalog 空。

因此：**只做加密、不做持久化 = 主动埋雷。必须先 K1，再 K2。**

---

## 2. 对照宪法的两档

| 档 | 做法 | 简单/稳定 | 能力 | 须你点头 |
|----|------|-----------|------|----------|
| **推荐（K1+K2）** | 复用**当前**运行时密钥写入 env + data volume；再 Admin/API 重保存 Pipe `API_KEY` 让其加密 | 官方推荐路径；重建不再掉线、不再空 catalog | 用户无感（不换密钥则 **不必再登录**） | 本 plan 默认请确认这一档 |
| **略降级（仅 K1）** | 只持久化密钥，Pipe 继续明文 | 更少一步；Admin 误保存仍会加密 | 同等能力；DB 里密钥仍明文 | 若你想少动 DB |

**不推荐：** 用 `openssl rand` 生成新密钥再写入 env（维护批次 1 已踩过）。  
**不推荐：** 只改 custom entrypoint 拷贝文件、env 继续空——多一段分叉，且 VPS 脚本仍可能再写入新 env 密钥。

---

## 3. 推荐方案拆步

### K1 — 持久化**当前**密钥（VPS，须重建容器一次）

目标：JWT 签名密钥跨容器重建不变。

1. **备份** `webui.db` 与当前 `/root/open-webui.env`（例：`/root/backups/webui-secret-persist-YYYYMMDD.db`）。  
2. 从**正在运行**的容器取出当前密钥（**禁止**新生成）：

   ```bash
   docker exec open-webui sh -c 'cat /app/backend/.webui_secret_key'
   ```

3. 把**同一串**写入 `/root/open-webui.env`：

   ```
   WEBUI_SECRET_KEY="<当前文件内容，去掉换行>"
   WEBUI_SECRET_KEY_FILE="/app/backend/data/.webui_secret_key"
   ```

   其它行（`WEBUI_URL` / CORS / cookie secure）**不动**。  
4. 写入 volume（双保险；env 被清空时 `start.sh` 仍能从 data 读）：

   ```bash
   docker exec open-webui sh -c \
     'cp /app/backend/.webui_secret_key /app/backend/data/.webui_secret_key && chmod 600 /app/backend/data/.webui_secret_key'
   ```

5. **重建**容器，约束与现场一致：

   | 必须保持 | 值 |
   |----------|-----|
   | 镜像 | `e97bf9531916` |
   | 端口 | `127.0.0.1:8080:8080` |
   | Entrypoint | `bash /custom/entrypoint.sh` |
   | 挂载 | custom css/js + `/opt/open-webui/custom` + volume `open-webui` |
   | env 文件 | `/root/open-webui.env`（此时密钥非空且 **等于** 旧文件） |
   | `openai.api_configs` | **不改**，保持全 false |

   `docker restart` **不够**：已创建容器的 env 不会跟着 env 文件变。

6. 冒烟（VPS + 本 agent）：

   - 容器 healthy；`docker exec` 看 `WEBUI_SECRET_KEY` 非空且与重建前文件一致  
   - 已登录会话 **仍有效**（密钥未变）  
   - **无**新的 `Failed to decrypt`（此时 Pipe 仍是明文，本来也不会 decrypt）  
   - 本 agent：`python3 scripts/verify_stack.py` 全绿、catalog 仍 473  

**K1 完成前禁止 K2。**

### K2 — 正规加密 Pipe `API_KEY`（本 agent，OWUI API）

目标：DB 不再长期明文；与运行时密钥配对。

1. **Merge** Pipe valves：只写 `API_KEY` = 现用 OpenRouter 明文（来源仍是 `openai.api_keys[0]` 或当前 GET valves 返回值），**禁止**全量覆盖其它 valves。  
2. 服务端 `EncryptedStr` 会写成 `encrypted:…`。  
3. `GET /api/models?refresh=true` → catalog 仍为 Pipe 前缀、规模约 473。  
4. **禁止** `POST /api/v1/models/sync` 空列表。  
5. 若 public grants 被冲：`scripts/restore_public_grants.py`。  
6. VPS 抽查（不要把密钥贴进 git / PR）：

   ```sql
   -- 只看前缀，不打印全文
   SELECT substr(json_extract(valves,'$.API_KEY'),1,12)
   FROM function
   WHERE id='open_webui_openrouter_integration';
   -- 期望：encrypted:gA
   ```

7. `verify_stack.py` + `verify_live_baseline.py` + `verify_notebook_youtube.py` 全绿。

正规入口等价于 Admin → Functions → Open WebUI OpenRouter Integration → Valves → 重填 API Key → Save。API merge 与点保存是同一条加密路径；本 agent 无浏览器也可做。

### K3 — 文档与防再踩（本 agent，不改实例）

更新 `AGENTS.md` / `VERSIONS.md` / delta / 灾备：

- env **可以且应当** 持有**稳定**的 `WEBUI_SECRET_KEY`（= 当前文件，不是新随机串）  
- VPS 脚本 **禁止** `openssl rand` / 空文件检测失败后写新密钥  
- 重建容器必须带同一 env 文件  
- `api_configs.enable` 仍全 false  

---

## 4. 明确不做

- 不换镜像、不改 Caddy、不动 GoogleBanana  
- 不启用 OpenAI 直连槽  
- 不把密钥、JWT、DB dump 提交进 git  
- 不改 Pipe `content` / Guard / Banner / RAG / Knowledge  
- 不把 `.webui_secret_key` 只拷到宿主机却不挂进 volume/env（重建仍丢）

---

## 5. 执行分工

| 步 | 谁 | 本 Cloud Agent 现状 |
|----|----|---------------------|
| K1 | **VPS 维护 agent**（root + docker） | **无 SSH**，不能替你 docker recreate |
| K2 | **本 Open WebUI agent**（已有 Admin JWT） | K1 冒烟通过后执行 |
| K3 | 本 agent | 随 K2 一起改文档 |

若你希望本 agent 连 K1 一起做：需要 VPS SSH（或把 recreate 脚本交给 VPS agent 按本 plan 跑）。

---

## 6. 成功标准

| 检查 | 通过 |
|------|------|
| 已登录用户 | **不必**因本次变更再登录（密钥未轮换） |
| 再做一次「删容器重建」（演练可选） | 会话仍在；catalog 非空 |
| Pipe `API_KEY` | DB 以 `encrypted:` 开头 |
| `openai.api_configs` | 仍全 false |
| `verify_stack.py` | 24 ok / 0 err，catalog ~473，19 public |
| Live / Notebook | `verify_live_baseline` / `verify_notebook_youtube` 不回归 |
| 日志 | 无新的 `Failed to decrypt` / `invalid token or key mismatch` |

---

## 7. 回滚

1. 停容器。  
2. 用 K1 前的 `webui.db` 备份恢复 volume 内数据库（会丢掉 K1 之后的新聊天）。  
3. env 中 `WEBUI_SECRET_KEY` 改回 `""` 并去掉 `WEBUI_SECRET_KEY_FILE`（或改回 K1 前 env 备份）。  
4. 按现场约束重建容器。  
5. 若只想撤销 K2：把 valves `API_KEY` merge 回明文（与 15:47 应急相同）；**仍建议保留 K1**，否则下次保存又会加密并在重建时炸掉。

15:47 备份仍在：`/root/backups/webui-valves-fix-20260821-154729.db`（K1 前请再做一份新的）。

---

## 8. 请你确认（未勾选 = 不执行）

- [ ] **采纳推荐档 K1+K2**（复用当前密钥，不新生成）  
- [ ] **K1 由 VPS 维护 agent 执行**；完成后把「密钥已写入 env 且与旧文件一致、容器 healthy」回传本 agent  
- [ ] **K1 通过后本 agent 执行 K2 + K3 + verify**  
- [ ] 保持 `api_configs` 全 false、镜像 `e97bf9531916`、custom entrypoint  

若改选 **仅 K1**：注明即可；K2 以后再说，但须接受「Admin 误保存仍会加密」。
