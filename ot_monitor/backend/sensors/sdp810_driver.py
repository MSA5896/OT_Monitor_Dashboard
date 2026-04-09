"""
sdp810_driver.py — Differential Pressure sensor driver.

Hardware:  Sensirion SDP810-500Pa or SDP31 (both I2C, same protocol)
Interface: I2C bus (SDA=GPIO2/Pin3, SCL=GPIO3/Pin5) — shared with BME280
Address:   0x25 (ADDR pin to GND)  or  0x26 (ADDR pin to VDD)

Wiring (from OT_System_Requirements_Detailed.md):
  SDP810 VDD  → RPi Pin 1  (3.3V)
  SDP810 GND  → RPi Pin 14 (GND)
  SDP810 SDA  → RPi Pin 3  (GPIO2 / SDA1)  — shared I2C bus
  SDP810 SCL  → RPi Pin 5  (GPIO3 / SCL1)  — shared I2C bus
  SDP810 ADDR → GND → I2C address 0x25
               (if BME280 is at 0x76, no address conflict)

Library: smbus2 (pip install smbus2)

SDP810 I2C Protocol (simplified flow):
  1. Send START_CONTINUOUS_MEASUREMENT command: 0x3615 (0mBar DP, no averaging)
     or 0x3616 (0mBar DP, averaging enabled) — use averaging for stable OT readings
  2. Wait ≥ 8 ms for first result
  3. Read 9 bytes:
       Bytes 0-1: Pressure (int16, big-endian)
       Byte  2:   CRC for pressure
       Bytes 3-4: Temperature (int16, big-endian) — °C × 200
       Byte  5:   CRC for temperature
       Bytes 6-7: Scale factor (int16) — divides the raw pressure reading
       Byte  8:   CRC for scale factor
  4. Differential Pressure (Pa) = pressure_raw / scale_factor

Note: The SDP810 measures bidirectional differential pressure.
      Positive = Port 1 > Port 2 (room is positive pressure — OT standard).
      Negative = Port 2 > Port 1 (room under negative pressure — ALARM).
"""

from __future__ import annotations

import logging
import struct
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# SDP810 I2C commands (register addresses sent as 2-byte commands)
_CMD_START_CONT_MASS_FLOW_AVG  = [0x36, 0x03]   # continuous, mass flow, averaging
_CMD_START_CONT_DIFF_PRESS_AVG = [0x36, 0x15]   # continuous, DP, no IRQline — USE THIS
_CMD_SOFT_RESET               = [0x00, 0x06]    # sent to general call address 0x00
_CMD_STOP_CONT                = [0x3F, 0xF9]

# CRC parameters (CRC-8, polynomial 0x31, init 0xFF)
_CRC_POLYNOMIAL = 0x31
_CRC_INIT       = 0xFF


@dataclass
class SDP810Reading:
    diff_pressure_pa: Optional[float]  # Pa — positive = room positive pressure
    temperature_c: Optional[float]     # °C (sensor internal, indicative only)
    ok: bool = True
    error: Optional[str] = None


class SDP810Driver:
    """
    Driver for Sensirion SDP810 differential pressure sensor via I2C (smbus2).

    Parameters
    ----------
    i2c_bus : int
        I2C bus number. RPi 4 default = 1 (/dev/i2c-1).
    i2c_address : int
        0x25 (ADDR→GND, default) or 0x26 (ADDR→VDD).
    """

    def __init__(
        self,
        i2c_bus: int = 1,
        i2c_address: int = 0x25,
    ):
        self.i2c_bus = i2c_bus
        self.i2c_address = i2c_address
        self._bus = None
        self._scale_factor: Optional[int] = None   # cached from first read
        self._measuring = False

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def open(self) -> None:
        """Open I2C bus and start continuous DP measurement."""
        import smbus2
        try:
            self._bus = smbus2.SMBus(self.i2c_bus)
            # Send start continuous measurement command (DP with averaging)
            self._bus.write_i2c_block_data(
                self.i2c_address, _CMD_START_CONT_DIFF_PRESS_AVG[0],
                [_CMD_START_CONT_DIFF_PRESS_AVG[1]]
            )
            self._measuring = True
            # Wait for first measurement cycle (SDP810 datasheet: ≥8 ms)
            time.sleep(0.050)
            logger.info(
                "SDP810 opened on I2C bus %d, address 0x%02X",
                self.i2c_bus, self.i2c_address,
            )
        except Exception as exc:
            logger.error("SDP810 open failed: %s", exc)
            raise

    def close(self) -> None:
        """Stop continuous mode and close I2C bus."""
        if self._bus:
            try:
                self._bus.write_i2c_block_data(
                    self.i2c_address, _CMD_STOP_CONT[0], [_CMD_STOP_CONT[1]]
                )
            except Exception:
                pass
            self._bus.close()
        self._bus = None
        self._measuring = False
        logger.info("SDP810 closed")

    # ── Reading ────────────────────────────────────────────────────────────────

    def read(self) -> SDP810Reading:
        """
        Read one differential pressure and temperature measurement.

        The SDP810 operates in continuous mode after open(). Each call to
        read() retrieves the latest averaged result from the sensor's internal
        buffer (10 Hz output rate in continuous mode).
        """
        if self._bus is None or not self._measuring:
            return SDP810Reading(diff_pressure_pa=None, temperature_c=None,
                                 ok=False, error="Not open — call open() first")
        try:
            import smbus2

            # Read 9 bytes from sensor
            raw = self._bus.read_i2c_block_data(self.i2c_address, 0x00, 9)
            return self._parse_measurement(raw)

        except Exception as exc:
            logger.warning("SDP810 read error: %s", exc)
            return SDP810Reading(diff_pressure_pa=None, temperature_c=None,
                                 ok=False, error=str(exc))

    def _parse_measurement(self, raw: list) -> SDP810Reading:
        """
        Parse 9-byte SDP810 response.

        Layout:
          Bytes 0-1: Pressure word (int16, big-endian)
          Byte  2:   CRC8 for pressure
          Bytes 3-4: Temperature word (int16, big-endian) — raw = °C × 200
          Byte  5:   CRC8 for temperature
          Bytes 6-7: Scale factor (int16, big-endian) — typically 60 for 500 Pa model
          Byte  8:   CRC8 for scale factor

        dp_pa = pressure_word / scale_factor
        temp_c = temperature_word / 200.0
        """
        # Validate CRCs
        if not self._crc_ok(raw[0:2], raw[2]):
            return SDP810Reading(diff_pressure_pa=None, temperature_c=None,
                                 ok=False, error="CRC error on pressure bytes")
        if not self._crc_ok(raw[3:5], raw[5]):
            return SDP810Reading(diff_pressure_pa=None, temperature_c=None,
                                 ok=False, error="CRC error on temperature bytes")
        if not self._crc_ok(raw[6:8], raw[8]):
            return SDP810Reading(diff_pressure_pa=None, temperature_c=None,
                                 ok=False, error="CRC error on scale factor bytes")

        # Parse signed 16-bit big-endian values
        pressure_raw = struct.unpack(">h", bytes(raw[0:2]))[0]
        temperature_raw = struct.unpack(">h", bytes(raw[3:5]))[0]
        scale_factor = struct.unpack(">h", bytes(raw[6:8]))[0]

        # Cache scale factor (it stays constant for the sensor's range)
        if scale_factor != 0:
            self._scale_factor = scale_factor

        if not self._scale_factor:
            return SDP810Reading(diff_pressure_pa=None, temperature_c=None,
                                 ok=False, error="Scale factor is zero — sensor initialisation error")

        dp_pa   = round(pressure_raw / self._scale_factor, 3)
        temp_c  = round(temperature_raw / 200.0, 2)

        # Sanity range (OTData model: -50 to 200 Pa)
        if not -50 <= dp_pa <= 200:
            return SDP810Reading(diff_pressure_pa=None, temperature_c=None,
                                 ok=False, error=f"DP out of range: {dp_pa} Pa")

        return SDP810Reading(diff_pressure_pa=dp_pa, temperature_c=temp_c, ok=True)

    @staticmethod
    def _crc_ok(data: list, received_crc: int) -> bool:
        """
        Validate CRC-8 with polynomial 0x31, init 0xFF (Sensirion standard).
        """
        crc = _CRC_INIT
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ _CRC_POLYNOMIAL
                else:
                    crc <<= 1
                crc &= 0xFF
        return crc == received_crc

    # ── Diagnostic ────────────────────────────────────────────────────────────

    def selftest(self) -> bool:
        """Read one DP measurement for verification."""
        reading = self.read()
        if not reading.ok:
            logger.error("SDP810 selftest FAILED: %s", reading.error)
            return False
        logger.info(
            "SDP810 selftest OK: DP=%.3f Pa  (sensor temp=%.2f°C)",
            reading.diff_pressure_pa, reading.temperature_c or 0.0,
        )
        return True
