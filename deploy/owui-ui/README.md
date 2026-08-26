# Open WebUI 界面覆盖（本仓）

真相源：`deploy/owui-ui/custom.css`（版本头 **ai-ui-1**）+ 空 `loader.js`。  
不要从 `open-webui-betterui` 拉 CSS。不要改 OWUI Svelte。不要动 `strip_bound_reasoning.py`。

## 部署（VPS）

Bind-mount 已存在：

- 宿主机 `/opt/open-webui/custom/custom.css` → 容器 `/app/build/static/custom.css`

**禁止 `docker cp`**（会 `device or resource busy`）。**禁止** `docker pull` / `:main`。

把本目录的 `custom.css` 覆盖到挂载源文件后：

```bash
SRC=/opt/open-webui/custom/custom.css
# 若 inspect 显示 Destination=/app/build/static/custom.css 的 Source 不同，改用那个路径
install -m 0644 custom.css "$SRC"
touch "$SRC"
docker restart open-webui
# 等容器起来
sleep 8
caddy reload --config /etc/caddy/Caddyfile 2>/dev/null || systemctl reload caddy
```

## 验收（先 curl，再手机硬刷新）

三处 `head` 都必须出现 `ai-ui-1`，且含 `model-selector`：

```bash
head -5 /opt/open-webui/custom/custom.css
curl -sS http://127.0.0.1:8080/static/custom.css | head -8
curl -sS https://micropigeon.com/static/custom.css | head -8
```

公网仍是旧 etag 时：先看 loopback，再 reload Caddy，不要再 `docker cp`。
