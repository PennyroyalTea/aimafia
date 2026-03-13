"""Authentication: Google ID token verification and session cookies."""

from __future__ import annotations

import os

from fastapi import APIRouter, Cookie, HTTPException, Response
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from itsdangerous import BadSignature, TimestampSigner
from pydantic import BaseModel

router = APIRouter(prefix="/auth")

GOOGLE_CLIENT_ID = ""
AUTH_SECRET = ""
ALLOWED_EMAILS: set[str] = set()
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def init_auth() -> None:
    """Load auth config from environment. Call on startup."""
    global GOOGLE_CLIENT_ID, AUTH_SECRET, ALLOWED_EMAILS
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    AUTH_SECRET = os.environ.get("AUTH_SECRET", "change-me-in-production")
    raw = os.environ.get("ALLOWED_EMAILS", "")
    ALLOWED_EMAILS = {e.strip().lower() for e in raw.split(",") if e.strip()}


class GoogleAuthRequest(BaseModel):
    credential: str


class AuthUser(BaseModel):
    authenticated: bool
    email: str | None = None
    name: str | None = None
    picture: str | None = None


def _sign_session(email: str) -> str:
    signer = TimestampSigner(AUTH_SECRET)
    return signer.sign(email).decode()


def _verify_session(session_value: str) -> str | None:
    signer = TimestampSigner(AUTH_SECRET)
    try:
        return signer.unsign(session_value, max_age=SESSION_MAX_AGE).decode()
    except BadSignature:
        return None


def require_auth(session: str = Cookie(default="")) -> str:
    """FastAPI dependency. Returns the user's email or raises 401."""
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    email = _verify_session(session)
    if email is None:
        raise HTTPException(status_code=401, detail="Session expired")
    return email


@router.get("/config")
async def auth_config():
    """Return public auth config (Google Client ID)."""
    return {"google_client_id": GOOGLE_CLIENT_ID}


@router.post("/google")
async def google_login(body: GoogleAuthRequest, response: Response):
    """Verify Google ID token and create session."""
    try:
        idinfo = id_token.verify_oauth2_token(
            body.credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    email = idinfo.get("email", "").lower()
    if not idinfo.get("email_verified"):
        raise HTTPException(status_code=401, detail="Email not verified")

    if ALLOWED_EMAILS and email not in ALLOWED_EMAILS:
        raise HTTPException(
            status_code=403,
            detail="This email is not on the invite list",
        )

    is_dev = os.environ.get("DEBUG", "").lower() in ("1", "true")
    session_value = _sign_session(email)
    response.set_cookie(
        key="session",
        value=session_value,
        httponly=True,
        secure=not is_dev,
        samesite="lax",
        max_age=SESSION_MAX_AGE,
        path="/",
    )
    return AuthUser(
        authenticated=True,
        email=email,
        name=idinfo.get("name"),
        picture=idinfo.get("picture"),
    )


@router.get("/me")
async def auth_status(session: str = Cookie(default="")):
    """Check current auth status."""
    if not session:
        return AuthUser(authenticated=False)
    email = _verify_session(session)
    if email is None:
        return AuthUser(authenticated=False)
    return AuthUser(authenticated=True, email=email)


@router.post("/logout")
async def logout(response: Response):
    """Clear session cookie."""
    response.delete_cookie(key="session", path="/")
    return {"ok": True}
