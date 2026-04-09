#!/usr/bin/env python3
"""
test_sensors.py — Standalone hardware sensor test script for Raspberry Pi.

Run this script DIRECTLY on the Raspberry Pi (not through the backend) to
verify that each sensor is wired correctly and returning valid data before
you switch the backend from simulator → hardware mode.

Usage:
    cd /path/to/ot_monitor/backend
    python sensors/test_sensors.py [--sensor all|bme280|pms5003|co2|sdp810]
                                   [--loop]
                                   [--interval 2]

Arguments:
    --sensor    Which sensor to test (default: all)
    --loop      Keep reading continuously until Ctrl+C (default: one-shot)
    --interval  Seconds between readings in loop mode (default: 2)

Examples:
    python sensors/test_sensors.py                        # test all sensors once
    python sensors/test_sensors.py --sensor co2           # test only CO₂
    python sensors/test_sensors.py --loop --interval 5    # live reading loop

Requirements on Raspberry Pi:
    pip install adafruit-circuitpython-bme280 adafruit-blinka pyserial smbus2

Prerequisite RPi setup:
    1. I2C enabled:  sudo raspi-config → Interfaces → I2C → Enable
    2. UART0 free:   sudo raspi-config → Interfaces → Serial → login=NO, hw=YES
    3. UART2 active: Add "dtoverlay=uart2" to /boot/config.txt, then reboot
    4. Verify:       i2cdetect -y 1    (should show 0x25=SDP810, 0x76=BME280)
                     ls /dev/serial0   (should exist for MH-Z19B)
                     ls /dev/ttyAMA1   (should exist for PMS5003)
"""

from __future__ import annotations

import argparse
import sys
import time
import logging

# ── Configure logging for console output ──────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test_sensors")

# ── ANSI colours for terminal output ─────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg: str) -> str:
    return f"{GREEN}✓  {msg}{RESET}"

def warn(msg: str) -> str:
    return f"{YELLOW}⚠  {msg}{RESET}"

def fail(msg: str) -> str:
    return f"{RED}✗  {msg}{RESET}"

def header(msg: str) -> str:
    return f"\n{BOLD}{'─'*60}\n  {msg}\n{'─'*60}{RESET}"


# ── Individual sensor test functions ─────────────────────────────────────────

def test_bme280(verbose: bool = True) -> bool:
    """Test BME280 Temperature, Humidity, Pressure on I2C 0x76."""
    if verbose:
        print(header("BME280 — Temperature / Humidity / Pressure (I2C 0x76)"))

    # Try both common I2C addresses
    for addr in [0x76, 0x77]:
        try:
            from sensors.bme280_driver import BME280Driver
            driver = BME280Driver(i2c_address=addr)
            driver.open()
            reading = driver.read()
            driver.close()

            if reading.ok:
                print(ok(f"I2C address 0x{addr:02X}  →  Found!"))
                print(ok(f"  Temperature : {reading.temperature_c:.2f} °C"))
                print(ok(f"  Humidity    : {reading.relative_humidity_pct:.1f} %RH"))
                print(ok(f"  Pressure    : {reading.pressure_hpa:.2f} hPa"))

                # Simple range check against OT requirements
                if not 10 <= reading.temperature_c <= 40:
                    print(warn(f"  Temperature {reading.temperature_c:.2f}°C is outside expected lab range 10–40°C"))
                if not 20 <= reading.relative_humidity_pct <= 85:
                    print(warn(f"  Humidity {reading.relative_humidity_pct:.1f}%RH is outside expected range 20–85%"))
                return True
            else:
                print(fail(f"  0x{addr:02X}: {reading.error}"))
        except Exception as exc:
            print(fail(f"  0x{addr:02X} open failed: {exc}"))

    print(fail("BME280 not found on any I2C address. Check wiring!"))
    return False


def test_pms5003(port: str = "/dev/ttyAMA1", verbose: bool = True) -> bool:
    """Test PMS5003 PM sensor on UART2 (/dev/ttyAMA1)."""
    if verbose:
        print(header(f"PMS5003 — PM1.0 / PM2.5 / PM10 (UART2 {port})"))

    try:
        from sensors.pms5003_driver import PMS5003Driver
        driver = PMS5003Driver(port=port, timeout_s=3.0)
        driver.open()

        print(f"  Waiting for first frame (up to 3 seconds)…")
        reading = driver.read()
        driver.close()

        if reading.ok:
            print(ok(f"  PM1.0  : {reading.pm1_ugm3:.1f} µg/m³"))
            print(ok(f"  PM2.5  : {reading.pm25_ugm3:.1f} µg/m³"))
            print(ok(f"  PM10   : {reading.pm10_ugm3:.1f} µg/m³"))
            print(ok(f"  Count > 0.3µm : {reading.count_03um} particles/0.1L"))

            # Threshold check (OT-grade per OT_System_Requirements_Detailed.md)
            if reading.pm25_ugm3 and reading.pm25_ugm3 > 25:
                print(warn(f"  PM2.5 {reading.pm25_ugm3:.1f} µg/m³ exceeds OT WARNING level (>25)"))
            return True
        else:
            print(fail(f"  Read error: {reading.error}"))
            print(fail(f"  Check: dtoverlay=uart2 in /boot/config.txt and reboot, then ls /dev/ttyAMA1"))
            return False
    except Exception as exc:
        print(fail(f"  PMS5003 failed: {exc}"))
        if "No such file or directory" in str(exc):
            print(warn("  Hint: Add 'dtoverlay=uart2' to /boot/config.txt and reboot"))
        return False


def test_mhz19(port: str = "/dev/serial0", verbose: bool = True) -> bool:
    """Test MH-Z19B CO₂ sensor on UART0 (/dev/serial0)."""
    if verbose:
        print(header(f"MH-Z19B — CO₂ Sensor (UART0 {port})"))

    try:
        from sensors.mhz19_driver import MHZ19Driver

        # Use a very short warmup for the test (skip actual 3-min wait)
        driver = MHZ19Driver(port=port, warmup_seconds=0, timeout_s=2.0)
        driver.open()

        print(f"  Skipping warm-up for test (will show warming_up=False)")
        reading = driver.read()
        driver.close()

        if reading.warming_up:
            print(warn("  Sensor reports warming up — this is normal at startup"))
            print(warn(f"  Wait 3 minutes after power-on for valid CO₂ readings"))
            return True  # Not a failure — expected at startup

        if reading.ok:
            print(ok(f"  CO₂ : {reading.co2_ppm:.0f} ppm"))
            print(ok(f"  Sensor internal temperature: {reading.temperature_c:.1f} °C"))

            # Threshold check
            if reading.co2_ppm and reading.co2_ppm > 1000:
                print(warn(f"  CO₂ {reading.co2_ppm:.0f} ppm exceeds WARNING level (>1000 ppm)"))
            elif reading.co2_ppm and reading.co2_ppm < 350:
                print(warn(f"  CO₂ {reading.co2_ppm:.0f} ppm is unusually low — sensor may need calibration"))
            return True
        else:
            print(fail(f"  Read error: {reading.error}"))
            print(warn("  Check: raspi-config → Serial → login shell=NO, hw=YES → Reboot"))
            print(warn(f"  Verify: ls /dev/serial0"))
            return False
    except Exception as exc:
        print(fail(f"  MH-Z19B failed: {exc}"))
        if "Permission denied" in str(exc):
            print(warn("  Hint: Add user to dialout group: sudo usermod -a -G dialout $USER"))
        return False


def test_sdp810(bus: int = 1, addr: int = 0x25, verbose: bool = True) -> bool:
    """Test SDP810 differential pressure sensor on I2C 0x25."""
    if verbose:
        print(header(f"SDP810 — Differential Pressure (I2C bus={bus}, addr=0x{addr:02X})"))

    # Try both possible addresses
    for test_addr in [0x25, 0x26]:
        try:
            from sensors.sdp810_driver import SDP810Driver
            driver = SDP810Driver(i2c_bus=bus, i2c_address=test_addr)
            driver.open()

            # Read twice — first read gives scale factor, second is "real"
            driver.read()
            reading = driver.read()
            driver.close()

            if reading.ok:
                print(ok(f"  I2C address 0x{test_addr:02X}  →  Found!"))
                print(ok(f"  Differential Pressure : {reading.diff_pressure_pa:.3f} Pa"))
                print(ok(f"  Sensor temperature    : {reading.temperature_c:.2f} °C"))

                # NABH OT threshold check
                dp = reading.diff_pressure_pa
                if dp and dp < 5:
                    print(warn(f"  DP {dp:.1f} Pa is below NABH minimum (8 Pa) — check HVAC!"))
                elif dp and dp > 20:
                    print(warn(f"  DP {dp:.1f} Pa exceeds warning threshold (20 Pa)"))
                elif dp and dp < 0:
                    print(fail(f"  Negative DP! Room is under NEGATIVE pressure — critical HVAC fault!"))
                return True
            else:
                print(fail(f"  0x{test_addr:02X}: {reading.error}"))
        except Exception as exc:
            print(fail(f"  0x{test_addr:02X} open failed: {exc}"))

    print(fail("SDP810 not found on any I2C address. Check wiring!"))
    print(warn("  Run: i2cdetect -y 1  to scan the I2C bus"))
    return False


# ── I2C Bus Scan ──────────────────────────────────────────────────────────────

def scan_i2c(bus: int = 1) -> None:
    """Scan I2C bus and print all detected addresses."""
    print(header(f"I2C Bus Scan (bus={bus})"))
    try:
        import smbus2
        b = smbus2.SMBus(bus)
        found = []
        for addr in range(0x03, 0x78):
            try:
                b.read_byte(addr)
                found.append(addr)
                print(ok(f"  Device at 0x{addr:02X}"), end="")
                if addr == 0x76:
                    print(f"  ← BME280 (SDO=GND)", end="")
                elif addr == 0x77:
                    print(f"  ← BME280 (SDO=3.3V)", end="")
                elif addr == 0x25:
                    print(f"  ← SDP810 (ADDR=GND)", end="")
                elif addr == 0x26:
                    print(f"  ← SDP810 (ADDR=VDD)", end="")
                print()
            except Exception:
                pass
        b.close()
        if not found:
            print(warn("  No I2C devices found! Check wiring and i2c enable."))
        else:
            print(ok(f"\n  Total {len(found)} device(s) found"))
    except Exception as exc:
        print(fail(f"  i2c scan failed: {exc}"))
        print(warn("  Is I2C enabled? Run: sudo raspi-config → Interfaces → I2C → Enable"))


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="OT Monitor — Raspberry Pi sensor hardware test"
    )
    parser.add_argument(
        "--sensor",
        choices=["all", "bme280", "pms5003", "co2", "sdp810", "i2c"],
        default="all",
        help="Which sensor to test (default: all)",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Keep reading continuously until Ctrl+C",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Seconds between readings in loop mode (default: 2)",
    )
    args = parser.parse_args()

    print(f"\n{BOLD}OT Environment Monitoring System — Sensor Hardware Test{RESET}")
    print(f"  Date/Time : {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"  Mode      : {'Loop (Ctrl+C to stop)' if args.loop else 'One-shot'}")
    print(f"  Sensor    : {args.sensor}")

    def run_once() -> dict:
        results = {}
        if args.sensor in ("all", "i2c"):
            scan_i2c()
        if args.sensor in ("all", "bme280"):
            results["bme280"] = test_bme280()
        if args.sensor in ("all", "pms5003"):
            results["pms5003"] = test_pms5003()
        if args.sensor in ("all", "co2"):
            results["co2"] = test_mhz19()
        if args.sensor in ("all", "sdp810"):
            results["sdp810"] = test_sdp810()
        return results

    if not args.loop:
        results = run_once()
        # Summary
        print(header("Test Summary"))
        all_ok = True
        for name, passed in results.items():
            if passed:
                print(ok(f"  {name.upper():<10} PASS"))
            else:
                print(fail(f"  {name.upper():<10} FAIL"))
                all_ok = False
        print()
        if all_ok:
            print(ok("All sensors passed! You can now switch config.yaml: data_source.type → hardware"))
        else:
            print(warn("One or more sensors failed. Fix wiring before switching to hardware mode."))
        sys.exit(0 if all_ok else 1)
    else:
        # Continuous loop
        try:
            iteration = 0
            while True:
                iteration += 1
                print(f"\n{BOLD}[Reading #{iteration}  {time.strftime('%H:%M:%S')}]{RESET}")
                run_once()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print(f"\n{YELLOW}Stopped by user.{RESET}")
            sys.exit(0)


if __name__ == "__main__":
    main()
