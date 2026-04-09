"""
pms5003_driver.py — PM1.0 / PM2.5 / PM10 Particulate Matter sensor driver.

Hardware:  Plantower PMS5003 laser particle counter
Interface: UART2 (/dev/ttyAMA1 on RPi 4)
           Baud rate: 9600, 8N1, 3.3V TTL logic
Wiring (from OT_System_Requirements_Detailed.md):
  PMS5003 Pin 1 (VCC)   → RPi Pin 2 (5V)
  PMS5003 Pin 2 (GND)   → RPi Pin 9 (GND)
  PMS5003 Pin 3 (SET)   → RPi Pin 11 (GPIO17) — pull HIGH to enable
  PMS5003 Pin 4 (RX)    → RPi Pin 24 (GPIO8 / UART2 TX)
  PMS5003 Pin 5 (TX)    → RPi Pin 21 (GPIO9 / UART2 RX)
  PMS5003 Pin 6 (RESET) → RPi Pin 13 (GPIO27) — pull HIGH for normal

Enable UART2 on RPi:
  Add the following line to /boot/config.txt (or /boot/firmware/config.txt on RPi OS Bookworm):
    dtoverlay=uart2
  Then reboot. The port appears as /dev/ttyAMA1.

Library: pyserial (pip install pyserial)
         pms5003  (pip install pms5003)

Frame format: PMS5003 sends a fixed 32-byte frame every ~1 second.
  Byte 0-1: Start characters 0x42 0x4D ('BM')
  Byte 2-3: Frame length (28 bytes)
  Byte 4-5: PM1.0 CF=1 (µg/m³)
  Byte 6-7: PM2.5 CF=1 (µg/m³)
  Byte 8-9: PM10  CF=1 (µg/m³)
  Byte 10-11: PM1.0 atmospheric (µg/m³)  ← these are used for OT
  Byte 12-13: PM2.5 atmospheric (µg/m³)
  Byte 14-15: PM10  atmospheric (µg/m³)
  ...
  Byte 30-31: Checksum

  Atmospheric environment values are used for indoor air quality monitoring.
  CF=1 values are for factory calibration / standardized environments.
"""

from __future__ import annotations

import logging
import struct
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# PMS5003 protocol constants
_START_BYTE_1 = 0x42
_START_BYTE_2 = 0x4D
_FRAME_LENGTH = 32          # total bytes per frame
_DATA_START   = 4           # index where PM data starts
_CHECKSUM_IDX = 30          # checksum word starts at byte 30


@dataclass
class PMS5003Reading:
    pm1_ugm3:  Optional[float]   # PM1.0 atmospheric µg/m³
    pm25_ugm3: Optional[float]   # PM2.5 atmospheric µg/m³
    pm10_ugm3: Optional[float]   # PM10  atmospheric µg/m³
    # Raw particle counts (useful for diagnostics)
    count_03um: Optional[int]    # particles > 0.3 µm per 0.1L
    count_05um: Optional[int]
    count_10um: Optional[int]
    count_25um: Optional[int]
    count_50um: Optional[int]
    count_100um: Optional[int]
    ok: bool = True
    error: Optional[str] = None


class PMS5003Driver:
    """
    Software driver for PMS5003 particulate matter sensor.

    Uses pyserial directly (not pms5003 library) for full frame control,
    checksum validation, and error recovery.

    Parameters
    ----------
    port : str
        Serial port. RPi 4 default = '/dev/ttyAMA1' (UART2).
        Alternative: '/dev/ttyUSB0' if using a USB-UART adapter.
    timeout_s : float
        Read timeout in seconds. PMS5003 sends frames every ~1 second.
        2.0 s timeout gives one retry window.
    max_consecutive_errors : int
        Number of consecutive bad frames before the driver flags a fault.
    """

    def __init__(
        self,
        port: str = "/dev/ttyAMA1",
        timeout_s: float = 2.0,
        max_consecutive_errors: int = 5,
    ):
        self.port = port
        self.timeout_s = timeout_s
        self.max_consecutive_errors = max_consecutive_errors
        self._serial = None
        self._error_count = 0

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def open(self) -> None:
        """Open serial port to PMS5003."""
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
            # Flush any stale bytes from the buffer
            self._serial.reset_input_buffer()
            time.sleep(0.5)
            logger.info("PMS5003 opened on %s (9600 baud)", self.port)
        except Exception as exc:
            logger.error("PMS5003 open failed on %s: %s", self.port, exc)
            raise

    def close(self) -> None:
        """Close serial port."""
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._serial = None
        logger.info("PMS5003 closed")

    # ── Reading ────────────────────────────────────────────────────────────────

    def read(self) -> PMS5003Reading:
        """
        Read one complete 32-byte frame from PMS5003.

        Automatically re-synchronises if the buffer is misaligned.
        Returns PMS5003Reading with ok=False on any error.
        """
        if self._serial is None or not self._serial.is_open:
            return self._error_reading("Serial port not open — call open() first")

        try:
            frame = self._read_frame()
            if frame is None:
                return self._error_reading("Timeout: no frame received within timeout window")

            return self._parse_frame(frame)

        except Exception as exc:
            self._error_count += 1
            logger.warning("PMS5003 read error (%d): %s", self._error_count, exc)
            return self._error_reading(str(exc))

    def _read_frame(self) -> Optional[bytes]:
        """
        Synchronise to the start sequence (0x42 0x4D) then read 32 bytes.

        This handles cases where we come in mid-stream by scanning for the
        start bytes rather than blindly reading 32-byte blocks.
        """
        # Scan for start byte 0x42
        deadline = time.monotonic() + self.timeout_s
        while time.monotonic() < deadline:
            b = self._serial.read(1)
            if not b:
                continue
            if b[0] == _START_BYTE_1:
                # Check next byte for 0x4D
                b2 = self._serial.read(1)
                if b2 and b2[0] == _START_BYTE_2:
                    # We have the 2-byte start sequence — read remaining 30 bytes
                    rest = self._serial.read(_FRAME_LENGTH - 2)
                    if len(rest) == _FRAME_LENGTH - 2:
                        return bytes([_START_BYTE_1, _START_BYTE_2]) + rest
        return None  # timeout

    def _parse_frame(self, frame: bytes) -> PMS5003Reading:
        """
        Parse and validate a 32-byte PMS5003 frame.

        Frame layout (all values big-endian uint16):
          [0-1]   Start chars 0x42 0x4D
          [2-3]   Frame length = 28
          [4-5]   PM1.0 CF=1
          [6-7]   PM2.5 CF=1
          [8-9]   PM10  CF=1
          [10-11] PM1.0 atmospheric  ← used
          [12-13] PM2.5 atmospheric  ← used
          [14-15] PM10  atmospheric  ← used
          [16-17] Particles > 0.3µm per 0.1L
          [18-19] Particles > 0.5µm
          [20-21] Particles > 1.0µm
          [22-23] Particles > 2.5µm
          [24-25] Particles > 5.0µm
          [26-27] Particles > 10 µm
          [28-29] Reserved / version
          [30-31] Checksum (sum of bytes 0–29)
        """
        # Verify checksum: sum of bytes 0–29 must equal uint16 at bytes 30-31
        expected_checksum = sum(frame[:30])
        received_checksum = struct.unpack(">H", frame[30:32])[0]

        if expected_checksum != received_checksum:
            self._error_count += 1
            return self._error_reading(
                f"Checksum mismatch: expected {expected_checksum}, got {received_checksum}"
            )

        # Parse all 16-bit big-endian words
        words = struct.unpack(">HHHHHHHHHHHHHHHH", frame)
        # words[0] = 0x424D (start), words[1] = frame_len
        # PM CF=1: words[2], words[3], words[4]
        # PM atm:  words[5], words[6], words[7]  ← atmospheric = indoor use
        # Counts:  words[8]..words[13]

        pm1  = float(words[5])
        pm25 = float(words[6])
        pm10 = float(words[7])

        # Sanity range check (0 to 2000 µg/m³ per OTData model)
        if pm25 > 2000 or pm10 > 2000:
            return self._error_reading(f"PM values out of physical range: PM2.5={pm25}, PM10={pm10}")

        self._error_count = 0  # reset on good frame
        return PMS5003Reading(
            pm1_ugm3=pm1,
            pm25_ugm3=pm25,
            pm10_ugm3=pm10,
            count_03um=words[8],
            count_05um=words[9],
            count_10um=words[10],
            count_25um=words[11],
            count_50um=words[12],
            count_100um=words[13],
            ok=True,
        )

    @staticmethod
    def _error_reading(msg: str) -> PMS5003Reading:
        return PMS5003Reading(
            pm1_ugm3=None, pm25_ugm3=None, pm10_ugm3=None,
            count_03um=None, count_05um=None, count_10um=None,
            count_25um=None, count_50um=None, count_100um=None,
            ok=False, error=msg,
        )

    # ── Diagnostic ────────────────────────────────────────────────────────────

    def selftest(self) -> bool:
        """Read one frame and verify it is valid."""
        reading = self.read()
        if not reading.ok:
            logger.error("PMS5003 selftest FAILED: %s", reading.error)
            return False
        logger.info(
            "PMS5003 selftest OK: PM1=%.1f  PM2.5=%.1f  PM10=%.1f µg/m³",
            reading.pm1_ugm3, reading.pm25_ugm3, reading.pm10_ugm3,
        )
        return True

    @property
    def fault(self) -> bool:
        """True if consecutive error count exceeds fault threshold."""
        return self._error_count >= self.max_consecutive_errors
