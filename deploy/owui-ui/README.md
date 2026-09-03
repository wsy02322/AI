# OWUI chrome overlay（ai-ui-2）

现网全宽主题 + 助手左边 **单层 4px**。静态 CSS，不加载 `loader.js`。

源文件：`deploy/owui-ui/custom.css`。VPS 上有 **两份**，改完必须对上浏览器实际读的那份。

## 两份路径

| 角色 | 路径 |
|------|------|
| bind 源（重启后拷贝的源头） | 宿主机 `/opt/open-webui/custom/custom.css` → 容器 `/app/build/static/custom.css` |
| 正在 serve（浏览器读这份） | 容器 `/app/backend/open_webui/static/custom.css` |

OWUI 启动时把 `FRONTEND_BUILD_DIR` 拷到 `STATIC_DIR`。只改 bind、**不重启**，公网 `Last-Modified` 不会变。L0 下 **不要为了 CSS 重启容器**（会逼用户重登）。热改：两处一起写，然后 `curl` 公网。

## 热改（不重启）

1. 把本目录 `custom.css` 拷到 bind 源 **和** served 文件。  
2. 验收（必须变；不能只看容器里「文件在」）：

```bash
curl -sSI https://micropigeon.com/static/custom.css | grep -iE 'last-modified|etag|content-length'
curl -sS "https://micropigeon.com/static/custom.css?t=$(date +%s)" | grep -n "padding-left"
```

现网契约：助手只留一层 `#messages-container .message-listitem:has(.chat-assistant) { padding-left: 4px }`；`.flex-auto.pl-1` 保持 `0`。DOM 是 `.chat-assistant` / `.markdown-prose`，没有 `.prose`。

## 重建

entrypoint 仍只在 VPS。重建后把本文件拷回 bind；若容器已在跑，再拷一份到 `STATIC_DIR`（或等下次启动拷贝）。然后按上面 `curl` 公网。

BetterUI 是 entrypoint 另一条补丁链，**不要**把 4px 写进 BetterUI。
