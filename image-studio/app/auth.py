from __future__ import annotations

import time
from typing import Any

import httpx
from fastapi import HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from . import config


class AuthError(Exception):
    pass


def _signer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(config.SECRET_KEY, salt="image-studio-v1")


def sign_session(payload: dict[str, Any]) -> str:
    return _signer().dumps(payload)


def read_session(token: str) -> dict[str, Any]:
    return _signer().loads(token, max_age=config.SESSION_DAYS * 86400)


async def owui_signin(ident: str, password: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{config.OPENWEBUI_URL}/api/v1/auths/signin",
            json={"email": ident, "password": password},
        )
    if resp.status_code != 200:
        raise AuthError("Incorrect username or password")
    data = resp.json()
    return {
        "id": str(data.get("id") or ""),
        "email": data.get("email") or ident,
        "name": data.get("name") or ident,
        "role": data.get("role") or "user",
        "iat": int(time.time()),
    }


def optional_user(request: Request) -> dict[str, Any] | None:
    raw = request.cookies.get(config.COOKIE_NAME)
    if not raw:
        return None
    try:
        return read_session(raw)
    except (BadSignature, SignatureExpired):
        return None


def current_user(request: Request) -> dict[str, Any]:
    user = optional_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")
    return user


def user_key(user: dict[str, Any]) -> str:
    return user.get("id") or user.get("email") or "user"


def set_session(response: Response, user: dict[str, Any], request: Request | None = None) -> None:
    secure = bool(config.COOKIE_SECURE)
    if request is not None and request.headers.get("x-forwarded-proto") == "https":
        secure = True
    if request is not None and request.url.scheme == "https":
        secure = True
    response.set_cookie(
        config.COOKIE_NAME,
        sign_session(user),
        max_age=config.SESSION_DAYS * 86400,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(config.COOKIE_NAME, path="/")
