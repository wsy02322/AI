# 全程落地页 — VPS（Caddy 静态，不进 Open WebUI）

给 VPS agent 复制。**不要**改 `open-webui` 容器、**不要**改 `/custom/entrypoint.sh`、**不要**写 `WEBUI_SECRET_KEY`、**不要** enable `openai.api_configs`。

页面是无状态 HTML：`/nav/#p=`。深链只在用户点击后由页面生成。

## 1. 源码

```bash
mkdir -p /var/www/micropigeon-nav
curl -sSL https://raw.githubusercontent.com/wsy02322/AI/cursor/nav-page-decf/nav/index.html \
  -o /var/www/micropigeon-nav/index.html
grep -q AMAP_NAV_PAGE_V1 /var/www/micropigeon-nav/index.html
```

## 2. Caddy

在 **`micropigeon.com` 这个 site 块里、`reverse_proxy 127.0.0.1:8080` 之前**插入。不要动 `image.micropigeon.com`，不要改 8080。

```
    handle /nav {
        redir /nav/ 308
    }
    handle_path /nav/* {
        root * /var/www/micropigeon-nav
        try_files {path} /index.html
        file_server
    }
```

然后 `caddy reload`。

## 3. 回传（不要带 key）

```bash
curl -sS https://micropigeon.com/nav/ | grep AMAP_NAV_PAGE_V1
```

应看到 `AMAP_NAV_PAGE_V1`，且 `server` 不再是 uvicorn。之后把 Tool Valve `NAV_PAGE_BASE` merge 成 `https://micropigeon.com/nav/`（不要覆盖 `AMAP_KEY`）。
