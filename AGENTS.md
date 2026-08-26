# AGENTS.md — 宪法（当前 Agent 唯一自动注入准则）

当前 session：只遵守下面宪法与 P0 并列。**不要主动打开** `docs/AGENT-ONBOARDING.md`。  
新 session / 新 Agent：开工前读 `docs/AGENT-ONBOARDING.md`。产品契约：`docs/SPEC.md`。

## 宪法

1. 媲美甚至超越 ChatGPT / Grok 等最顶级付费档。特别困难复杂：**先确认**是否改用略微降级、简单稳定特别多的方案。  
2. 务必简单和稳定，优先易维护。  
3. 重大改动：先 plan，确认后再执行。  
4. **一般情况不开浏览器**，也不录屏、不截屏。优先脚本与终端/日志。仅当你明确要求，或改了本仓库前端代码且脚本无法证明时才开浏览器。  
5. 验收跟改动走：Banner / Suggested / Description 只跑对应 apply 的自带校验。**禁止**为此全量 `verify_stack`（4 次 live smoke）、禁止重写未改的 Description。全量 verify 仅 Pipe / Guard / catalog / 模型能力。  
6. 动实例时禁止：空 `POST /api/v1/models/sync`；全量覆盖 Pipe valves（只 merge）；写入新的非空 `WEBUI_SECRET_KEY`；把 `openai.api_configs` 设为 `enable: true`。细节在 `docs/AGENT-ONBOARDING.md`，当前 session 不必打开。

目标仍是顶级；降级必须是用户点头的权衡，不是执行者自行放弃。

## P0（并列，不是顺序）

图像生成、**语音聊天**、**屏幕共享**、Notebook/YouTube 同级。不得写成「屏享 → 语音」。维持 **19 个 public**。未确认 N2+ 不改 Notebook 入口、不装第二前端。无 Realtime 钥匙时不换 OWUI 镜像。
