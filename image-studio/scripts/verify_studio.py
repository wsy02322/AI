#!/usr/bin/env python3
"""Studio acceptance: login against live OWUI, CRUD, missing-key 503, no secret leak."""

from __future__ import annotations

import io
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("STUDIO_DATA_DIR", str(Path(tempfile.mkdtemp(prefix="studio-verify-"))))
os.environ.setdefault("STUDIO_SECRET_KEY", "verify-secret-not-for-prod")

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.main import app  # noqa: E402


def png_bytes(color=(20, 40, 80, 255), size=(32, 32)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", size, color).save(buf, format="PNG")
    return buf.getvalue()


def main() -> int:
    errors: list[str] = []
    oks: list[str] = []
    user = os.environ.get("OPENWEBUI_USERNAME") or os.environ.get("OPENWEBUI_EMAIL") or ""
    password = os.environ.get("OPENWEBUI_PASSWORD") or ""
    if not user or not password:
        print("missing OPENWEBUI_USERNAME / OPENWEBUI_PASSWORD")
        return 1

    client = TestClient(app)
    health = client.get("/healthz").json()
    if health.get("ok") and health.get("app") == "image-studio":
        oks.append("healthz")
    else:
        errors.append(f"healthz {health}")
    if any(health.get("providers", {}).values()) is False:
        oks.append("providers empty in this agent (keys not in env)")

    login = client.post("/api/login", json={"username": user, "password": password})
    if login.status_code == 200 and login.json().get("ok"):
        oks.append("login json against live OWUI")
    else:
        errors.append(f"login {login.status_code} {login.text[:200]}")
        _report(oks, errors)
        return 1
    if "studio_session" not in client.cookies:
        errors.append("missing studio_session cookie")
    else:
        oks.append("studio cookie set")

    models = client.get("/api/models").json()
    ids = [row["id"] for row in models.get("models") or []]
    if "openai:gpt-image-2" in ids and len(ids) == 8:
        oks.append(f"catalog {len(ids)}")
    else:
        errors.append(f"catalog {ids}")
    if models.get("mask_model_id") == "openai:gpt-image-2":
        oks.append("mask_model_id")
    else:
        errors.append(f"mask_model_id {models.get('mask_model_id')}")

    created = client.post("/api/works", data={"title": "verify"})
    work = created.json().get("work") or {}
    work_id = work.get("id")
    if created.status_code == 200 and work_id:
        oks.append("create work")
    else:
        errors.append(f"create work {created.text[:200]}")
        _report(oks, errors)
        return 1

    upload = client.post(
        f"/api/works/{work_id}/upload",
        files={"image": ("dot.png", png_bytes(), "image/png")},
        data={"prompt": "dot"},
    )
    if upload.status_code == 200 and (upload.json().get("work") or {}).get("current"):
        oks.append("upload version")
    else:
        errors.append(f"upload {upload.status_code} {upload.text[:200]}")

    gen = client.post(
        "/api/generate",
        data={"model_id": "openai:gpt-image-2", "prompt": "a red square", "work_id": work_id},
    )
    if gen.status_code == 503 and "missing key" in gen.text:
        oks.append("generate 503 missing key")
    else:
        errors.append(f"generate expected 503, got {gen.status_code} {gen.text[:240]}")
    if "sk-" in gen.text or "AIza" in gen.text:
        errors.append("generate error leaked a key-looking string")
    else:
        oks.append("generate error does not leak keys")

    edit = client.post(
        "/api/edit",
        data={"model_id": "openai:gpt-image-2", "prompt": "make it blue", "work_id": work_id},
        files={"mask": ("mask.png", png_bytes((255, 255, 255, 180)), "image/png")},
    )
    if edit.status_code == 503 and "missing key" in edit.text:
        oks.append("edit+mask 503 missing key")
    else:
        errors.append(f"edit expected 503, got {edit.status_code} {edit.text[:240]}")

    semantic = client.post(
        "/api/edit",
        data={"model_id": "google:gemini-3-pro-image", "prompt": "only change sky", "work_id": work_id},
        files={"mask": ("mask.png", png_bytes((255, 255, 255, 180)), "image/png")},
    )
    if semantic.status_code == 400:
        oks.append("gemini rejects pixel mask")
    else:
        errors.append(f"gemini mask should 400, got {semantic.status_code} {semantic.text[:200]}")

    _report(oks, errors)
    return 1 if errors else 0


def _report(oks: list[str], errors: list[str]) -> None:
    for row in oks:
        print(f"ok  {row}")
    for row in errors:
        print(f"err {row}")
    print(f"{len(oks)} ok / {len(errors)} err")


if __name__ == "__main__":
    sys.exit(main())
