"""Google OAuth authentication for the mafia game analyzer."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from pydantic import BaseModel

from backend import mongo

router = APIRouter(prefix="/auth")

SESSION_MAX_AGE = 30 * 24 * 60 * 60  # 30 days in seconds


def _get_google_client_id() -> str:
    return os.environ.get("GOOGLE_CLIENT_ID", "")


def _get_jwt_secret() -> str:
    return os.environ.get("JWT_SECRET", "")


def _is_cookie_secure() -> bool:
    return os.environ.get("COOKIE_SECURE", "false").lower() == "true"


class UserInfo(BaseModel):
    email: str
    name: str


class GoogleTokenRequest(BaseModel):
    credential: str


def _verify_google_token(credential: str) -> dict:
    """Verify Google ID token (blocking call, run in thread)."""
    return google_id_token.verify_oauth2_token(
        credential,
        google_requests.Request(),
        _get_google_client_id(),
    )


def _create_session_jwt(email: str, name: str) -> str:
    payload = {
        "email": email,
        "name": name,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=SESSION_MAX_AGE),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm="HS256")


def _decode_session_jwt(token: str) -> dict:
    return jwt.decode(token, _get_jwt_secret(), algorithms=["HS256"])


@router.post("/google")
async def google_login(body: GoogleTokenRequest, response: Response):
    if not _get_google_client_id() or not _get_jwt_secret():
        raise HTTPException(status_code=500, detail="Auth not configured")

    try:
        idinfo = await asyncio.to_thread(_verify_google_token, body.credential)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    email = idinfo.get("email", "")
    name = idinfo.get("name", email)

    # Upsert user in database
    await mongo.db.users.update_one(
        {"email": email},
        {
            "$set": {"name": name, "last_login": datetime.now(timezone.utc)},
            "$setOnInsert": {"email": email, "created_at": datetime.now(timezone.utc)},
        },
        upsert=True,
    )

    session_token = _create_session_jwt(email, name)
    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=_is_cookie_secure(),
        max_age=SESSION_MAX_AGE,
        path="/",
    )
    return {"email": email, "name": name}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="session", path="/")
    return {"ok": True}


@router.get("/me")
async def me(session: str | None = Cookie(default=None)):
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = _decode_session_jwt(session)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid session")
    return {"email": payload["email"], "name": payload["name"]}


async def require_auth(session: str | None = Cookie(default=None)) -> UserInfo:
    """FastAPI dependency that enforces authentication."""
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = _decode_session_jwt(session)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid session")
    return UserInfo(email=payload["email"], name=payload["name"])
