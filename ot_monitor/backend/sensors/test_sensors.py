#!/usr/bin/env python3
"""
test_sensors.py — Standalone hardware sensor test script for Raspberry Pi.

Run this script DIRECTLY on the Raspberry Pi (not through the backend) to
verify that each sensor is wired correctly and returning valid data before
you switch the backend from simulator → hardware mode.

Usage:
    cd /path/to/ot_monitor/backend
    python sensors/test_sensors.py [--sensor all|scd30|bme280|pms5003|i2c]
                                   [--loop]
                                   [--interval 2]

Arguments:
    --sensor    Which sensor to test (default: all)
    --loop      Keep reading continuously until Ctrl+C (default: one-shot)
    --interval  Seconds between readings in loop mode (default: 2)

Examples:
    python sensors/test_sensors.py                        # test all sensors once
    python sensors/test_sensors.py --sensor scd30         # test only SCD30
    python sensors/test_sensors.py --loop --interval 5    # live reading loop

Requirements on Raspberry Pi:
    pip install adafruit-circuitpython-scd30 adafruit-circuitpython-bme280 adafruit-blinka pyserial smbus2

Prerequisite RPi setup:
    1. I2C enabled:     sudo raspi-config → Interfaces → I2C → Enable
    2. I2C speed:       Add "dtparam=i2c_arm_baudrate=10000" to /boot/firmware/config.txt → reboot
    3. UART2 active:    Add "dtoverlay=uart2" to /boot/firmware/config.txt → reboot
    4. Verify I2C:      i2cdetect -y 1   (should show 0x61=SCD30, 0x76=BME280)
    5. Verify UART2:    ls /dev/ttyAMA1  (should exist for PMS5003)
"""

from __future__ import annotations

import argparse
import sys
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test_sensors")

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):   return f"{GREEN}✓  {msg}{RESET}"
def warn(msg): return f"{YELLOW}⚠  {msg}{RESET}"
def fail(msg): return f"{RED}✗  {msg}{RESET}"
def header(msg): return f"\n{BOLD}{'─'*60}\n  {msg}\n{'─'*60}{RESET}"


# ── SCD30 test ────────────────────────────────────────────────────────────────

def test_scd30(verbose: bool = True) -> bool:
    """Test SCD30 CO₂ + Temperature + Humidity on I2C 0x61."""
    if verbose:
        print(header("SCD30 — CO₂ / Temperature / Humidity (I2C 0x61)"))

    try:
        from sensors.scd30_driver import SCD30Driver
        driver = SCD30Driver(measurement_interval_s=2, temperature_offset_c=0.0)
        driver.open()

        print("  Waiting for first measurement (up to 15 seconds)…")
        # Override warmup to 0 for the test — we just want to see a reading
        driver._start_time = time.monotonic() - 15

        reading = driver.read()
        driver.close()

        if reading.warming_up:
            print(warn("  Sensor warming up — this is normal at first power-on"))
            print(warn("  Wait 10 seconds and try again"))
            return True

        if reading.ok:
            print(ok(f"  CO₂         : {reading.co2_ppm:.1f} ppm"))
            print(ok(f"  Temperature : {reading.temperature_c:.2f} °C"))
            print(ok(f"  Humidity    : {reading.relative_humidity_pct:.1f} %RH"))

            if reading.co2_ppm and reading.co2_ppm > 1000:
                print(warn(f"  CO₂ {reading.co2_ppm:.0f} ppm exceeds WARNING level (>1000 ppm)"))
            if reading.co2_ppm and reading.co2_ppm < 350:
                print(warn(f"  CO₂ {reading.co2_ppm:.0f} ppm unusually low — sensor may need calibration"))
            if reading.temperature_c and not 10 <= reading.temperature_c <= 40:
                print(warn(f"  Temperature {reading.temperature_c:.2f}°C outside expected range 10–40°C"))
            return True
        else:
            print(fail(f"  Read error: {reading.error}"))
            print(warn("  Check: i2cdetect -y 1  (should show 0x61)"))
            print(warn("  Check: dtparam=i2c_arm_baudrate=10000 in /boot/firmware/config.txt"))
            return False

    except Exception as exc:
        print(fail(f"  SCD30 failed: {exc}"))
        if "No such file" in str(exc) or "I2C" in str(exc):
            print(warn("  Hint: Enable I2C in raspi-config and slow bus: dtparam=i2c_arm_baudrate=10000"))
        return False


# ── BME280 test ───────────────────────────────────────────────────────────────

def test_bme280(verbose: bool = True) -> bool:
    """Test BME280 Barometric Pressure on I2C 0x76."""
    if verbose:
        print(header("BME280 — Barometric Pressure (I2C 0x76)"))

    for addr in [0x76, 0x77]:
        try:
            from sensors.bme280_driver import BME280Driver
            driver = BME280Driver(i2c_address=addr)
            driver.open()
            reading = driver.read()
            driver.close()

            if reading.ok:
                print(ok(f"  I2C address 0x{addr:02X}  →  Found!"))
                print(ok(f"  Pressure    : {reading.pressure_hpa:.2f} hPa"))
                print(ok(f"  Temperature : {reading.temperature_c:.2f} °C  (reference only)"))
                print(ok(f"  Humidity    : {reading.relative_humidity_pct:.1f} %RH  (reference only)"))

                if not 970 <= reading.pressure_hpa <= 1050:
                    print(warn(f"  Pressure {reading.pressure_hpa:.1f} hPa outside normal sea-level range (970–1050)"))
                return True
            else:
                print(fail(f"  0x{addr:02X}: {reading.error}"))
        except Exception as exc:
            print(fail(f"  0x{addr:02X} open failed: {exc}"))

    print(fail("BME280 not found on any I2C address. Check wiring!"))
    return False


# ── PMS5003 test ──────────────────────────────────────────────────────────────

def test_pms5003(port: str = "/dev/ttyAMA1", verbose: bool = True) -> bool:
    """Test PMS5003 PM sensor on UART2 (/dev/ttyAMA1)."""
    if verbose:
        print(header(f"PMS5003 — PM1.0 / PM2.5 / PM10 (UART2 {port})"))

    try:
        from sensors.pms5003_driver import PMS5003Driver
        driver = PMS5003Driver(port=port, timeout_s=3.0)
        driver.open()

        print("  Waiting for first frame (up to 3 seconds)…")
        reading = driver.read()
        driver.close()

        if reading.ok:
            print(ok(f"  PM1.0  : {reading.pm1_ugm3:.1f} µg/m³"))
            print(ok(f"  PM2.5  : {reading.pm25_ugm3:.1f} µg/m³"))
            print(ok(f"  PM10   : {reading.pm10_ugm3:.1f} µg/m³"))
            print(ok(f"  Count > 0.3µm : {reading.count_03um} particles/0.1L"))

            if reading.pm25_ugm3 and reading.pm25_ugm3 > 25:
                print(warn(f"  PM2.5 {reading.pm25_ugm3:.1f} µg/m³ exceeds OT WARNING level (>25)"))
            return True
        else:
            print(fail(f"  Read error: {reading.error}"))
            print(warn("  Check: dtoverlay=uart2 in /boot/firmware/config.txt and ls /dev/ttyAMA1"))
            return False
    except Exception as exc:
        print(fail(f"  PMS5003 failed: {exc}"))
        if "No such file or directory" in str(exc):
            print(warn("  Hint: Add 'dtoverlay=uart2' to /boot/firmware/config.txt and reboot"))
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
                label = {
                    0x61: "← SCD30 (CO₂/Temp/Humidity)",
                    0x76: "← BME280 (SDO=GND, Pressure)",
                    0x77: "← BME280 (SDO=3.3V, Pressure)",
                }.get(addr, "")
                print(ok(f"  Device at 0x{addr:02X}  {label}"))
            except Exception:
                pass
        b.close()
        if not found:
            print(warn("  No I2C devices found! Check wiring and I2C enable."))
        else:
            print(ok(f"\n  Total {len(found)} device(s) found"))
            if 0x61 not in found:
                print(warn("  SCD30 (0x61) not found — check SDA/SCL and SEL→GND"))
            if 0x76 not in found and 0x77 not in found:
                print(warn("  BME280 not found — check SDA/SCL and SDO wiring"))
    except Exception as exc:
        print(fail(f"  I2C scan failed: {exc}"))
        print(warn("  Is I2C enabled? Run: sudo raspi-config → Interfaces → I2C → Enable"))


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="OT Monitor — Raspberry Pi sensor hardware test"
    )
    parser.add_argument(
        "--sensor",
        choices=["all", "scd30", "bme280", "pms5003", "i2c"],
        default="all",
        help="Which sensor to test (default: all)",
    )
    parser.add_argument("--loop",     action="store_true", help="Keep reading continuously until Ctrl+C")
    parser.add_argument("--interval", type=float, default=2.0, help="Seconds between readings in loop mode")
    args = parser.parse_args()

    print(f"\n{BOLD}OT Environment Monitoring System — Sensor Hardware Test{RESET}")
    print(f"  Date/Time : {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"  Mode      : {'Loop (Ctrl+C to stop)' if args.loop else 'One-shot'}")
    print(f"  Sensor    : {args.sensor}")

    def run_once() -> dict:
        results = {}
        if args.sensor in ("all", "i2c"):
            scan_i2c()
        if args.sensor in ("all", "scd30"):
            results["scd30"] = test_scd30()
        if args.sensor in ("all", "bme280"):
            results["bme280"] = test_bme280()
        if args.sensor in ("all", "pms5003"):
            results["pms5003"] = test_pms5003()
        return results

    if not args.loop:
        results = run_once()
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
            print(ok("All sensors passed! Switch config.yaml → data_source.type: hardware"))
        else:
            print(warn("One or more sensors failed. Fix wiring before switching to hardware mode."))
        sys.exit(0 if all_ok else 1)
    else:
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
