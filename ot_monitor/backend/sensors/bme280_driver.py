"""
bme280_driver.py — Temperature, Humidity & Barometric Pressure sensor driver.

Hardware:  Bosch BME280 breakout board
Interface: I2C bus (SDA=GPIO2/Pin3, SCL=GPIO3/Pin5)
Address:   0x76 (SDO tied to GND)  or  0x77 (SDO tied to 3.3V)
Library:   adafruit-circuitpython-bme280

Wiring (from OT_System_Requirements_Detailed.md):
  BME280 VCC  → RPi Pin 1  (3.3V)
  BME280 GND  → RPi Pin 6  (GND)
  BME280 SDA  → RPi Pin 3  (GPIO2 / SDA1)
  BME280 SCL  → RPi Pin 5  (GPIO3 / SCL1)
  BME280 SDO  → RPi Pin 6  (GND)  → I2C address = 0x76

Install:
  pip install adafruit-circuitpython-bme280 adafruit-blinka

Note: Forced mode is used (read-then-sleep) to avoid sensor self-heating error
      (+0.5–1.5 °C in normal/continuous mode). This gives accurate readings.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class BME280Reading:
    temperature_c: Optional[float]          # °C
    relative_humidity_pct: Optional[float]  # %RH
    pressure_hpa: Optional[float]           # hPa
    ok: bool = True
    error: Optional[str] = None


class BME280Driver:
    """
    Driver for BME280 over I2C using adafruit-circuitpython-bme280.

    Parameters
    ----------
    i2c_address : int
        I2C address — 0x76 (SDO→GND, default) or 0x77 (SDO→3.3V).
    sea_level_pressure_hpa : float
        Reference sea-level pressure for altitude computation (not used in OT
        system, but kept for completeness).
    """

    def __init__(
        self,
        i2c_address: int = 0x76,
        sea_level_pressure_hpa: float = 1013.25,
    ):
        self.i2c_address = i2c_address
        self.sea_level_pressure_hpa = sea_level_pressure_hpa
        self._sensor = None
        self._i2c = None

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def open(self) -> None:
        """Initialise I2C bus and BME280 sensor in forced mode."""
        try:
            import board                          # adafruit blinka
            import busio
            import adafruit_bme280.advanced as adafruit_bme280

            self._i2c = busio.I2C(board.SCL, board.SDA)
            self._sensor = adafruit_bme280.Adafruit_BME280_I2C(
                self._i2c, address=self.i2c_address
            )
            # ── FORCED MODE: sensor sleeps between measurements ─────────────
            # This eliminates self-heating error. Sensor wakes, measures, sleeps.
            self._sensor.mode = adafruit_bme280.MODE_FORCE

            # Oversampling — x4 for temperature & humidity, x1 for pressure
            # (balances accuracy vs noise; ideal for 1 Hz read rate)
            self._sensor.overscan_temperature = adafruit_bme280.OVERSCAN_X4
            self._sensor.overscan_humidity    = adafruit_bme280.OVERSCAN_X4
            self._sensor.overscan_pressure    = adafruit_bme280.OVERSCAN_X1

            # IIR filter coefficient — smooths pressure jitter from doors/HVAC
            self._sensor.iir_filter = adafruit_bme280.IIR_FILTER_X4

            self._sensor.sea_level_pressure = self.sea_level_pressure_hpa
            logger.info(
                "BME280 opened on I2C address 0x%02X (forced mode)", self.i2c_address
            )
        except Exception as exc:
            logger.error("BME280 open failed: %s", exc)
            raise

    def close(self) -> None:
        """Release I2C bus."""
        try:
            if self._i2c:
                self._i2c.deinit()
        except Exception:
            pass
        self._sensor = None
        self._i2c = None
        logger.info("BME280 closed")

    # ── Reading ────────────────────────────────────────────────────────────────

    def read(self) -> BME280Reading:
        """
        Read temperature, humidity, and pressure.

        Returns a BME280Reading dataclass. On sensor error, ok=False and
        all physical values are None.
        """
        if self._sensor is None:
            return BME280Reading(
                temperature_c=None,
                relative_humidity_pct=None,
                pressure_hpa=None,
                ok=False,
                error="Sensor not initialised — call open() first",
            )

        try:
            import adafruit_bme280.advanced as adafruit_bme280

            # Trigger forced-mode measurement
            self._sensor.mode = adafruit_bme280.MODE_FORCE

            # Wait for measurement to complete (~3 ms for x4 oversample)
            time.sleep(0.010)

            temp_c = round(self._sensor.temperature, 2)
            hum_pct = round(self._sensor.relative_humidity, 1)
            pres_hpa = round(self._sensor.pressure, 2)

            # Sanity bounds (physical limits, not threshold limits)
            if not -40 <= temp_c <= 85:
                raise ValueError(f"Temperature out of sensor range: {temp_c} °C")
            if not 0 <= hum_pct <= 100:
                raise ValueError(f"Humidity out of sensor range: {hum_pct} %RH")
            if not 300 <= pres_hpa <= 1100:
                raise ValueError(f"Pressure out of sensor range: {pres_hpa} hPa")

            return BME280Reading(
                temperature_c=temp_c,
                relative_humidity_pct=hum_pct,
                pressure_hpa=pres_hpa,
                ok=True,
            )

        except Exception as exc:
            logger.warning("BME280 read error: %s", exc)
            return BME280Reading(
                temperature_c=None,
                relative_humidity_pct=None,
                pressure_hpa=None,
                ok=False,
                error=str(exc),
            )

    # ── Quick diagnostic ───────────────────────────────────────────────────────

    def selftest(self) -> bool:
        """Return True if sensor is reachable and returns valid data."""
        reading = self.read()
        if not reading.ok:
            logger.error("BME280 selftest FAILED: %s", reading.error)
            return False
        logger.info(
            "BME280 selftest OK: %.2f°C  %.1f%%RH  %.2f hPa",
            reading.temperature_c,
            reading.relative_humidity_pct,
            reading.pressure_hpa,
        )
        return True
