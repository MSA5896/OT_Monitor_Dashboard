"""
simulator_source.py – Built-in data source that generates synthetic OT telemetry.
Used when no physical hardware is attached (development / CI / demos).
Supports multiple simulation scenarios selectable via SIMULATOR_SCENARIO env var
or programmatically by setting .scenario attribute before start().

Scenarios:
  normal       – Steady values within safe range with small noise.
  temp_drift   – Gradual temperature rise triggering WARNING then ALARM.
  pm_spike     – Sudden PM2.5/PM10 spike mimicking surgical smoke.
  disconnect   – Periodic drops of ~5 s to test reconnect handling.
  sensor_fault – Random sensor fields set to None (fault injection).
  power_loss   – Mains lost at t=20s; runs on backup battery and drains.
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
import random
import time
from datetime import datetime, timezone, timedelta
from typing import AsyncIterator, Optional

from data_model import DoorState, OTData, PowerSource, TelemetryPacket, DeviceHealth, SensorHealth
from data_sources import DataSource

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))


class SimulatorSource(DataSource):
    def __init__(self, config, scenario: Optional[str] = None):
        self.cfg      = config
        self.scenario = scenario or os.environ.get("SIMULATOR_SCENARIO", "normal")
        self._running = False
        self._queue: asyncio.Queue[TelemetryPacket] = asyncio.Queue(maxsize=10)
        self._sequence = 0

    async def start(self) -> None:
        self._running = True
        asyncio.create_task(self._generate_loop())
        logger.info("SimulatorSource started (scenario=%s)", self.scenario)

    async def stop(self) -> None:
        self._running = False

    async def packets(self) -> AsyncIterator[TelemetryPacket]:
        while self._running:
            try:
                pkt = await asyncio.wait_for(self._queue.get(), timeout=2.0)
                yield pkt
            except asyncio.TimeoutError:
                continue

    # ── Generation loop ──────────────────────────────────────────────────────

    async def _generate_loop(self) -> None:
        """Produce one packet per second according to current scenario."""
        elapsed = 0.0
        base_temp = 22.0
        base_hum  = 52.0
        base_pm25 = 12.0
        base_pm1  = 6.0
        base_pm10 = 20.0
        base_dp   = 8.0

        while self._running:
            await asyncio.sleep(1.0)
            elapsed += 1.0
            self._sequence += 1
            t = elapsed

            # Default: normal fluctuation
            temp  = base_temp + 0.5 * math.sin(t / 60) + random.gauss(0, 0.1)
            hum   = base_hum  + 2.0 * math.sin(t / 90 + 1) + random.gauss(0, 0.3)
            pm1   = base_pm1  + abs(random.gauss(0, 1.0))
            pm25  = base_pm25 + abs(random.gauss(0, 1.5))
            pm10  = base_pm10 + abs(random.gauss(0, 2.0))
            dp    = base_dp   + random.gauss(0, 0.5)
            door  = DoorState.CLOSED
            fault_temp = False
            fault_pm   = False
            skip_packet = False

            # Power: on mains by default, backup battery kept topped up (95–100%)
            power_source = PowerSource.MAINS
            battery_pct  = min(100.0, 97.0 + 3.0 * math.sin(t / 200))

            # ── Scenario overrides ────────────────────────────────────────────
            if self.scenario == "temp_drift":
                temp += min(t / 30, 8.0)   # +8 °C over 4 min

            elif self.scenario == "pm_spike":
                if 30 <= t <= 60:
                    pm1  += 80  + 20 * math.sin((t - 30) * 0.3)
                    pm25 += 120 + 30 * math.sin((t - 30) * 0.3)
                    pm10 += 200 + 50 * math.sin((t - 30) * 0.3)
                elif 60 < t <= 120:
                    # Gradual recovery
                    decay = (t - 60) / 60
                    pm25 = max(base_pm25, pm25 - 100 * decay)
                    pm10 = max(base_pm10, pm10 - 150 * decay)

            elif self.scenario == "disconnect":
                # Drop packets for 5 s every 30 s
                if int(t) % 30 < 5:
                    skip_packet = True
                    await asyncio.sleep(0)
                    continue

            elif self.scenario == "sensor_fault":
                if random.random() < 0.15:   # 15% chance per second
                    fault_temp = True
                if random.random() < 0.10:
                    fault_pm = True

            elif self.scenario == "power_loss":
                # Mains lost at t=20s; run on battery and drain ~0.5%/s
                if t >= 20:
                    power_source = PowerSource.BATTERY
                    battery_pct  = max(0.0, 100.0 - 0.5 * (t - 20))

            # ── Build health ────────────────────────────────────────────────
            health = DeviceHealth(
                temperature_sensor=SensorHealth(ok=not fault_temp,
                                                error_code="E_TIMEOUT" if fault_temp else None),
                pm_sensor=SensorHealth(ok=not fault_pm,
                                       error_code="E_CRC" if fault_pm else None),
            )

            data = OTData(
                temperature_c          = None if fault_temp else round(max(15, min(35, temp)), 2),
                relative_humidity_pct  = round(max(10, min(95, hum)), 1),
                pm1_ugm3               = None if fault_pm  else round(max(0, pm1), 2),
                pm25_ugm3              = None if fault_pm  else round(max(0, pm25), 2),
                pm10_ugm3              = None if fault_pm  else round(max(0, pm10), 2),
                diff_pressure_pa       = round(max(-5, dp), 2),
                door_state             = door,
                co2_ppm                = round(420 + 10 * math.sin(t / 120) + random.gauss(0, 5), 1),
                voc_ppb                = round(max(0, 50 + random.gauss(0, 10)), 1),
                battery_pct            = round(battery_pct, 1),
                power_source           = power_source,
            )

            pkt = TelemetryPacket(
                api_version    = "1.0",
                schema_version = "1.0",
                timestamp_iso  = datetime.now(IST).isoformat(),
                ot_id          = self.cfg.ot_id,
                sequence       = self._sequence,
                data           = data,
                device_health  = health,
            )

            try:
                self._queue.put_nowait(pkt)
            except asyncio.QueueFull:
                pass  # dashboard too slow — drop oldest
