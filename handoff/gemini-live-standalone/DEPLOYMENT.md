# 同 VPS 部署

与机上其它服务 **并存**。不要改、不要停其它站点，除非用户明确要求。

## 隔离

| 项 | 建议 |
|----|------|
| 进程 | 独立 systemd 或独立容器 |
| 端口 | `127.0.0.1:8090`（示例）；勿占 `8080` |
| 域名 | 新子域名 + HTTPS（Caddy `reverse_proxy`） |
| 环境 | 独立 `.env`：`GEMINI_API_KEY`、`HOST`、`PORT` |
| 日志 | 独立目录 |

用户访问与通话路径见 `ACCESS.md`。本服务 **会转发音视频到 Google**，VPS 出站须能访问 `generativelanguage.googleapis.com`（欧盟机房通常可以）。

## 最小形态

1. 应用监听 `127.0.0.1:8090`  
2. Caddy：HTTPS + 反代，**WebSocket 升级**（`/ws`）必须通  
3. 防火墙只开 443  

## 资源

- 无 GPU  
- 内存 512MB～1GB  
- 5 人同时屏享：出站大约 **1 MB/s 量级**（音频 + 1 fps JPEG）  

## 不要

- 把 API key 写进 Caddy 或前端  
- 绑定 `0.0.0.0` 裸对公网  
- 假设用户在桌面 Chrome 或能直连 Google  
- 假设微信内置浏览器能开麦/摄像头
