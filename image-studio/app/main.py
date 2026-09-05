"""Image Studio FastAPI app. Isolated from the Open WebUI process."""

from __future__ import annotations

import io
from urllib.parse import quote
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image

from . import auth, catalog, config, providers, store

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = Jinja2Templates(directory=str(ROOT / "templates"))

app = FastAPI(title="Image Studio", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")


def _json_error(exc: HTTPException) -> JSONResponse:
    return JSONResponse({"ok": False, "error": exc.detail}, status_code=exc.status_code)


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api/"):
        return _json_error(exc)
    if exc.status_code == 401:
        return RedirectResponse("/login", status_code=303)
    return JSONResponse({"ok": False, "error": exc.detail}, status_code=exc.status_code)


@app.get("/healthz")
async def healthz():
    return {
        "ok": True,
        "app": "image-studio",
        "version": "0.1.0",
        "providers": config.key_status(),
        "openwebui": config.OPENWEBUI_URL,
    }


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if auth.optional_user(request):
        return RedirectResponse("/", status_code=303)
    return TEMPLATES.TemplateResponse(
        "login.html",
        {"request": request, "error": request.query_params.get("error", "")},
    )


@app.post("/api/login")
async def api_login(request: Request):
    username = ""
    password = ""
    ctype = request.headers.get("content-type") or ""
    if "application/json" in ctype:
        body = await request.json()
        username = str(body.get("username") or body.get("email") or "").strip()
        password = str(body.get("password") or "")
    else:
        form = await request.form()
        username = str(form.get("username") or "").strip()
        password = str(form.get("password") or "")
    if not username or not password:
        raise HTTPException(status_code=400, detail="请输入账号和密码")
    try:
        user = await auth.owui_signin(username, password)
    except auth.AuthError as exc:
        if "application/json" in ctype:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        return RedirectResponse("/login?error=" + quote(str(exc)), status_code=303)
    if "application/json" in ctype:
        response = JSONResponse({"ok": True, "user": {"email": user["email"], "name": user["name"]}})
    else:
        response = RedirectResponse("/", status_code=303)
    auth.set_session(response, user, request)
    return response


@app.post("/api/logout")
async def api_logout():
    response = RedirectResponse("/login", status_code=303)
    auth.clear_session(response)
    return response


@app.get("/", response_class=HTMLResponse)
async def studio_page(request: Request):
    user = auth.optional_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    return TEMPLATES.TemplateResponse(
        "studio.html",
        {"request": request, "user": user, "models": catalog.list_models()},
    )


@app.get("/api/models")
async def api_models(request: Request):
    auth.current_user(request)
    return {"ok": True, "models": catalog.list_models()}


@app.get("/api/works")
async def api_works(request: Request):
    user = auth.current_user(request)
    return {"ok": True, "works": store.list_works(auth.user_key(user))}


@app.post("/api/works")
async def api_create_work(request: Request, title: str = Form("未命名")):
    user = auth.current_user(request)
    work = store.create_work(auth.user_key(user), title)
    return {"ok": True, "work": work}


@app.get("/api/works/{work_id}")
async def api_get_work(request: Request, work_id: str):
    user = auth.current_user(request)
    work = store.get_work(auth.user_key(user), work_id)
    if not work:
        raise HTTPException(status_code=404, detail="作品不存在")
    return {"ok": True, "work": work}


@app.post("/api/works/{work_id}/title")
async def api_rename_work(request: Request, work_id: str, title: str = Form(...)):
    user = auth.current_user(request)
    work = store.rename_work(auth.user_key(user), work_id, title)
    if not work:
        raise HTTPException(status_code=404, detail="作品不存在")
    return {"ok": True, "work": work}


@app.delete("/api/works/{work_id}")
async def api_delete_work(request: Request, work_id: str):
    user = auth.current_user(request)
    if not store.delete_work(auth.user_key(user), work_id):
        raise HTTPException(status_code=404, detail="作品不存在")
    return {"ok": True}


@app.get("/api/works/{work_id}/files/{filename}")
async def api_file(request: Request, work_id: str, filename: str):
    user = auth.current_user(request)
    path = store.file_path(auth.user_key(user), work_id, filename)
    if not path:
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(path, media_type="image/png")


async def _read_png(upload: UploadFile | None) -> bytes | None:
    if not upload or not getattr(upload, "filename", None):
        return None
    data = await upload.read()
    if not data:
        return None
    image = Image.open(io.BytesIO(data))
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA")
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


@app.post("/api/works/{work_id}/upload")
async def api_upload(
    request: Request,
    work_id: str,
    image: UploadFile = File(...),
    prompt: str = Form("upload"),
):
    user = auth.current_user(request)
    key = auth.user_key(user)
    work = store.get_work(key, work_id)
    if not work:
        raise HTTPException(status_code=404, detail="作品不存在")
    image_bytes = await _read_png(image)
    if not image_bytes:
        raise HTTPException(status_code=400, detail="请上传一张图片")
    work = store.add_version(
        key,
        work_id,
        image_bytes=image_bytes,
        prompt=prompt,
        model="upload",
        kind="upload",
    )
    return {"ok": True, "work": work}


@app.post("/api/generate")
async def api_generate(
    request: Request,
    model_id: str = Form(...),
    prompt: str = Form(...),
    work_id: str = Form(""),
    title: str = Form(""),
    aspect: str = Form(""),
    resolution: str = Form(""),
    quality: str = Form(""),
):
    user = auth.current_user(request)
    key = auth.user_key(user)
    try:
        model = catalog.get_model(model_id)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail="未知模型") from exc
    work = None
    if work_id:
        work = store.get_work(key, work_id)
        if not work:
            raise HTTPException(status_code=404, detail="作品不存在")
    else:
        work = store.create_work(key, title or prompt[:40] or "未命名")
    try:
        png = providers.generate(
            model_id=model_id,
            prompt=prompt,
            aspect=aspect or model.get("default_aspect") or "1:1",
            resolution=resolution or model.get("default_resolution") or "",
            quality=quality,
        )
    except providers.ProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    work = store.add_version(
        key,
        work["id"],
        image_bytes=png,
        prompt=prompt,
        model=model_id,
        kind="generate",
    )
    return {"ok": True, "work_id": work["id"], "work": work}


@app.post("/api/edit")
async def api_edit(
    request: Request,
    model_id: str = Form(...),
    prompt: str = Form(...),
    work_id: str = Form(...),
    image: UploadFile | None = File(None),
    mask: UploadFile | None = File(None),
    aspect: str = Form(""),
    resolution: str = Form(""),
    quality: str = Form(""),
):
    user = auth.current_user(request)
    key = auth.user_key(user)
    try:
        model = catalog.get_model(model_id)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail="未知模型") from exc
    work = store.get_work(key, work_id)
    if not work:
        raise HTTPException(status_code=404, detail="作品不存在")
    image_bytes = await _read_png(image)
    if not image_bytes:
        image_bytes = store.current_image(key, work_id)
    if not image_bytes:
        raise HTTPException(status_code=400, detail="没有可编辑的底图")
    mask_bytes = await _read_png(mask)
    if mask_bytes and model.get("edit") != "mask":
        raise HTTPException(status_code=400, detail="这个模型没有像素蒙版，请用语义编辑")
    try:
        png = providers.edit(
            model_id=model_id,
            prompt=prompt,
            canvas=image_bytes,
            mask=mask_bytes,
            aspect=aspect or model.get("default_aspect") or "1:1",
            resolution=resolution or model.get("default_resolution") or "",
            quality=quality,
        )
    except providers.ProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    work = store.add_version(
        key,
        work_id,
        image_bytes=png,
        prompt=prompt,
        model=model_id,
        kind="edit",
    )
    return {"ok": True, "work_id": work_id, "work": work}
