"""
scd30_driver.py — CO₂, Temperature & Humidity sensor driver.

Hardware:  Sensirion SCD30 NDIR CO₂ sensor module
Interface: I2C bus (SDA=GPIO2/Pin3, SCL=GPIO3/Pin5)
Address:   0x61 (fixed — not configurable)
Library:   adafruit-circuitpython-scd30  +  adafruit-blinka

Wiring:
  SCD30 VCC  → RPi Pin 1  (3.3V)
  SCD30 GND  → RPi Pin 6  (GND)
  SCD30 SDA  → RPi Pin 3  (GPIO2 / SDA1)
  SCD30 SCL  → RPi Pin 5  (GPIO3 / SCL1)
  SCD30 SEL  → RPi Pin 6  (GND)   ← tie LOW to select I2C mode (not UART)

IMPORTANT — I2C clock stretching:
  The SCD30 uses clock stretching which the RPi I2C controller handles poorly
  at 100kHz. Slow the I2C bus to 10kHz by adding this to /boot/firmware/config.txt
  (or /boot/config.txt on older RPi OS):
    dtparam=i2c_arm_baudrate=10000
  Then reboot. This resolves any read timeout or CRC errors.

Install:
  pip install adafruit-circuitpython-scd30 adafruit-blinka

Measurements provided:
  - CO₂ concentration (ppm)   — NDIR, range 400–10000 ppm
  - Temperature (°C)           — compensated, range -40–70°C
  - Relative Humidity (%RH)    — range 0–95%

Optional features used:
  - Ambient pressure compensation: feed local hPa to improve CO₂ accuracy
  - Temperature offset: subtract self-heating error (typically 0–3°C)
  - Measurement interval: configurable polling cadence (default 2 s)

Note on CO₂ readings < 400 ppm:
  SCD30 outputs a minimum of ~400 ppm (outdoor fresh air baseline).
  Values below 400 in a sealed indoor room indicate the sensor needs
  zero-point recalibration via Automatic Self-Calibration (ASC) or
  the forced recalibration command. ASC is enabled by default and
  runs in the background over 7+ days of operation.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

_SCD30_I2C_ADDR = 0x61
_WARMUP_SECONDS = 10     # time before first measurement is ready
_POLL_TIMEOUT   = 5.0    # max seconds to wait for data_available


@dataclass
class SCD30Reading:
    co2_ppm:               Optional[float]   # CO₂ ppm (400–10000)
    temperature_c:         Optional[float]   # °C
    relative_humidity_pct: Optional[float]   # %RH
    ok: bool = True
    warming_up: bool = False
    error: Optional[str] = None


class SCD30Driver:
    """
    Driver for Sensirion SCD30 over I2C using adafruit-circuitpython-scd30.

    Parameters
    ----------
    measurement_interval_s : int
        How often the sensor takes a new measurement (2–1800 s). Default 2 s.
    temperature_offset_c : float
        Degrees to subtract from the reported temperature to compensate for
        enclosure self-heating. Typical value: 0–3°C. Default 0.
    ambient_pressure_hpa : int
        Ambient pressure in hPa for CO₂ compensation. Default 1013.
        Update this dynamically if you have a barometric pressure source.
    """

    def __init__(
        self,
        measurement_interval_s: int = 2,
        temperature_offset_c: float = 0.0,
        ambient_pressure_hpa: int = 1013,
    ):
        self.measurement_interval_s = measurement_interval_s
        self.temperature_offset_c   = temperature_offset_c
        self.ambient_pressure_hpa   = ambient_pressure_hpa
        self._sensor    = None
        self._i2c       = None
        self._start_time: Optional[float] = None

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def open(self) -> None:
        """Initialise I2C bus and SCD30 sensor with continuous measurement."""
        try:
            import board
            import busio
            import adafruit_scd30

            # Use 10 kHz for clock-stretching compatibility
            self._i2c = busio.I2C(board.SCL, board.SDA, frequency=10000)
            self._sensor = adafruit_scd30.SCD30(self._i2c)

            # Configure measurement interval
            self._sensor.measurement_interval = self.measurement_interval_s

            # Ambient pressure compensation improves CO₂ accuracy by ~1–3%
            self._sensor.ambient_pressure = self.ambient_pressure_hpa

            # Temperature offset to subtract self-heating
            self._sensor.temperature_offset = self.temperature_offset_c

            self._start_time = time.monotonic()

            logger.info(
                "SCD30 opened on I2C 0x%02X  (interval=%ds, offset=%.1f°C, pressure=%dhPa)",
                _SCD30_I2C_ADDR,
                self.measurement_interval_s,
                self.temperature_offset_c,
                self.ambient_pressure_hpa,
            )
        except Exception as exc:
            logger.error("SCD30 open failed: %s", exc)
            raise

    def close(self) -> None:
        """Release I2C bus."""
        try:
            if self._i2c:
                self._i2c.deinit()
        except Exception:
            pass
        self._sensor = None
        self._i2c    = None
        logger.info("SCD30 closed")

    # ── Reading ────────────────────────────────────────────────────────────────

    @property
    def is_warming_up(self) -> bool:
        if self._start_time is None:
            return True
        return (time.monotonic() - self._start_time) < _WARMUP_SECONDS

    def read(self) -> SCD30Reading:
        """
        Wait for the SCD30 to signal data_available, then return one reading.

        On first call after open(), the sensor may need up to 10 s to warm up.
        Returns SCD30Reading with ok=False on any error, warming_up=True during
        the initial warm-up period.
        """
        if self._sensor is None:
            return SCD30Reading(
                co2_ppm=None, temperature_c=None, relative_humidity_pct=None,
                ok=False, error="Sensor not initialised — call open() first",
            )

        if self.is_warming_up:
            elapsed   = time.monotonic() - self._start_time
            remaining = int(_WARMUP_SECONDS - elapsed)
            return SCD30Reading(
                co2_ppm=None, temperature_c=None, relative_humidity_pct=None,
                ok=True, warming_up=True,
                error=f"Warming up ({remaining}s remaining)",
            )

        try:
            # Poll data_available — SCD30 signals when a new measurement is ready
            deadline = time.monotonic() + _POLL_TIMEOUT
            while not self._sensor.data_available:
                if time.monotonic() > deadline:
                    return SCD30Reading(
                        co2_ppm=None, temperature_c=None, relative_humidity_pct=None,
                        ok=False,
                        error=f"Timeout: no data from SCD30 within {_POLL_TIMEOUT:.0f}s",
                    )
                time.sleep(0.1)

            co2  = round(self._sensor.CO2, 1)
            temp = round(self._sensor.temperature, 2)
            hum  = round(self._sensor.relative_humidity, 1)

            # Sanity bounds
            if not 0 <= co2 <= 10000:
                raise ValueError(f"CO₂ out of physical range: {co2} ppm")
            if not -40 <= temp <= 70:
                raise ValueError(f"Temperature out of sensor range: {temp} °C")
            if not 0 <= hum <= 100:
                raise ValueError(f"Humidity out of range: {hum} %RH")

            return SCD30Reading(
                co2_ppm=co2,
                temperature_c=temp,
                relative_humidity_pct=hum,
                ok=True,
            )

        except Exception as exc:
            logger.warning("SCD30 read error: %s", exc)
            return SCD30Reading(
                co2_ppm=None, temperature_c=None, relative_humidity_pct=None,
                ok=False, error=str(exc),
            )

    # ── Calibration ───────────────────────────────────────────────────────────

    def set_forced_recalibration(self, reference_co2_ppm: int = 400) -> None:
        """
        Forced Recalibration (FRC) — set a known CO₂ reference value.

        Use only when the sensor is in a known-concentration environment
        (e.g. fresh outdoor air ≈ 420 ppm). Overrides ASC.

        Parameters
        ----------
        reference_co2_ppm : int
            Known CO₂ concentration in ppm at time of calibration.
        """
        if self._sensor is None:
            logger.error("Cannot calibrate — sensor not open")
            return
        self._sensor.forced_recalibration_reference = reference_co2_ppm
        logger.warning(
            "SCD30 forced recalibration set to %d ppm — ensure sensor is in "
            "a known-concentration environment first", reference_co2_ppm,
        )

    # ── Diagnostic ────────────────────────────────────────────────────────────

    def selftest(self) -> bool:
        """Read one measurement and log the result."""
        reading = self.read()
        if reading.warming_up:
            logger.info("SCD30 selftest: warming up (normal at startup)")
            return True
        if not reading.ok:
            logger.error("SCD30 selftest FAILED: %s", reading.error)
            return False
        logger.info(
            "SCD30 selftest OK: CO₂=%.1f ppm  Temp=%.2f°C  Humidity=%.1f%%RH",
            reading.co2_ppm, reading.temperature_c, reading.relative_humidity_pct,
        )
        return True
