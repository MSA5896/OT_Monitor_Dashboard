"""
storage.py – SQLite time-series storage using aiosqlite (async).
Tables:
  - telemetry : 1-Hz readings (pruned per retention_days)
  - alarm_log : persistent alarm events with acknowledgement support
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import aiosqlite

from config import AppConfig
from data_model import AlarmEvent, AlarmLevel, OTData

logger = logging.getLogger(__name__)


class Storage:
    def __init__(self, config: AppConfig):
        self.cfg   = config
        self.db_path = config.storage.db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def initialise(self) -> None:
        """Open DB connection and create tables if needed."""
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL;")
        await self._create_tables()
        logger.info("Storage initialised: %s", self.db_path)

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    async def _create_tables(self) -> None:
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                ot_id                 TEXT    NOT NULL,
                timestamp_iso         TEXT    NOT NULL,
                timestamp_unix        REAL    NOT NULL,
                temperature_c         REAL,
                relative_humidity_pct REAL,
                pm1_ugm3              REAL,
                pm25_ugm3             REAL,
                pm10_ugm3             REAL,
                diff_pressure_pa      REAL,
                co2_ppm               REAL,
                voc_ppb               REAL,
                door_state            TEXT,
                occupancy_count       INTEGER,
                system_status         TEXT,
                ext_json              TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_telemetry_ts  ON telemetry(timestamp_unix);
            CREATE INDEX IF NOT EXISTS idx_telemetry_ot  ON telemetry(ot_id, timestamp_unix);

            CREATE TABLE IF NOT EXISTS alarm_log (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                ot_id          TEXT NOT NULL,
                timestamp_iso  TEXT NOT NULL,
                timestamp_unix REAL NOT NULL,
                parameter      TEXT NOT NULL,
                level          TEXT NOT NULL,
                value          REAL,
                message        TEXT,
                acknowledged   INTEGER DEFAULT 0,
                ack_by         TEXT,
                ack_at_iso     TEXT,
                duration_s     REAL,
                cleared        INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_alarm_ts ON alarm_log(timestamp_unix);
        """)
        await self._db.commit()

    # ── Write ─────────────────────────────────────────────────────────────────

    async def insert_telemetry(
        self,
        ot_id: str,
        timestamp_iso: str,
        data: OTData,
        system_status: str = "SAFE",
    ) -> None:
        ts_unix = datetime.fromisoformat(timestamp_iso).timestamp()
        ext_json = json.dumps(data.ext) if data.ext else "{}"
        await self._db.execute(
            """
            INSERT INTO telemetry (
                ot_id, timestamp_iso, timestamp_unix,
                temperature_c, relative_humidity_pct,
                pm1_ugm3, pm25_ugm3, pm10_ugm3,
                diff_pressure_pa, co2_ppm, voc_ppb,
                door_state, occupancy_count, system_status, ext_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                ot_id, timestamp_iso, ts_unix,
                data.temperature_c, data.relative_humidity_pct,
                data.pm1_ugm3, data.pm25_ugm3, data.pm10_ugm3,
                data.diff_pressure_pa, data.co2_ppm, data.voc_ppb,
                data.door_state.value if data.door_state else None,
                data.occupancy_count, system_status, ext_json,
            )
        )
        await self._db.commit()

    async def insert_alarm(self, event: AlarmEvent) -> int:
        """Insert an alarm event; returns the new row id."""
        ts_unix = datetime.fromisoformat(event.timestamp_iso).timestamp()
        cursor = await self._db.execute(
            """
            INSERT INTO alarm_log (
                ot_id, timestamp_iso, timestamp_unix,
                parameter, level, value, message,
                acknowledged, duration_s, cleared
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                event.ot_id, event.timestamp_iso, ts_unix,
                event.parameter, event.level.value, event.value,
                event.message, int(event.acknowledged),
                event.duration_s,
                1 if event.level == AlarmLevel.NORMAL else 0,
            )
        )
        await self._db.commit()
        return cursor.lastrowid

    # ── Query ─────────────────────────────────────────────────────────────────

    async def query_telemetry(
        self,
        ot_id: str,
        start_iso: str,
        end_iso: str,
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        start_unix = datetime.fromisoformat(start_iso).timestamp()
        end_unix   = datetime.fromisoformat(end_iso).timestamp()

        safe_fields = {
            "timestamp_iso", "temperature_c", "relative_humidity_pct",
            "pm1_ugm3", "pm25_ugm3", "pm10_ugm3", "diff_pressure_pa",
            "co2_ppm", "voc_ppb", "door_state", "system_status"
        }
        if fields:
            cols = ", ".join(f for f in fields if f in safe_fields)
            if not cols:
                cols = "timestamp_iso, temperature_c, relative_humidity_pct, pm25_ugm3"
        else:
            cols = "timestamp_iso, temperature_c, relative_humidity_pct, pm1_ugm3, pm25_ugm3, pm10_ugm3, diff_pressure_pa, co2_ppm, voc_ppb, door_state, system_status"

        cursor = await self._db.execute(
            f"SELECT {cols} FROM telemetry WHERE ot_id=? AND timestamp_unix BETWEEN ? AND ? ORDER BY timestamp_unix ASC",
            (ot_id, start_unix, end_unix)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def query_alarms(
        self,
        ot_id: Optional[str] = None,
        limit: int = 200,
        include_cleared: bool = True,
    ) -> List[Dict[str, Any]]:
        conditions = []
        params = []
        if ot_id:
            conditions.append("ot_id = ?")
            params.append(ot_id)
        if not include_cleared:
            conditions.append("cleared = 0")
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params.append(limit)
        cursor = await self._db.execute(
            f"SELECT * FROM alarm_log {where} ORDER BY timestamp_unix DESC LIMIT ?",
            params
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def acknowledge_alarm(self, alarm_id: int, ack_by: str) -> bool:
        from datetime import datetime
        ack_iso = datetime.now().astimezone().isoformat()
        result = await self._db.execute(
            "UPDATE alarm_log SET acknowledged=1, ack_by=?, ack_at_iso=? WHERE id=?",
            (ack_by, ack_iso, alarm_id)
        )
        await self._db.commit()
        return result.rowcount > 0

    # ── Export ────────────────────────────────────────────────────────────────

    async def export_csv(self, ot_id: str, start_iso: str, end_iso: str) -> str:
        rows = await self.query_telemetry(ot_id, start_iso, end_iso)
        if not rows:
            return ""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()

    # ── Maintenance ───────────────────────────────────────────────────────────

    async def prune_old_data(self) -> int:
        """Delete telemetry older than retention_days. Returns rows deleted."""
        cutoff = time.time() - self.cfg.storage.retention_days * 86400
        cursor = await self._db.execute(
            "DELETE FROM telemetry WHERE timestamp_unix < ?", (cutoff,)
        )
        await self._db.commit()
        deleted = cursor.rowcount
        if deleted:
            logger.info("Pruned %d old telemetry rows", deleted)
        return deleted

    async def prune_loop(self) -> None:
        """Background coroutine: runs pruning periodically."""
        interval_s = self.cfg.storage.prune_interval_hours * 3600
        while True:
            await asyncio.sleep(interval_s)
            try:
                await self.prune_old_data()
            except Exception as e:
                logger.error("Prune error: %s", e)
