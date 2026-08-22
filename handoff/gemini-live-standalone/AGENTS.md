# 新项目 Agent 守则

本文件给 **创建独立 Live 产品** 的 agent。不要拿 Hub 仓库的 `AGENTS.md` 当施工手册去改 Open WebUI。

## 宪法（继承 Hub，略作范围限制）

1. **强能力**：语音+屏享对标 Gemini / ChatGPT 顶级 Live。特别难的事先确认是否略降级。  
2. **简单稳定**：少厂商、少密钥、少分叉。MVP 只用 Google Live API + 一个小 token 后端。  
3. **重大改动先 plan、确认再执行。** 创建新仓、消耗 Google Live 钥匙、对外域名，都算重大。若用户已经确认「独立仓 + 官方 C2S MVP」，则可在新仓内实现 MVP，仍 **禁止** 改 micropigeon OWUI。

## 仓库边界

| 可以 | 不可以 |
|------|--------|
| 新建独立 Git 仓库（建议名 `gemini-live-standalone` 或用户指定） | 在 `wsy02322/AI` 里实现通话前端并当 OWUI 功能合并 |
| 本交接包复制进新仓 `docs/` 作规格 | 改 `https://micropigeon.com` 的 Pipe / Call / 镜像 / `openai.api_configs` |
| 本地 / 新部署跑官方 C2S 示例改版 | 把 `GEMINI_API_KEY` 写进前端或本交接包 |

Hub 继续承担：聊天、图像、Sonar、对比、L1 Call（Whisper→模型→MiniMax）。本产品不替代 Hub。

## 开工前

1. 向用户要 **Google AI Studio / Gemini API key**（现网 Hub **没有** Realtime/Live 钥匙）。  
2. 新仓 README 写清：如何配置 `.env`、如何 `uv run server.py`、浏览器打开哪一页。  
3. 不要在本交接包所在的 Hub 仓库里安装一堆前端依赖「顺便做 Live」。

## 与用户沟通

- 不要把 MVP 验收成「已超越 Gemini 官网」。诚实口径：接近网页 Live，打不赢 Gemini App 生态与手机端。  
- 阶段 2 三项分开确认，不要和 MVP 同一张工单。
