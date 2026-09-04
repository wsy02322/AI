# Image Studio

独立画图站：`https://image.micropigeon.com`。对标 ChatGPT / Grok / Gemini 官网图像面，**不经过** Open WebUI 聊天 / Pipe / Guard。

现网 OWUI 图像模型先保留（双轨）。看图理解留在聊天。视频先不做。

## 本机

```bash
cd image-studio
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 填钥匙；本仓库 agent 通常没有直连 key
uvicorn app.main:app --host 127.0.0.1 --port 8091
```

登录 = 现网 OWUI 同一套账号（`POST /api/v1/auths/signin`），Studio 自管 cookie。

```bash
python3 tests/test_unit.py
python3 scripts/probe_capabilities.py
python3 scripts/verify_studio.py   # 需要 OPENWEBUI_* ，无钥匙时 generate 必须 503
```

## VPS

见 `DEPLOY.md`。独立容器、`127.0.0.1:8091`、独立 volume。钥匙只进 VPS env，不进 git、不进聊天、不进 Pipe。
