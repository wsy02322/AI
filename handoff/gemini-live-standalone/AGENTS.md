# 新项目 Agent 守则

## 原则

1. **强能力**：对标 Gemini / ChatGPT 顶级网页 Live（语音 + 屏享 + 打断）。  
2. **简单稳定**：MVP 仅 Google Live API + 小 token 后端；少厂商。  
3. **重大改动先确认**：新域名、对外 HTTPS、Google 账单上限。

用户已确认：新建 GitHub 仓库 + 官方 C2S MVP + 同 VPS 部署。

## 仓库

- 在 **用户指定的新 GitHub 仓库** 内实现；不要塞进别的文档仓当子目录功能。  
- 把本交接包复制进新仓 `docs/`。  
- `.env` 不进 git；提供 `.env.example`。

## 开工前向用户索取

- `GEMINI_API_KEY`（Google AI Studio）  
- 期望的 **域名或子域名**（若要对公网 HTTPS）  
- VPS 上 **可用端口**（见 `DEPLOYMENT.md`）

## 沟通口径

- MVP ≈ 网页 Gemini Live，不宣称超越官方 App。  
- 阶段 2 每项单独确认，不与 MVP 同一 PR。
