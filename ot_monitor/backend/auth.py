from __future__ import annotations

import hashlib
import hmac
import time
from typing import Optional

from fastapi import HTTPException, Request, status

import app_state


SESSION_COOKIE = "ot_session"


def _get_config():
    cfg = app_state.config
    if cfg is None:
        raise HTTPException(503, "Server not ready")
    return cfg


def _make_signature(payload: str, secret: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def _verify_signature(payload: str, signature: str, secret: str) -> bool:
    return hmac.compare_digest(signature, _make_signature(payload, secret))


def _create_session_token(username: str, role: str, secret: str, expires_at: int) -> str:
    payload = f"{username}|{role}|{expires_at}"
    sig = _make_signature(payload, secret)
    return f"{payload}|{sig}"


def _parse_session_token(token: str, secret: str) -> Optional[dict]:
    try:
        payload, sig = token.rsplit("|", 1)
        if not _verify_signature(payload, sig, secret):
            return None
        parts = payload.split("|")
        if len(parts) == 3:
            username, role, expires_at_str = parts
        elif len(parts) == 2:
            # Legacy token (no role field) — treat as admin
            username, expires_at_str = parts
            role = "admin"
        else:
            return None
        if int(expires_at_str) < int(time.time()):
            return None
        return {"username": username, "role": role, "expires_at": int(expires_at_str)}
    except Exception:
        return None


def set_session_cookie(response, username: str, role: str) -> None:
    cfg = _get_config()
    expires_at = int(time.time()) + cfg.auth.session_expire_minutes * 60
    token = _create_session_token(username, role, cfg.auth.session_secret, expires_at)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=cfg.auth.enable_tls,
        samesite="lax",
        max_age=cfg.auth.session_expire_minutes * 60,
    )


def clear_session_cookie(response) -> None:
    response.delete_cookie(SESSION_COOKIE)


def require_session(request: Request) -> dict:
    """Return session dict {username, role, expires_at} or raise 401."""
    cfg = _get_config()
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    session = _parse_session_token(token, cfg.auth.session_secret)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    return session


def require_admin(request: Request) -> dict:
    """Return session dict only if role == 'admin', else raise 403."""
    session = require_session(request)
    if session.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for this action",
        )
    return session


