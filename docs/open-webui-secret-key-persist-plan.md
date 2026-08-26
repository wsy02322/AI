# 运维密钥策略 — 轻量档（已确认）+ 可选持久化（不执行）

> **状态**：**L0 已执行**（2026-08-21）。`apply_ops_l0.py` + `verify_ops_l0.py` 已落地；K1/K2 **冻结**。  
> **日期**：2026-08-21  
> **宪法**：（2）简单稳定优先 — 容器重建后 **用户重登录可接受**；agent 脚本 **1～2 分钟** 可还原功能与契约配置。

关联：`docs/SPEC.md`（ST-OPS-*）、`AGENTS.md`（宪法）、`docs/AGENT-ONBOARDING.md`（L0 SOP）、`docs/open-webui-disaster-recovery-rebuild-plan.md`

---

## 0. 已确认的策略（L0 — 默认且唯一执行档）

| 项 | 策略 | 可接受代价 |
|----|------|------------|
| **`WEBUI_SECRET_KEY`** | env 保持 `""`；容器内 `.webui_secret_key` **不持久化**到 volume | 容器重建 → **全员重新登录** |
| **Pipe `API_KEY`** | merge 恢复（输入明文；OWUI API 保存后常为 `encrypted:`，catalog 正常即可） | Admin 误改 env 密钥导致 decrypt 失败 → merge 明文重填 |
| **`openai.api_configs`** | 5 条全 `enable: false` | 不变 |
| **OpenRouter 密钥** | **必须有**（Pipe / TTS / RAG）；丢失则从 OpenRouter 控制台重开再 merge | 无 key = 站点不可用 |
| **用户聊天 / Knowledge** | 靠 **DB / volume 备份**，不靠 JWT 持久化 | DB 全毁 = 数据不可还原 |

**明确不做（更重代价，用户已拒绝）：**

- K1：持久化 JWT 密钥到 env + data volume  
- K2：Pipe `API_KEY` 正规 `encrypted:`（与 JWT 强耦合，15:09 已证易炸 catalog）  
- VPS 脚本随意写入**新的**非空 `WEBUI_SECRET_KEY`  

**仍须单独 plan 才做：** 合规要求、多机共享同一 JWT、或 Pipe key 必须 Fernet 的场景 → 见本文 §4 可选档（当前 **冻结**）。

---

## 1. 为什么 L0 足够

1. **功能与契约配置**不依赖「同一把旧 JWT」— 都在 `webui.db` + Git scripts。  
2. **15:47 模式**已验证：catalog 空 → merge 明文 OpenRouter key → 473 模型恢复。  
3. **Pipe 明文**使 agent 恢复 **不依赖** `WEBUI_SECRET_KEY` 是否变化。  
4. 宪法第 2 条：少密钥耦合、少 VPS 纪律、少与维护脚本打架。

**JWT 持久化 / Pipe 加密的收益**：少一次重登、DB 里少明文 Pipe key。  
**代价**：env/volume 双写、重建纪律、加密与 JWT 错位 → catalog 空（已踩坑）。  
**结论**：收益 < 代价 → **默认不做**。

---

## 2. 容器重建 SOP（VPS + Agent）

升配、换容器、`docker rm` 后 recreate — **按此顺序，不必持久化 JWT**。

### VPS

1. 大改前备份 `webui.db`（聊天 / Knowledge 才需要；JWT 不需要）。  
2. `/root/open-webui.env`：**保持** `WEBUI_SECRET_KEY=""`；**禁止**写入新的随机密钥。  
3. 重建容器时保持：镜像 `e97bf9531916`、entrypoint `/custom/entrypoint.sh`、`127.0.0.1:8080`、`api_configs` 未改。  
4. 通知用户：**请重新登录**（预期行为，不是故障）。

4. Agent：`python3 scripts/apply_ops_l0.py` → `verify_ops_l0.py` → 全套 verify  
5. 通知用户：**请重新登录**

**禁止**：空 `POST /api/v1/models/sync`；启用 `openai.api_configs`。

---

## 3. 故障模式（L0 下）

| 现象 | 根因 | 修复 |
|------|------|------|
| 全员掉线 | 容器重建，新 `.webui_secret_key` | **正常** — 重登录 |
| catalog 空 + `Failed to decrypt` | env 写了**新** `WEBUI_SECRET_KEY` 且 Pipe key 为 `encrypted:` | env 改回 `""` → merge **明文** Pipe key → refresh models |
| catalog 空，无 decrypt | Pipe `API_KEY` 被清空 | merge 明文 key |
| 聊天没了 | DB / volume 丢 | 恢复 DB 备份；**不是**重填 JWT 能解决的 |

**OWUI API 行为**：经 `valves/update` 保存时，Pipe `API_KEY` 常被写成 `encrypted:`（运行时仍有 `.webui_secret_key`）。L0 验收看 **catalog 是否正常**，不是 DB 是否字面明文。decrypt 失败时仍用 **merge 明文** 恢复（与 15:47 同路径）。

---

## 4. 可选档 K1+K2（冻结，不执行）

仅当日后有 **合规 / 多机 JWT 一致** 等硬性需求时，**另开 plan、另确认** 后再执行。  
原 K1/K2 步骤保留作参考，**不是**当前运维目标：

<details>
<summary>展开：原 K1+K2 参考（勿在未确认时执行）</summary>

- K1：复用**当前** `.webui_secret_key` 写入 env + data volume（禁止 openssl rand 新密钥）  
- K2：Admin/API merge 保存 Pipe key → `encrypted:`  
- 必须先 K1 再 K2；只做 K2 会在重建时再次 catalog 空  

</details>

---

## 5. 真正要备份的（与 JWT 无关）

| 资产 | 频率 | 说明 |
|------|------|------|
| **`webui.db` / data volume** | 周备 + 大改前 | 聊天、用户、Knowledge、Pipe valves |
| **Git（SPEC + scripts + verify）** | 每次合并 | 功能契约可重建 |
| **OpenRouter 密钥** | 密码库 / OpenRouter 控制台 | 不入 git |
| **`/opt/open-webui/custom`** | 建议 VPS 侧备份 | entrypoint 不在本仓库 |

JWT / `.webui_secret_key`：**不必**单独备份。

---

## 6. 决策记录

| 日期 | 决策 |
|------|------|
| 2026-08-21 | **已执行** `apply_ops_l0.py` / `verify_ops_l0.py`；实例 5 ok + verify_stack 24 ok |
| 2026-08-21 | 默认档定为 **L0**；SPEC ST-OPS-* 与本文件一致 |
