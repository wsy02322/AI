# Image Studio — VPS 部署（独立容器，不进 Open WebUI）

给 VPS agent 复制。**不要**改 `open-webui` 容器、**不要**改 `/custom/entrypoint.sh`、**不要**写 `WEBUI_SECRET_KEY`、**不要** enable `openai.api_configs`、**不要** merge 这些钥匙进 Pipe、**不要**拷现网 `openai.api_keys[0]` 进 Studio（除非用户书面说复用）。

仓库现已 **public**：`https://github.com/wsy02322/AI`。分支 `cursor/image-studio-plan-decf`。

## 隔离

| 项 | 值 |
|----|-----|
| 域名 | `https://image.micropigeon.com` |
| 监听 | `127.0.0.1:8091`（容器内 8091；**不要**占 8080 / 8090） |
| 数据 | 独立 volume `/var/lib/image-studio` → `/data`。和 `webui.db` **分开备份** |
| env | `/opt/image-studio/.env`（权限 600）。钥匙只放这里，**不要**放进 git 树 |
| 源码 | `/opt/image-studio/src`（只读构建上下文） |

## 0. 先齐两样再 `docker run`

1. DNS：Spaceship 加 `image.micropigeon.com` **A → `78.47.152.85`**，灰云（不要 Cloudflare 橙云）。没记录就先不要指望 Caddy 签 443；容器仍可先在 `127.0.0.1:8091` 起来。
2. `/opt/image-studio/.env` 已就位（四把 key + `STUDIO_SECRET_KEY`）。钥匙不在对话里。本文件不含 key。

## 1. 源码（匿名即可）

```bash
mkdir -p /opt/image-studio /var/lib/image-studio
# 优先 git：
git clone --depth 1 -b cursor/image-studio-plan-decf \
  https://github.com/wsy02322/AI.git /opt/image-studio/src
# 若 git 仍失败，用公开 tarball（分支最新）：
# curl -sSL https://github.com/wsy02322/AI/archive/refs/heads/cursor/image-studio-plan-decf.tar.gz \
#   | tar -xzf - -C /tmp
# rm -rf /opt/image-studio/src
# mv /tmp/AI-cursor-image-studio-plan-decf /opt/image-studio/src
test -f /opt/image-studio/src/image-studio/Dockerfile
```

## 2. env（用户注入或用户自己 SSH 写好后再跑）

把 `image-studio/.env.example` 拷到 `/opt/image-studio/.env`（**在 git 树外面**），填：

```
OPENWEBUI_URL=https://micropigeon.com
STUDIO_HOST=0.0.0.0
STUDIO_PORT=8091
STUDIO_PUBLIC_URL=https://image.micropigeon.com
STUDIO_DATA_DIR=/data
STUDIO_SECRET_KEY=          # VPS 本地生成 32+ 字符，跟 volume 一起留着
STUDIO_COOKIE_SECURE=1
STUDIO_OPENAI_API_KEY=
STUDIO_GEMINI_API_KEY=
STUDIO_XAI_API_KEY=
STUDIO_OPENROUTER_API_KEY=
```

```bash
chmod 600 /opt/image-studio/.env
# 缺任何一把 STUDIO_*_API_KEY 就停，不要空着启动冒充直连
```

`STUDIO_SECRET_KEY` 可在 VPS 生成：`python3 -c 'import secrets; print(secrets.token_urlsafe(48))'`

## 3. 构建并启动

```bash
docker build -t image-studio:local /opt/image-studio/src/image-studio
docker rm -f image-studio 2>/dev/null || true
docker run -d --name image-studio --restart unless-stopped \
  --env-file /opt/image-studio/.env \
  -p 127.0.0.1:8091:8091 \
  -v /var/lib/image-studio:/data \
  image-studio:local
curl -sS http://127.0.0.1:8091/healthz
# providers.openai / google / xai / openrouter 均应为 true
```

## 4. Caddy

**只追加**，不要动 `micropigeon.com` → `8080`：

```
image.micropigeon.com {
    reverse_proxy 127.0.0.1:8091
}
```

DNS 未加好时不要强求 HTTPS 绿；先回传 `healthz` 即可。

## 回传（不要带 key）

- `docker ps --filter name=image-studio`
- `curl -sS http://127.0.0.1:8091/healthz`（应无密钥明文）
- `image.micropigeon.com` 是否 443 / 证书
- Caddy reload 是否成功

真出图由用户在浏览器登录后点「生成」。

## 不要

- 把 Studio 绑进 OWUI 镜像或 BetterUI entrypoint
- 把官方 key 写入 OWUI `api_configs` 或 Pipe valves
- 拷 `openai.api_keys[0]` 进 Studio（那是关掉的直连槽）
- 在 git 提交 `.env` / `/data`
- 关 OWUI 图像模型（另确认）
- 动 GoogleBanana 8787/8788
