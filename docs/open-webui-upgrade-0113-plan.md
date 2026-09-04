# OWUI 0.11.0 → 0.11.3 升级（已确认）

> **状态**：已确认执行。目标 = 官方 **v0.11.3 钉死 digest**，不是 `:main`，不是 Realtime 镜像。  
> **日期**：2026-09-04  
> **现网起点**：`GET /api/version` = **0.11.0**；镜像 digest `e97bf9531916`。  
> **升级前基线（2026-09-04）**：`verify_stack.py` **27 ok / 0 err**；Pipe sha `f797e92d6d3f`；picker **21** = public。  
> **不搭车**：Tika / 扩 Direct MIME、Notebook N2+、画图 Studio、Realtime / L2、K1/K2、空 `models/sync`、新的非空 `WEBUI_SECRET_KEY`。

BetterUI / `custom.css` 若在新前端失效：**先保聊天可用**（stock 外观），CSS 另修。不要为补丁卡住回滚。

---

## 0. 角色

| 谁 | 做什么 |
|----|--------|
| **你** | 转达下面 §1 给 VPS agent；窗口内不要挂长对话；起来后 **重登** |
| **VPS agent** | 只做 §1：备份、pull、recreate。不跑本仓库 Python、不改 Pipe、不装 Tika |
| **本仓库 agent** | 升级前 verify → 容器起来后重放脚本 + 全套 verify → 把新 digest 写入 `VERSIONS.md` / archive |

---

## 1. 转达 VPS agent（可整段复制）

**任务**：把生产容器 `open-webui` 从钉死 digest `e97bf9531916`（OWUI 0.11.0）换到官方 **`ghcr.io/open-webui/open-webui:v0.11.3`**，再把 **实际 digest 记下来**回传。不要漂 `:latest` / `:main`。不要换 Realtime 镜像（`rbb-dev/open-webui-realtime` 等）。

### 禁止

- 改 `/root/open-webui.env` 里的 `WEBUI_SECRET_KEY`（必须保持 `""`）。**禁止**写入新的随机非空密钥。  
- 启用 `openai.api_configs`。  
- `POST /api/v1/models/sync`（尤其空列表）。  
- 顺手起 Tika、改 `CONTENT_EXTRACTION_ENGINE`、扩 Direct MIME。  
- 改 Pipe valves / 重装 Pipe Function。  
- 为了补丁失败而反复 recreate；补丁挂了就用官方 `start.sh` 先起来，把失败日志回传。

### 步骤

1. **备份**（聊天 / Knowledge；JWT 不用备）  
   - 停写前复制 `webui.db`（volume 里，常见 `/app/backend/data/webui.db` 对应宿主机 bind/volume）。  
   - 例：`/root/backups/webui-before-owui-0113-$(date +%Y%m%d-%H%M%S).db`  
   - 备份 `/opt/open-webui/custom/`（entrypoint、BetterUI、`custom.css`）。

2. **记录现状**（回传）  
   - `docker inspect open-webui --format '{{.Image}} {{.Id}}'`  
   - `docker inspect open-webui --format '{{json .Config.Env}}'` 里确认有 `WEBUI_SECRET_KEY=` 空或未设非空值  
   - `docker inspect open-webui --format '{{json .HostConfig.Binds}} {{json .HostConfig.PortBindings}} {{json .Config.Entrypoint}} {{json .HostConfig.RestartPolicy}}'`  
   - 镜像 digest：`docker image inspect $(docker inspect -f '{{.Image}}' open-webui) --format '{{index .RepoDigests 0}}'`

3. **确认 env 文件**  
   - `/root/open-webui.env` 中 `WEBUI_SECRET_KEY=""`。若发现非空随机值：**停下回传，不要 recreate。**

4. **拉镜像（钉 tag，起来后再钉 digest）**  
   ```bash
   docker pull ghcr.io/open-webui/open-webui:v0.11.3
   docker image inspect ghcr.io/open-webui/open-webui:v0.11.3 --format '{{index .RepoDigests 0}}'
   ```  
   把这一行 digest **回传**（写入仓库用）。

5. **recreate（保持 volume / 127.0.0.1:8080 / env / restart）**  
   - 用**现有** compose 或 run 参数，只把 image 换成 `ghcr.io/open-webui/open-webui:v0.11.3`。  
   - 继续 bind `127.0.0.1:8080:8080`（Caddy 反代不变）。  
   - 同一 data volume。  
   - entrypoint 先仍 `/custom/entrypoint.sh`（BetterUI + 官方 `start.sh`）。  
   - 若新前端补丁失败、容器起不来：改回官方 `start.sh`（或镜像默认 entrypoint）先恢复站点，把 entrypoint 错误日志回传。CSS 可以稍后修。

6. **健康检查**  
   - 容器 running。  
   - 本机 `curl -sS http://127.0.0.1:8080/api/version` 应为 `"version":"0.11.3"`。  
   - 不要登录去点 Admin「sync models」。

7. **通知**  
   - 告诉用户：**请重新登录**（L0 预期，不是故障）。  
   - 回传：新 image digest、entrypoint 是否仍是 custom、`api/version` 输出、有无报错。

完。Pipe / public / Banner / verify 由仓库 agent 做，VPS **不要**跑 `scripts/*.py`。

---

## 2. 本仓库 agent（升级前）

- [x] 目标定为 0.11.3 钉 digest；BetterUI 失败则 stock 先可用。  
- [x] 关掉 picker 多出来的 2 个新家族：`nvidia.nemotron-3.5-content-safety`、`x-ai.grok-4.3:batch`（不进契约）。  
- [x] `verify_stack.py` 升级前绿基线：**27 ok / 0 err**（OWUI 仍 0.11.0；Pipe `f797e92d6d3f`；picker 21；烟雾 Grok/Opus/Sol/Sonar 200）。  
- [x] 其余探针（不挡换镜像）：
  - `verify_compare_cross_model.py` **5 ok / 0 err**
  - `verify_fable_thinking_replay.py` **7 ok / 0 err**
  - `verify_ops_l0.py` **5 ok / 1 err**：`/api/v1/models` 列表只有 21（inactive 仍可按 id GET）。这是列表过滤，不是 catalog 被空 sync 删光。升级后仍以 `verify_stack` 为准；不要为了「>400 行」去 `refresh` 把新家族灌进 picker。
  - `verify_live_baseline.py` **12 ok / 1 err**：TTS/STT/Call 正常。Banner `usage-guide-v3` **按契约不写** screen share（live 脚本的 needle 过期）。升级后 **不要**为绿把屏享塞回 Banner。

## 3. 本仓库 agent（VPS 起来之后）

1. `GET /api/version` 确认 0.11.3。  
2. catalog 空或 decrypt 失败 → `apply_ops_l0.py`（merge-only）。  
3. 否则跳过 L0 key 写入，仍跑：  
   `apply_plan_a_hide_integrations.py`  
   `apply_ui_guidance_banners.py`  
   `apply_wave0.py`  
   `apply_model_catalog_visibility.py`  
   `restore_public_grants.py`  
   Pipe 补丁若丢 marker：`patch_pipe_cross_model_reasoning.py`、`patch_pipe_fable_thinking_replay.py`（已有则 no-op）。ST-13 `IMAGE_DATA_URI_PERSIST_V1` 若丢了：按 `docs/open-webui-openrouter-image-continuity-plan.md` **模式**补，本瘦身树没有单独 ST-13 patch 脚本。  
4. verify：以 `verify_stack.py` 全绿为放行。compare / fable 尽量再跑。ops_l0 的「catalog <400」和 live 的「banner screen share」按 §2 已知项解读，不要为绿改契约。  
5. 把新 digest + 0.11.3 写入 `docs/VERSIONS.md`、`docs/open-webui-rebuild-archive.md`、`AGENTS.md` 容器表。  
6. 抽取引擎保持空；不要开 Tika 4 开关当升级附赠。  
7. 新版本可能多 `ask_user` / tool 审批：Sonar / 纯图像仍须无 tools；Guard + `builtin_tools=false` 不能丢。

## 4. 回滚（仅站点起不来）

VPS：image 改回 `e97bf9531916`（或备份记下的旧 RepoDigest），同一 volume / env。用户再重登。不要用空 sync「修」catalog。

---

## 5. 执行记录

| 时 | 谁 | 结果 |
|----|----|------|
| 2026-09-04 | 仓库 agent | 计划落地；picker 23→21；`verify_stack` 全绿。**等 VPS §1** |
| （待填） | VPS | pull `v0.11.3`、recreate、回传 digest / `api/version` |
| （待填） | 仓库 agent | §3 重放脚本 + verify；钉子改成新 digest |
