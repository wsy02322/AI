from __future__ import annotations

import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import config

SAFE = re.compile(r"[^a-zA-Z0-9._-]+")


def _user_dir(email: str) -> Path:
    slug = SAFE.sub("_", email).strip("._") or "user"
    path = config.DATA_DIR / "users" / slug
    path.mkdir(parents=True, exist_ok=True)
    return path


def _meta_path(email: str, work_id: str) -> Path:
    return _user_dir(email) / work_id / "meta.json"


def _load(email: str, work_id: str) -> dict[str, Any]:
    path = _meta_path(email, work_id)
    if not path.exists():
        raise FileNotFoundError(work_id)
    return json.loads(path.read_text())


def _save(email: str, work: dict[str, Any]) -> None:
    folder = _user_dir(email) / work["id"]
    folder.mkdir(parents=True, exist_ok=True)
    tmp = folder / "meta.json.tmp"
    tmp.write_text(json.dumps(work, ensure_ascii=False, indent=2))
    tmp.replace(folder / "meta.json")


def list_works(email: str) -> list[dict[str, Any]]:
    root = _user_dir(email)
    out: list[dict[str, Any]] = []
    for meta in sorted(root.glob("*/meta.json"), reverse=True):
        work = json.loads(meta.read_text())
        out.append(
            {
                "id": work["id"],
                "title": work.get("title") or "Untitled",
                "updated": work.get("updated"),
                "current": work.get("current"),
            }
        )
    return out


def create_work(email: str, title: str = "Untitled") -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    work = {
        "id": uuid.uuid4().hex[:12],
        "title": title or "Untitled",
        "created": now,
        "updated": now,
        "current": None,
        "versions": [],
    }
    _save(email, work)
    return work


def get_work(email: str, work_id: str) -> dict[str, Any] | None:
    try:
        return _load(email, work_id)
    except FileNotFoundError:
        return None


def rename_work(email: str, work_id: str, title: str) -> dict[str, Any] | None:
    work = get_work(email, work_id)
    if not work:
        return None
    work["title"] = (title or "").strip() or work.get("title") or "Untitled"
    work["updated"] = datetime.now(timezone.utc).isoformat()
    _save(email, work)
    return work


def delete_work(email: str, work_id: str) -> bool:
    folder = _user_dir(email) / work_id
    if not folder.is_dir():
        return False
    shutil.rmtree(folder)
    return True


def file_path(email: str, work_id: str, filename: str) -> Path | None:
    name = Path(filename).name
    if not re.fullmatch(r"[a-zA-Z0-9._-]+\.png", name):
        return None
    work = get_work(email, work_id)
    if not work:
        return None
    allowed = {row.get("file") for row in work.get("versions") or []}
    if name not in allowed:
        return None
    path = _user_dir(email) / work_id / name
    return path if path.is_file() else None


def download_filename(work: dict[str, Any], filename: str) -> str:
    title = SAFE.sub("-", (work.get("title") or "image")).strip("-._") or "image"
    stem = Path(filename).stem[:24] or "v"
    return f"{title[:48]}-{stem}.png"


def add_version(
    email: str,
    work_id: str,
    *,
    image_bytes: bytes,
    prompt: str,
    model: str,
    kind: str,
) -> dict[str, Any]:
    work = _load(email, work_id)
    vid = uuid.uuid4().hex[:12]
    folder = _user_dir(email) / work_id
    dest = folder / f"{vid}.png"
    dest.write_bytes(image_bytes)
    version = {
        "id": vid,
        "file": dest.name,
        "prompt": prompt,
        "model": model,
        "kind": kind,
        "created": datetime.now(timezone.utc).isoformat(),
    }
    work["versions"].append(version)
    work["current"] = vid
    work["updated"] = version["created"]
    if work.get("title") in ("", "Untitled") and prompt:
        work["title"] = prompt[:60]
    _save(email, work)
    return work


def version_path(email: str, work_id: str, version_id: str) -> Path:
    work = _load(email, work_id)
    for row in work["versions"]:
        if row["id"] == version_id:
            path = _user_dir(email) / work_id / row["file"]
            if not path.exists():
                raise FileNotFoundError(version_id)
            return path
    raise FileNotFoundError(version_id)


def current_image(email: str, work_id: str) -> bytes | None:
    work = get_work(email, work_id)
    if not work:
        return None
    current = work.get("current")
    if not current:
        return None
    try:
        return version_path(email, work_id, current).read_bytes()
    except FileNotFoundError:
        return None
