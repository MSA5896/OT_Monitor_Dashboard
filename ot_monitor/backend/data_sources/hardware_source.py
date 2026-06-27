"""
hardware_source.py — Real hardware DataSource for Raspberry Pi deployment.

Reads three physical sensors concurrently using asyncio + thread executor,
then packages the results into a TelemetryPacket and puts it in the queue.

SENSOR CONFIGURATION:
  ┌──────────────┬──────────────────────────────┬────────────────────────────────────────┐
  │ Sensor       │ Interface                    │ What it measures                       │
  ├──────────────┼──────────────────────────────┼────────────────────────────────────────┤
  │ SCD30        │ I2C 0x61  (10 kHz)          │ CO₂ ppm, Temperature °C, Humidity %RH │
  │ BME280       │ I2C 0x76  (10 kHz)          │ Barometric Pressure hPa                │
  │ PMS5003      │ UART0 /dev/serial0 GPIO14/15 │ PM1.0, PM2.5, PM10 (µg/m³)            │
  └──────────────┴──────────────────────────────┴────────────────────────────────────────┘

Sensor responsibilities:
  - SCD30  → primary CO₂, Temperature, Humidity readings
  - BME280 → barometric pressure only (hPa); temperature/humidity fields ignored
             — also supplies ambient pressure to SCD30 for CO₂ compensation
  - PMS5003 → particulate matter PM1 / PM2.5 / PM10

How to activate:
  In config/config.yaml, change:
    data_source:
      type: hardware

Optional config.yaml overrides:
  hardware_source:
    scd30_measurement_interval_s: 2      # 2–1800 s, default 2
    scd30_temperature_offset_c:   0.0    # subtract this from SCD30 temp
    bme280_i2c_address:           0x76   # 0x76 (SDO→GND) or 0x77 (SDO→3.3V)
    pms_port:                     "/dev/serial0"  # UART0: GPIO14(TX/Pin8), GPIO15(RX/Pin10)
    poll_interval_s:              2.0
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
from sensors.scd30_driver   import SCD30Driver,   SCD30Reading
from sensors.bme280_driver  import BME280Driver,  BME280Reading
from sensors.pms5003_driver import PMS5003Driver, PMS5003Reading

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))


class HardwareSource(DataSource):
    """
    Concrete DataSource reading SCD30, BME280, and PMS5003 on Raspberry Pi.

    Architecture:
    - Sensor I/O is blocking (UART read can block 1–2 s, SCD30 polls data_available).
    - Each sensor is read in a background thread — the FastAPI event loop is never blocked.
    - All three sensors are read concurrently (3 threads in parallel).
    - BME280 pressure is fed back to SCD30 for CO₂ ambient pressure compensation.
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
            scd30_interval = int(hw.get("scd30_measurement_interval_s", 2))
            scd30_offset   = float(hw.get("scd30_temperature_offset_c", 0.0))
            bme_addr       = hw.get("bme280_i2c_address", 0x76)
            pms_port       = hw.get("pms_port", "/dev/serial0")
            poll_s         = float(hw.get("poll_interval_s", 2.0))
        else:
            scd30_interval = 2
            scd30_offset   = 0.0
            bme_addr       = 0x76
            pms_port       = "/dev/serial0"
            poll_s         = 2.0

        self._poll_interval = poll_s

        # Initialise drivers (ports not yet opened)
        # SCD30 starts with default ambient pressure; updated from BME280 each cycle
        self._scd30  = SCD30Driver(
            measurement_interval_s=scd30_interval,
            temperature_offset_c=scd30_offset,
            ambient_pressure_hpa=1013,
        )
        self._bme280 = BME280Driver(i2c_address=bme_addr)
        self._pms    = PMS5003Driver(port=pms_port)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Open all sensor ports and start the background polling loop."""
        loop = asyncio.get_event_loop()

        try:
            await loop.run_in_executor(self._executor, self._scd30.open)
            logger.info("SCD30 ready — CO₂, Temperature, Humidity")
        except Exception as exc:
            logger.error("SCD30 failed to open: %s — CO₂/temp/humidity unavailable", exc)

        try:
            await loop.run_in_executor(self._executor, self._bme280.open)
            logger.info("BME280 ready — Barometric Pressure")
        except Exception as exc:
            logger.error("BME280 failed to open: %s — pressure unavailable", exc)

        try:
            await loop.run_in_executor(self._executor, self._pms.open)
            logger.info("PMS5003 ready — PM1.0 / PM2.5 / PM10")
        except Exception as exc:
            logger.error("PMS5003 failed to open: %s — PM unavailable", exc)

        self._running = True
        asyncio.create_task(self._poll_loop())
        logger.info(
            "HardwareSource started — 3 sensors (SCD30 + BME280 + PMS5003), polling every %.1f s",
            self._poll_interval,
        )

    async def stop(self) -> None:
        """Stop polling and close all sensor ports cleanly."""
        self._running = False
        loop = asyncio.get_event_loop()
        for driver, name in [
            (self._scd30,  "SCD30"),
            (self._bme280, "BME280"),
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

            scd_r, bme_r, pms_r = await self._read_all_concurrent()

            # Feed BME280 pressure back to SCD30 for CO₂ compensation
            if bme_r.ok and bme_r.pressure_hpa is not None:
                self._scd30.ambient_pressure_hpa = int(bme_r.pressure_hpa)
                try:
                    self._scd30._sensor.ambient_pressure = int(bme_r.pressure_hpa)
                except Exception:
                    pass

            pkt = self._build_packet(scd_r, bme_r, pms_r)

            try:
                self._queue.put_nowait(pkt)
            except asyncio.QueueFull:
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                await self._queue.put(pkt)

            elapsed   = time.monotonic() - start
            sleep_for = max(0.0, self._poll_interval - elapsed)
            await asyncio.sleep(sleep_for)

    async def _read_all_concurrent(self):
        """Read SCD30, BME280, and PMS5003 in parallel."""
        loop = asyncio.get_event_loop()
        results = await asyncio.gather(
            loop.run_in_executor(self._executor, self._scd30.read),
            loop.run_in_executor(self._executor, self._bme280.read),
            loop.run_in_executor(self._executor, self._pms.read),
            return_exceptions=True,
        )
        scd_r = results[0] if isinstance(results[0], SCD30Reading) \
            else SCD30Reading(None, None, None, ok=False, error=str(results[0]))
        bme_r = results[1] if isinstance(results[1], BME280Reading) \
            else BME280Reading(None, None, None, ok=False, error=str(results[1]))
        pms_r = results[2] if isinstance(results[2], PMS5003Reading) \
            else PMS5003Reading(None, None, None, None, None, None, None, None, None,
                                ok=False, error=str(results[2]))
        return scd_r, bme_r, pms_r

    def _build_packet(
        self,
        scd: SCD30Reading,
        bme: BME280Reading,
        pms: PMS5003Reading,
    ) -> TelemetryPacket:
        """Assemble sensor readings into a TelemetryPacket."""
        self._sequence += 1

        scd_health = SensorHealth(
            ok=scd.ok or scd.warming_up,
            error_code="WARMING_UP" if scd.warming_up else (
                _truncate_error(scd.error) if not scd.ok else None
            ),
        )

        health = DeviceHealth(
            temperature_sensor=scd_health,
            humidity_sensor=scd_health,
            co2_sensor=scd_health,
            pm_sensor=SensorHealth(
                ok=pms.ok,
                error_code=_truncate_error(pms.error) if not pms.ok else None,
            ),
            pressure_sensor=SensorHealth(
                ok=bme.ok,
                error_code=_truncate_error(bme.error) if not bme.ok else None,
            ),
        )

        # Barometric pressure from BME280 → ext dict for dashboard display
        ext = {}
        if bme.ok and bme.pressure_hpa is not None:
            ext["pressure_hpa"] = bme.pressure_hpa

        data = OTData(
            temperature_c         = scd.temperature_c,
            relative_humidity_pct = scd.relative_humidity_pct,
            pm1_ugm3              = pms.pm1_ugm3,
            pm25_ugm3             = pms.pm25_ugm3,
            pm10_ugm3             = pms.pm10_ugm3,
            diff_pressure_pa      = None,
            co2_ppm               = scd.co2_ppm,
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
    if msg is None:
        return None
    return msg[:max_len] + ("…" if len(msg) > max_len else "")
