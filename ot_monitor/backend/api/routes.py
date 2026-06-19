"""
api/routes.py – REST API endpoints.
Uses app_state module for shared backend objects (no request.app.state threading).

Endpoints:
  GET  /health
  GET  /history
  GET  /export/csv
  GET  /alarms
  POST /alarms/{id}/acknowledge
  GET  /settings/thresholds
  POST /settings/thresholds   (Basic-Auth required)
  POST /settings/reload
"""
from __future__ import annotations

import csv
import dataclasses
import io
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse

import app_state
from auth import clear_session_cookie, require_admin, require_session, set_session_cookie

router = APIRouter()
IST = timezone(timedelta(hours=5, minutes=30))


# ─── Auth helpers ─────────────────────────────────────────────────────────────

def _check_admin(request: Request) -> dict:
    """Require admin role — used for write operations (settings, ack alarms)."""
    return require_admin(request)


def _check_any_user(request: Request) -> dict:
    """Require any authenticated session — used for download/export."""
    return require_session(request)


# ─── /auth/login ──────────────────────────────────────────────────────────────

@router.post("/auth/login", tags=["auth"])
async def login(request: Request):
    cfg = app_state.config
    if cfg is None:
        raise HTTPException(503, "Server not ready")

    body = await request.json()
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""

    user = next(
        (u for u in cfg.auth.users if u.username == username and u.password == password),
        None,
    )
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    response = JSONResponse({"ok": True, "username": user.username, "role": user.role})
    set_session_cookie(response, user.username, user.role)
    return response


@router.post("/auth/logout", tags=["auth"])
async def logout():
    response = JSONResponse({"ok": True})
    clear_session_cookie(response)
    return response


@router.get("/auth/me", tags=["auth"])
async def me(request: Request):
    session = require_session(request)
    return {
        "ok": True,
        "username": session["username"],
        "role": session.get("role", "viewer"),
        "expires_at": session["expires_at"],
    }


# ─── /health ──────────────────────────────────────────────────────────────────

@router.get("/health", tags=["diagnostics"])
async def get_health():
    payload = app_state.latest_payload
    cfg     = app_state.config
    return {
        "status":         "ok",
        "ot_id":          cfg.ot_id if cfg else None,
        "uptime_s":       payload.device_health.uptime_s if payload else None,
        "device_health":  payload.device_health.model_dump() if payload else None,
        "system_status":  payload.system_status.value if payload else "UNKNOWN",
        "network_status": payload.network_status.value if payload else "UNKNOWN",
    }


# ─── /history ─────────────────────────────────────────────────────────────────

@router.get("/history", tags=["data"])
async def get_history(
    start:  Optional[str]   = Query(None, description="ISO-8601 start time"),
    end:    Optional[str]   = Query(None, description="ISO-8601 end time"),
    fields: Optional[str]   = Query(None, description="Comma-separated field names"),
    hours:  Optional[float] = Query(None, description="Last N hours (convenience)"),
):
    storage = app_state.storage
    cfg     = app_state.config
    if storage is None or cfg is None:
        raise HTTPException(503, "Server not ready")

    now = datetime.now(IST)
    if hours is not None:
        end_dt, start_dt = now, now - timedelta(hours=hours)
    else:
        try:
            start_dt = datetime.fromisoformat(start) if start else now - timedelta(hours=1)
            end_dt   = datetime.fromisoformat(end)   if end   else now
        except ValueError as e:
            raise HTTPException(400, f"Invalid datetime: {e}")

    field_list = [f.strip() for f in fields.split(",")] if fields else None
    rows = await storage.query_telemetry(
        cfg.ot_id, start_dt.isoformat(), end_dt.isoformat(), field_list
    )
    return {"count": len(rows), "data": rows}


# ─── /export/csv ──────────────────────────────────────────────────────────────

@router.get("/export/csv", tags=["data"])
async def export_csv(
    request: Request,
    start: Optional[str]   = Query(None),
    end:   Optional[str]   = Query(None),
    hours: Optional[float] = Query(None),
):
    _check_any_user(request)  # both admin and viewer can download
    storage = app_state.storage
    cfg     = app_state.config
    if storage is None or cfg is None:
        raise HTTPException(503, "Server not ready")

    now = datetime.now(IST)
    if hours is not None:
        end_dt, start_dt = now, now - timedelta(hours=hours)
    else:
        start_dt = datetime.fromisoformat(start) if start else now - timedelta(hours=24)
        end_dt   = datetime.fromisoformat(end)   if end   else now

    csv_data = await storage.export_csv(cfg.ot_id, start_dt.isoformat(), end_dt.isoformat())
    filename = f"OT_{cfg.ot_id}_{start_dt.strftime('%Y%m%d_%H%M')}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── /alarms ──────────────────────────────────────────────────────────────────

@router.get("/alarms", tags=["alarms"])
async def get_alarms(
    limit:           int  = Query(100, ge=1, le=1000),
    include_cleared: bool = Query(True),
):
    storage = app_state.storage
    cfg     = app_state.config
    if storage is None or cfg is None:
        raise HTTPException(503, "Server not ready")
    rows = await storage.query_alarms(cfg.ot_id, limit=limit, include_cleared=include_cleared)
    return {"count": len(rows), "alarms": rows}


@router.post("/alarms/{alarm_id}/acknowledge", tags=["alarms"])
async def acknowledge_alarm(
    request: Request,
    alarm_id: int,
    ack_by:   str = Query("nurse"),
):
    _check_admin(request)
    storage = app_state.storage
    if storage is None:
        raise HTTPException(503, "Server not ready")
    ok = await storage.acknowledge_alarm(alarm_id, ack_by)
    if not ok:
        raise HTTPException(404, "Alarm not found")
    return {"acknowledged": True, "alarm_id": alarm_id}


# ─── /settings/thresholds ─────────────────────────────────────────────────────

@router.get("/settings/thresholds", tags=["settings"])
async def get_thresholds():
    cfg = app_state.config
    if cfg is None:
        raise HTTPException(503, "Server not ready")
    return dataclasses.asdict(cfg.thresholds)


@router.post("/settings/thresholds", tags=["settings"])
async def update_thresholds(request: Request):
    _check_admin(request)
    cfg = app_state.config
    if cfg is None:
        raise HTTPException(503, "Server not ready")

    body = await request.json()
    from config import ParameterThreshold
    th = cfg.thresholds
    for param, values in body.items():
        if hasattr(th, param) and isinstance(values, dict):
            existing = getattr(th, param)
            updated  = dataclasses.replace(existing, **{
                k: float(v) for k, v in values.items()
                if k in ParameterThreshold.__dataclass_fields__ and v is not None
            })
            setattr(th, param, updated)

    return {"status": "updated", "thresholds": dataclasses.asdict(cfg.thresholds)}


@router.post("/settings/reload", tags=["settings"])
async def reload_config_route(request: Request):
    _check_admin(request)
    from config import reload_config
    cfg = reload_config()
    app_state.config = cfg
    return {"status": "reloaded", "ot_id": cfg.ot_id}


# ─── /settings/users ──────────────────────────────────────────────────────────

@router.get("/settings/users", tags=["settings"])
async def list_users(request: Request):
    _check_admin(request)
    cfg = app_state.config
    if cfg is None:
        raise HTTPException(503, "Server not ready")
    return {"users": [{"username": u.username, "role": u.role} for u in cfg.auth.users]}


@router.post("/settings/users", tags=["settings"])
async def add_user(request: Request):
    _check_admin(request)
    cfg = app_state.config
    if cfg is None:
        raise HTTPException(503, "Server not ready")

    body     = await request.json()
    username = (body.get("username") or "").strip()
    password = (body.get("password") or "").strip()
    role     = (body.get("role") or "viewer").strip()

    if not username or not password:
        raise HTTPException(400, "username and password are required")
    if role not in ("admin", "viewer"):
        raise HTTPException(400, "role must be 'admin' or 'viewer'")
    if any(u.username == username for u in cfg.auth.users):
        raise HTTPException(409, f"User '{username}' already exists")

    from config import UserConfig, save_users
    cfg.auth.users.append(UserConfig(username=username, password=password, role=role))
    save_users(cfg.auth.users)
    return {"ok": True, "username": username, "role": role}


@router.delete("/settings/users/{username}", tags=["settings"])
async def remove_user(request: Request, username: str):
    session = _check_admin(request)
    cfg = app_state.config
    if cfg is None:
        raise HTTPException(503, "Server not ready")

    if session["username"] == username:
        raise HTTPException(400, "Cannot delete your own account")
    if not any(u.username == username for u in cfg.auth.users):
        raise HTTPException(404, f"User '{username}' not found")

    remaining = [u for u in cfg.auth.users if u.username != username]
    if not any(u.role == "admin" for u in remaining):
        raise HTTPException(400, "Cannot remove the last admin account")

    cfg.auth.users = remaining
    from config import save_users
    save_users(cfg.auth.users)
    return {"ok": True, "deleted": username}
