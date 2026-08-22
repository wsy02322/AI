# 同 VPS 部署

用户会在 **已有 VPS** 上运行本产品，与机上其它服务 **并存**。新 agent **只负责本产品**，不要改、不要停其它站点，除非用户明确要求。

## 隔离原则

| 项 | 建议 |
|----|------|
| 进程 | 独立 systemd 单元或独立 Docker 容器 |
| 端口 | **新端口**（例如 `127.0.0.1:8090`）；勿占用 `8080` 除非用户指定 |
| 域名 | 新子域名（例如 `live.example.com`）或用户给定路径 |
| HTTPS | Caddy / nginx 反代到本服务监听地址 |
| 环境变量 | 独立 `.env`；仅 `GEMINI_API_KEY` + 可选 `HOST`/`PORT` |
| 日志 | 独立目录，例如 `/var/log/gemini-live/` |

## 最小生产形态（MVP 可后补）

1. `uv run server.py` 或 `gunicorn` 监听 `127.0.0.1:8090`  
2. Caddy 增加一条 `reverse_proxy`  
3. 防火墙只开放 443（若已有 Caddy 则通常已满足）  

## 资源

- **无 GPU 要求**（媒体走 Google Live API）  
- 内存：Python + 静态前端，**512MB～1GB** 通常够  
- 带宽：上行主要是用户麦克风；屏享在浏览器侧编码为 JPEG 后进 Google，VPS 几乎不扛视频

## 健康检查

- `GET /` 或 `/health` 返回 200  
- 日志无 token 签发失败  

## 备份

- MVP 无用户 DB 则无需备份  
- 阶段 2 若加会话存储，再定备份策略  

## 不要

- 为了本服务去改机上其它容器的 env / 数据库  
- 把 `GEMINI_API_KEY` 写进 Caddy 配置或前端静态文件  
- 默认绑定 `0.0.0.0` 对外暴露 token 后端（应经反代 + TLS）
