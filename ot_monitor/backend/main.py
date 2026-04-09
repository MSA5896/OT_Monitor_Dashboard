from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import timedelta, timezone
from typing import Set

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.dirname(__file__))

import app_state
from config import get_config
from data_model import (
    AlarmEvent, AlarmLevel, DashboardPayload, NetworkStatus, SystemStatus,
)
from data_sources import create_source
from alarm_engine import AlarmEngine
from storage import Storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s – %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ot_monitor")

IST = timezone(timedelta(hours=5, minutes=30))

# ─── Connected Flutter WebSocket clients ─────────────────────────────────────
_ws_clients: Set[WebSocket] = set()


# ─── Lifespan context manager (replaces deprecated @app.on_event) ─────────────
@asynccontextmanager
async def lifespan(application: FastAPI):
    """
    Modern FastAPI lifespan handler.
    Everything before `yield` is startup; everything after is shutdown.
    """
    # ── Startup ──────────────────────────────────────────────────────────────
    cfg     = get_config()
    storage = Storage(cfg)
    await storage.initialise()

    engine = AlarmEngine(cfg)
    source = create_source(cfg)

    # Populate shared module-level state (used by api/routes.py)
    app_state.config         = cfg
    app_state.storage        = storage
    app_state.alarm_engine   = engine
    app_state.latest_payload = None

    # Alarm events → SQLite
    async def on_alarm(event: AlarmEvent):
        try:
            await storage.insert_alarm(event)
        except Exception as e:
            logger.error("Failed to store alarm: %s", e)

    engine.register_alarm_callback(on_alarm)
    await source.start()

    ingest_task = asyncio.create_task(_ingest_loop(source, engine, storage, cfg))
    prune_task  = asyncio.create_task(storage.prune_loop())

    logger.info("OT Monitor backend started  ✓  (ot_id=%s, source=%s)",
                cfg.ot_id, cfg.data_source.type)

    yield  # ← application runs here

    # ── Shutdown ─────────────────────────────────────────────────────────────
    ingest_task.cancel()
    prune_task.cancel()
    await storage.close()
    logger.info("Backend shut down cleanly.")


# ─── FastAPI application ──────────────────────────────────────────────────────
app = FastAPI(
    title="OT Infection Monitor – Backend",
    version="1.0.0",
    description="Gateway API and WebSocket server for OT environmental monitoring.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # restrict in production with specific origins
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Mount REST routes via router ────────────────────────────────────────────
from api.routes import router as api_router  # noqa: E402 (after sys.path setup)
app.include_router(api_router)


# ─── WebSocket endpoint (Flutter connects here) ───────────────────────────────
@app.websocket("/ws")
async def ws_dashboard(ws: WebSocket):
    await ws.accept()
    _ws_clients.add(ws)
    logger.info("Flutter client connected  (%d total)", len(_ws_clients))
    try:
        while True:
            # Hold the connection open; data is pushed from the ingest loop
            await asyncio.sleep(20)
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(ws)
        logger.info("Flutter client disconnected  (%d remain)", len(_ws_clients))


# ─── Broadcast helper ─────────────────────────────────────────────────────────
async def _broadcast(payload: DashboardPayload) -> None:
    if not _ws_clients:
        return
    data = payload.model_dump_json()
    dead: Set[WebSocket] = set()
    for ws in list(_ws_clients):
        try:
            await ws.send_text(data)
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)


# ─── Ingest loop ─────────────────────────────────────────────────────────────
async def _ingest_loop(source, engine: AlarmEngine, storage: Storage, cfg) -> None:
    """Consume packets from data source → evaluate alarms → persist → broadcast."""
    broadcast_interval = cfg.server.ws_broadcast_interval_s
    last_broadcast     = 0.0
    start_time         = time.monotonic()

    async for pkt in source.packets():
        try:
            alarm_states, system_status, combo_events = await engine.evaluate(
                pkt.data, pkt.ot_id, pkt.timestamp_iso
            )

            net_status = (
                NetworkStatus.CLOUD_SYNCED if cfg.cloud.enabled
                else NetworkStatus.LOCAL_ONLY
            )

            # Active alarms = all non-NORMAL parameter states + combo events
            active: list[AlarmEvent] = [
                AlarmEvent(
                    ot_id=pkt.ot_id,
                    timestamp_iso=pkt.timestamp_iso,
                    parameter=s.parameter,
                    level=s.level,
                    value=s.value,
                    message=s.message,
                )
                for s in alarm_states.values()
                if s.level != AlarmLevel.NORMAL
            ] + combo_events

            pkt.device_health.uptime_s = time.monotonic() - start_time

            payload = DashboardPayload(
                timestamp_iso  = pkt.timestamp_iso,
                ot_id          = pkt.ot_id,
                ot_name        = cfg.ot_name,
                data           = pkt.data,
                device_health  = pkt.device_health,
                system_status  = system_status,
                network_status = net_status,
                cloud_sync     = cfg.cloud.enabled,
                alarm_states   = alarm_states,
                active_alarms  = active,
            )

            # Update module-level state (read by /health endpoint)
            app_state.latest_payload = payload

            # Persist to SQLite
            await storage.insert_telemetry(
                pkt.ot_id, pkt.timestamp_iso, pkt.data, system_status.value
            )

            # Broadcast to Flutter clients at configured cadence (default 1 Hz)
            now = time.monotonic()
            if now - last_broadcast >= broadcast_interval:
                await _broadcast(payload)
                last_broadcast = now

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Ingest error: %s", e, exc_info=True)


# ─── Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cfg = get_config()
    uvicorn.run(
        "main:app",
        host=cfg.server.host,
        port=cfg.server.port,
        log_level="info",
        reload=False,
    )
