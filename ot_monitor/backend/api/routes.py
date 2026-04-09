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

import base64
import csv
import dataclasses
import io
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

import app_state

router = APIRouter()
IST = timezone(timedelta(hours=5, minutes=30))


# ─── Auth helper ──────────────────────────────────────────────────────────────

def _check_admin(request: Request) -> None:
    cfg = app_state.config
    if cfg is None:
        raise HTTPException(503, "Server not ready")
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Basic "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )
    try:
        decoded = base64.b64decode(auth[6:]).decode()
        _, pwd  = decoded.split(":", 1) if ":" in decoded else ("", "")
    except Exception:
        raise HTTPException(401, "Malformed credentials")
    if not secrets.compare_digest(pwd.encode(), cfg.auth.settings_password.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin password",
            headers={"WWW-Authenticate": "Basic"},
        )


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
    start: Optional[str]   = Query(None),
    end:   Optional[str]   = Query(None),
    hours: Optional[float] = Query(None),
):
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
    alarm_id: int,
    ack_by:   str = Query("nurse"),
):
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
