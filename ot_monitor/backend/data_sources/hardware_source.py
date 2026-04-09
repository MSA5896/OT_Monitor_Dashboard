"""
hardware_source.py — Real hardware DataSource for Raspberry Pi deployment.

Reads all three physical sensors concurrently using asyncio + thread executor,
then packages the results into a TelemetryPacket and puts it in the queue.

SENSOR CONFIGURATION (updated — SDP810 removed):
  ┌──────────────┬─────────────────────┬──────────────────────────────────────┐
  │ Sensor       │ Interface           │ What it measures                     │
  ├──────────────┼─────────────────────┼──────────────────────────────────────┤
  │ BME280       │ I2C (0x76)          │ Temperature, Humidity, Pressure(hPa) │
  │ MH-Z19B      │ UART0 /dev/serial0  │ CO₂ concentration (ppm)              │
  │ PMS5003      │ UART2 /dev/ttyAMA1  │ PM1.0, PM2.5, PM10 (µg/m³)          │
  └──────────────┴─────────────────────┴──────────────────────────────────────┘

NOTE on pressure measurement:
  The SDP810 differential pressure sensor was originally included to measure
  the pressure difference between two physical points (e.g. OT room vs corridor).
  Since the requirement is just to monitor the ATMOSPHERIC BAROMETRIC PRESSURE
  of the OT room environment, the BME280 already provides this directly in hPa.
  The SDP810 has been removed from the system. BME280's pressure reading is used.

How to activate:
  In config/config.yaml, change:
    data_source:
      type: hardware

Optional config.yaml overrides:
  hardware_source:
    bme280_i2c_address: 0x76   # 0x76 (SDO→GND) or 0x77 (SDO→3.3V)
    co2_port: "/dev/serial0"   # UART0 for MH-Z19B
    pms_port: "/dev/ttyAMA1"   # UART2 for PMS5003
    poll_interval_s: 2.0
    co2_warmup_s: 180
"""

from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, Optional

from data_model import (
    DeviceHealth, DoorState, OTData, SensorHealth, TelemetryPacket,
)
from data_sources import DataSource
from sensors.bme280_driver  import BME280Driver, BME280Reading
from sensors.mhz19_driver   import MHZ19Driver, MHZ19Reading
from sensors.pms5003_driver import PMS5003Driver, PMS5003Reading

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))


class HardwareSource(DataSource):
    """
    Concrete DataSource reading BME280, MH-Z19B, and PMS5003 on Raspberry Pi.

    Architecture:
    - Sensor I/O is blocking (UART read can block for 1–2 seconds).
    - Each sensor is read in a background thread so the FastAPI event loop
      (which handles WebSocket) is never blocked.
    - All three sensors are read concurrently (3 threads in parallel).
    - Results are assembled into a TelemetryPacket and queued at 1–2 Hz.
    """

    def __init__(self, config):
        self.cfg       = config
        self._running  = False
        self._sequence = 0
        self._queue: asyncio.Queue[TelemetryPacket] = asyncio.Queue(maxsize=10)
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="sensor")

        # Read optional hardware-specific overrides from config.yaml
        hw = getattr(config, "hardware_source", None) or {}
        if isinstance(hw, dict):
            bme_addr   = hw.get("bme280_i2c_address", 0x76)
            co2_port   = hw.get("co2_port", "/dev/serial0")
            pms_port   = hw.get("pms_port", "/dev/ttyAMA1")
            poll_s     = hw.get("poll_interval_s", 2.0)
            co2_warmup = hw.get("co2_warmup_s", 180)
        else:
            bme_addr   = 0x76
            co2_port   = "/dev/serial0"
            pms_port   = "/dev/ttyAMA1"
            poll_s     = 2.0
            co2_warmup = 180

        self._poll_interval = poll_s

        # Initialise drivers (ports not yet opened)
        self._bme280 = BME280Driver(i2c_address=bme_addr)
        self._mhz19  = MHZ19Driver(port=co2_port, warmup_seconds=co2_warmup)
        self._pms    = PMS5003Driver(port=pms_port)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Open all sensor ports and start the background polling loop."""
        loop = asyncio.get_event_loop()

        try:
            await loop.run_in_executor(self._executor, self._bme280.open)
            logger.info("BME280 ready — Temperature, Humidity, Pressure")
        except Exception as exc:
            logger.error("BME280 failed to open: %s — data will show as unavailable", exc)

        try:
            await loop.run_in_executor(self._executor, self._mhz19.open)
            logger.info("MH-Z19B ready — CO₂ (warm-up: %d s)", self._mhz19.warmup_seconds)
        except Exception as exc:
            logger.error("MH-Z19B failed to open: %s — data will show as unavailable", exc)

        try:
            await loop.run_in_executor(self._executor, self._pms.open)
            logger.info("PMS5003 ready — PM1.0 / PM2.5 / PM10")
        except Exception as exc:
            logger.error("PMS5003 failed to open: %s — data will show as unavailable", exc)

        self._running = True
        asyncio.create_task(self._poll_loop())
        logger.info(
            "HardwareSource started — 3 sensors, polling every %.1f s",
            self._poll_interval,
        )

    async def stop(self) -> None:
        """Stop polling and close all sensor ports cleanly."""
        self._running = False
        loop = asyncio.get_event_loop()
        for driver, name in [
            (self._bme280, "BME280"),
            (self._mhz19,  "MH-Z19B"),
            (self._pms,    "PMS5003"),
        ]:
            try:
                await loop.run_in_executor(self._executor, driver.close)
                logger.info("%s closed", name)
            except Exception as exc:
                logger.warning("Error closing %s: %s", name, exc)
        self._executor.shutdown(wait=False)

    async def packets(self) -> AsyncIterator[TelemetryPacket]:
        """Async generator yielding TelemetryPackets from the queue."""
        while self._running:
            try:
                pkt = await asyncio.wait_for(self._queue.get(), timeout=5.0)
                yield pkt
            except asyncio.TimeoutError:
                continue

    # ── Poll loop ─────────────────────────────────────────────────────────────

    async def _poll_loop(self) -> None:
        """Read all sensors concurrently every poll_interval_s."""
        while self._running:
            start = time.monotonic()

            bme_r, co2_r, pms_r = await self._read_all_concurrent()
            pkt = self._build_packet(bme_r, co2_r, pms_r)

            try:
                self._queue.put_nowait(pkt)
            except asyncio.QueueFull:
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                await self._queue.put(pkt)

            elapsed  = time.monotonic() - start
            sleep_for = max(0.0, self._poll_interval - elapsed)
            await asyncio.sleep(sleep_for)

    async def _read_all_concurrent(self):
        """Read BME280, MH-Z19B, and PMS5003 in parallel."""
        loop = asyncio.get_event_loop()
        results = await asyncio.gather(
            loop.run_in_executor(self._executor, self._bme280.read),
            loop.run_in_executor(self._executor, self._mhz19.read),
            loop.run_in_executor(self._executor, self._pms.read),
            return_exceptions=True,
        )
        bme_r = results[0] if isinstance(results[0], BME280Reading) \
            else BME280Reading(None, None, None, ok=False, error=str(results[0]))
        co2_r = results[1] if isinstance(results[1], MHZ19Reading) \
            else MHZ19Reading(None, None, ok=False, error=str(results[1]))
        pms_r = results[2] if isinstance(results[2], PMS5003Reading) \
            else PMS5003Reading(None, None, None, None, None, None, None, None, None,
                                ok=False, error=str(results[2]))
        return bme_r, co2_r, pms_r

    def _build_packet(
        self,
        bme: BME280Reading,
        co2: MHZ19Reading,
        pms: PMS5003Reading,
    ) -> TelemetryPacket:
        """Assemble sensor readings into a TelemetryPacket."""
        self._sequence += 1

        # ── Device health ──────────────────────────────────────────────────
        health = DeviceHealth(
            temperature_sensor=SensorHealth(
                ok=bme.ok,
                error_code=_truncate_error(bme.error) if not bme.ok else None,
            ),
            humidity_sensor=SensorHealth(
                ok=bme.ok,
                error_code=_truncate_error(bme.error) if not bme.ok else None,
            ),
            pressure_sensor=SensorHealth(
                # Pressure now comes from BME280 — same ok status
                ok=bme.ok,
                error_code=_truncate_error(bme.error) if not bme.ok else None,
            ),
            pm_sensor=SensorHealth(
                ok=pms.ok,
                error_code=_truncate_error(pms.error) if not pms.ok else None,
            ),
            co2_sensor=SensorHealth(
                ok=co2.ok or co2.warming_up,
                error_code="WARMING_UP" if co2.warming_up else (
                    _truncate_error(co2.error) if not co2.ok else None
                ),
            ),
        )

        # ── OT data payload ───────────────────────────────────────────────
        # Note: diff_pressure_pa is intentionally left as None.
        # Atmospheric barometric pressure (hPa) is reported by BME280 and
        # stored in the ext dict for dashboard display.
        ext = {}
        if bme.pressure_hpa is not None:
            ext["pressure_hpa"] = bme.pressure_hpa

        data = OTData(
            temperature_c         = bme.temperature_c,
            relative_humidity_pct = bme.relative_humidity_pct,
            pm1_ugm3              = pms.pm1_ugm3,
            pm25_ugm3             = pms.pm25_ugm3,
            pm10_ugm3             = pms.pm10_ugm3,
            diff_pressure_pa      = None,   # SDP810 removed — not applicable
            co2_ppm               = co2.co2_ppm,
            door_state            = DoorState.UNKNOWN,
            ext                   = ext,
        )

        return TelemetryPacket(
            api_version    = "1.0",
            schema_version = "1.0",
            timestamp_iso  = datetime.now(IST).isoformat(),
            ot_id          = self.cfg.ot_id,
            sequence       = self._sequence,
            data           = data,
            device_health  = health,
        )


def _truncate_error(msg: Optional[str], max_len: int = 64) -> Optional[str]:
    """Shorten error strings to fit in the dashboard health card."""
    if msg is None:
        return None
    return msg[:max_len] + ("…" if len(msg) > max_len else "")
