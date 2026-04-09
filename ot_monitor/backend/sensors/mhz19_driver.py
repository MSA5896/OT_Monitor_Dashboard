"""
mhz19_driver.py — CO₂ concentration sensor driver.

Hardware:  Winsen MH-Z19B Non-Dispersive Infrared (NDIR) CO₂ sensor
Interface: UART0 (/dev/serial0 on RPi 4)
           Baud rate: 9600, 8N1
Wiring (from OT_System_Requirements_Detailed.md):
  MH-Z19B Vin  → RPi Pin 4  (5V)
  MH-Z19B GND  → RPi Pin 14 (GND)
  MH-Z19B TX   → RPi Pin 10 (GPIO15 / UART0 RX)
  MH-Z19B RX   → RPi Pin 8  (GPIO14 / UART0 TX)

IMPORTANT — Enable UART0 serial port on RPi:
  1. Run: sudo raspi-config
  2. Go to: Interface Options → Serial Port
  3. "Would you like a login shell to be accessible over the serial port?" → NO
  4. "Would you like the serial port hardware to be enabled?" → YES
  5. Reboot: sudo reboot
  The port will appear as /dev/serial0 → /dev/ttyAMA0

Library: pyserial (pip install pyserial)
         mh_z19  (pip install mh_z19)  — optional, we implement protocol directly

Protocol: Command-Response over UART.
  Command to read CO₂:
    0xFF 0x01 0x86 0x00 0x00 0x00 0x00 0x00 0x79
  Response (9 bytes):
    Byte 0: 0xFF (start)
    Byte 1: 0x86 (command echo)
    Byte 2: High byte of CO₂ ppm
    Byte 3: Low byte of CO₂ ppm
    Byte 4-7: Temperature & status (version dependent)
    Byte 8: Checksum = 0xFF - ((sum of bytes 1-7) % 256) + 1

Warm-up: MH-Z19B requires a minimum 3-minute warm-up after power-on
         before outputting valid CO₂ readings. During warm-up, readings
         are set to None and the dashboard shows "Warming Up…".
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Command bytes (read CO₂ measurement)
_CMD_READ_CO2 = bytes([0xFF, 0x01, 0x86, 0x00, 0x00, 0x00, 0x00, 0x00, 0x79])
_RESPONSE_LEN = 9

# Warm-up required before valid readings
_WARMUP_SECONDS = 180   # 3 minutes (manufacturer specification)


@dataclass
class MHZ19Reading:
    co2_ppm: Optional[float]    # CO₂ concentration in ppm
    temperature_c: Optional[float]  # Sensor internal temperature (indicative only)
    ok: bool = True
    warming_up: bool = False     # True during 3-min warm-up period
    error: Optional[str] = None


class MHZ19Driver:
    """
    Driver for MH-Z19B CO₂ sensor over UART.

    Implements the UART binary protocol directly without external libraries,
    for maximum reliability and portability.

    Parameters
    ----------
    port : str
        Serial port. Default = '/dev/serial0' (UART0 on RPi).
    warmup_seconds : float
        Warm-up delay. Default = 180 s (3 minutes per datasheet).
    timeout_s : float
        Read timeout per command-response cycle.
    """

    def __init__(
        self,
        port: str = "/dev/serial0",
        warmup_seconds: float = _WARMUP_SECONDS,
        timeout_s: float = 1.5,
    ):
        self.port = port
        self.warmup_seconds = warmup_seconds
        self.timeout_s = timeout_s
        self._serial = None
        self._start_time: Optional[float] = None

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def open(self) -> None:
        """Open UART port and record start time for warm-up tracking."""
        import serial
        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=9600,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout_s,
            )
            self._serial.reset_input_buffer()
            self._start_time = time.monotonic()
            logger.info(
                "MH-Z19B opened on %s — warm-up period: %d s",
                self.port, self.warmup_seconds,
            )
        except Exception as exc:
            logger.error("MH-Z19B open failed on %s: %s", self.port, exc)
            raise

    def close(self) -> None:
        """Close UART port."""
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._serial = None
        logger.info("MH-Z19B closed")

    # ── Reading ────────────────────────────────────────────────────────────────

    @property
    def is_warming_up(self) -> bool:
        """True during the mandatory 3-minute warm-up period after power-on."""
        if self._start_time is None:
            return True
        return (time.monotonic() - self._start_time) < self.warmup_seconds

    def read(self) -> MHZ19Reading:
        """
        Send a read command and parse the 9-byte CO₂ response.

        Returns MHZ19Reading. During warm-up, returns warming_up=True
        and co2_ppm=None — the dashboard should show "Warming Up…".
        """
        if self._serial is None or not self._serial.is_open:
            return MHZ19Reading(co2_ppm=None, temperature_c=None, ok=False,
                                error="Port not open — call open() first")

        if self.is_warming_up:
            elapsed = time.monotonic() - self._start_time
            remaining = int(self.warmup_seconds - elapsed)
            logger.debug("MH-Z19B warming up — %d s remaining", remaining)
            return MHZ19Reading(co2_ppm=None, temperature_c=None,
                                ok=True, warming_up=True,
                                error=f"Warming up ({remaining}s remaining)")

        try:
            # Flush stale data before sending command
            self._serial.reset_input_buffer()

            # Send read command
            self._serial.write(_CMD_READ_CO2)
            self._serial.flush()

            # Read 9-byte response
            response = self._serial.read(_RESPONSE_LEN)

            if len(response) < _RESPONSE_LEN:
                raise IOError(
                    f"Incomplete response: got {len(response)} bytes, expected {_RESPONSE_LEN}"
                )

            return self._parse_response(response)

        except Exception as exc:
            logger.warning("MH-Z19B read error: %s", exc)
            return MHZ19Reading(co2_ppm=None, temperature_c=None,
                                ok=False, error=str(exc))

    def _parse_response(self, response: bytes) -> MHZ19Reading:
        """
        Parse and verify a 9-byte MH-Z19B response.

        Checksum algorithm:
          checksum = 0xFF - ((sum of bytes 1 through 7) % 256) + 1
          The result is masked to one byte: & 0xFF
        """
        # Start byte check
        if response[0] != 0xFF:
            return MHZ19Reading(co2_ppm=None, temperature_c=None, ok=False,
                                error=f"Bad start byte: 0x{response[0]:02X}")

        # Command echo check
        if response[1] != 0x86:
            return MHZ19Reading(co2_ppm=None, temperature_c=None, ok=False,
                                error=f"Unexpected command byte: 0x{response[1]:02X}")

        # Verify checksum
        expected = (0xFF - (sum(response[1:8]) % 256) + 1) & 0xFF
        received = response[8]
        if expected != received:
            return MHZ19Reading(co2_ppm=None, temperature_c=None, ok=False,
                                error=f"Checksum mismatch: expected 0x{expected:02X}, "
                                      f"got 0x{received:02X}")

        # CO₂ value (bytes 2 and 3, big-endian)
        co2_ppm = float((response[2] << 8) | response[3])

        # Temperature value: byte 4 encodes temperature as (value - 40) °C
        # This is the sensor's internal temperature — informational only
        temp_c = float(response[4]) - 40.0

        # Sanity check: CO₂ physical range
        if not 0 <= co2_ppm <= 10000:
            return MHZ19Reading(co2_ppm=None, temperature_c=None, ok=False,
                                error=f"CO₂ out of range: {co2_ppm} ppm")

        return MHZ19Reading(co2_ppm=co2_ppm, temperature_c=temp_c, ok=True)

    # ── Calibration ───────────────────────────────────────────────────────────

    def calibrate_zero(self) -> bool:
        """
        Perform zero-point calibration (400 ppm reference — outdoor fresh air).

        IMPORTANT: Sensor must be exposed to fresh outdoor air (400 ppm CO₂)
        for at least 20 minutes before running this command.
        Use only during scheduled maintenance, not normal operation.
        """
        if self._serial is None or not self._serial.is_open:
            return False

        cmd_zero = bytes([0xFF, 0x01, 0x87, 0x00, 0x00, 0x00, 0x00, 0x00, 0x78])
        try:
            self._serial.write(cmd_zero)
            self._serial.flush()
            logger.warning(
                "MH-Z19B zero-point calibration command sent — "
                "ensure sensor has been in fresh air for >20 minutes"
            )
            return True
        except Exception as exc:
            logger.error("MH-Z19B calibration failed: %s", exc)
            return False

    # ── Diagnostic ────────────────────────────────────────────────────────────

    def selftest(self) -> bool:
        """
        Read and log one CO₂ reading for verification.
        Returns True if reading is valid (warm-up counts as OK).
        """
        reading = self.read()
        if reading.warming_up:
            logger.info("MH-Z19B selftest: sensor warming up")
            return True  # Expected state at startup — not a failure
        if not reading.ok:
            logger.error("MH-Z19B selftest FAILED: %s", reading.error)
            return False
        logger.info(
            "MH-Z19B selftest OK: CO₂=%.0f ppm  (internal temp=%.1f°C)",
            reading.co2_ppm, reading.temperature_c or 0.0,
        )
        return True
