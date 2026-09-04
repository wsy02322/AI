# Image Studio — VPS 部署（独立容器，不进 Open WebUI）

给 VPS agent 复制。**不要**改 `open-webui` 容器、**不要**改 `/custom/entrypoint.sh`、**不要**写 `WEBUI_SECRET_KEY`、**不要** enable `openai.api_configs`、**不要** merge 这些钥匙进 Pipe。

## 隔离

| 项 | 值 |
|----|-----|
| 域名 | `https://image.micropigeon.com` |
| 监听 | `127.0.0.1:8091`（容器内 8091；**不要**占 8080 / 8090） |
| 数据 | 独立 volume，例如 `/var/lib/image-studio` → `/data`。和 `webui.db` **分开备份** |
| env | `/opt/image-studio/.env`（权限 600）。钥匙只放这里 |
| 构建 | 仓库 `image-studio/` Dockerfile |

## env（VPS 填，不要贴回聊天）

从仓库 `image-studio/.env.example` 复制到 `/opt/image-studio/.env`，注入：

- `STUDIO_OPENAI_API_KEY`
- `STUDIO_GEMINI_API_KEY`
- `STUDIO_XAI_API_KEY`
- `STUDIO_OPENROUTER_API_KEY`
- `STUDIO_SECRET_KEY`（随机 32+ 字符，跟 volume 一起持久化）
- `STUDIO_COOKIE_SECURE=1`
- `OPENWEBUI_URL=https://micropigeon.com`
- `STUDIO_PUBLIC_URL=https://image.micropigeon.com`
- `STUDIO_DATA_DIR=/data`

## 容器示例

```bash
mkdir -p /var/lib/image-studio /opt/image-studio
# 把仓库 image-studio/ 同步到构建上下文后：
docker build -t image-studio:local /path/to/repo/image-studio
docker rm -f image-studio 2>/dev/null || true
docker run -d --name image-studio --restart unless-stopped \
  --env-file /opt/image-studio/.env \
  -p 127.0.0.1:8091:8091 \
  -v /var/lib/image-studio:/data \
  image-studio:local
```

## Caddy

在现有 Caddy 里加站点，**不要**动 `micropigeon.com` → `8080`：

```
image.micropigeon.com {
    reverse_proxy 127.0.0.1:8091
}
```

DNS：`image` A/AAAA 指到同一台 VPS。

## 验收（钥匙注入后）

```bash
curl -sS http://127.0.0.1:8091/healthz
# providers.openai/google/xai/openrouter 应为 true（对应钥匙已注入）
cd /path/to/repo/image-studio
python3 scripts/verify_studio.py
# 真出图：用站点登录后点「生成」。不要把 key 贴到聊天。
```

## 备份

升配 / 换盘前：复制 `/var/lib/image-studio`（图库）。**不要**和 `webui.db` 绑成同一个 tar 当唯一备份。

## 不要

- 把 Studio 绑进 OWUI 镜像或 BetterUI entrypoint
- 把官方 key 写入 OWUI `api_configs` 或 Pipe valves
- 在本仓库 git 提交 `.env` / `/data`
- 关 OWUI 图像模型（另确认）
