# 用户怎么访问

## 结论（5 人、多数在中国）

- **形态：桌面 Web**，不是手机 App、不是电话。  
- **打开：Chrome / Edge 访问 HTTPS 网址**（例如 `https://live.你的域名/`）。  
- **通话音视频必须走 VPS 中继到 Google**。浏览器直连 `generativelanguage.googleapis.com` 在中国大陆 **经常失败**，不能当默认。

## 推荐客户端

| 场景 | 建议 | 原因 |
|------|------|------|
| **MVP（5 人）** | **电脑 Chrome 或 Edge** | `getUserMedia` + `getDisplayMedia` 最稳；屏享是产品核心 |
| 手机浏览器 | 仅应急听/说 | iOS Safari 网页屏享几乎不可用；微信内置浏览器更不行 |
| 原生 App（iOS/Android/Electron） | **不做 MVP** | 同样要连你的 VPS，**不降低中德延迟**；屏享/上架成本高，5 人不值 |

没有 App Store、没有拨号、不要嵌进别的站点 iframe。

## 用户步骤

1. 打开给定 HTTPS 网址（须 HTTPS，否则浏览器会拦麦克风和屏享）  
2. 允许麦克风  
3. 开始通话，直接说话  
4. 可选：共享窗口 / 整个屏幕  
5. 想打断就接着说  

## 数据怎么走（中国用户默认）

```
浏览器（中国）
  --HTTPS/WSS-->  你的 VPS（已有站点同机，新端口 + Caddy）
                    --WSS-->  Google Gemini Live
```

- 打开页面、麦克风 PCM、屏享 JPEG **全部先到 VPS**，再由 VPS 转给 Google。  
- VPS 在欧盟可以访问 Google；用户只需能打开你的域名（与访问同机其它 HTTPS 站一样）。  
- `GEMINI_API_KEY` 只留在 VPS，不下发浏览器。

**不要**默认「浏览器直连 Google」（官方 ephemeral-token C2S）。那条只适合已能访问 Google 的网络；5 人里多数在中国，会表现为：页面能开、一点通话就超时。
