"""
simulator.py – Standalone CLI simulator for the OT Monitor backend.
Publishes realistic OT telemetry to the backend's WebSocket endpoint
(or any WebSocket server accepting TelemetryPacket JSON).

Usage:
    python simulator.py                              # normal scenario
    python simulator.py --scenario pm_spike
    python simulator.py --scenario temp_drift --url ws://192.168.1.10:8000/ws
    python simulator.py --list-scenarios

Scenarios:
  normal       Steady safe-range values with realistic noise.
  temp_drift   Gradual temperature rise → WARNING → ALARM.
  pm_spike     Sudden PM2.5/PM10 spike (surgical smoke simulation).
  disconnect   Periodic 5-second drop-outs (tests reconnection in dashboard).
  sensor_fault Random sensor fields set to None (fault injection).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import os
import random
import signal
import sys
import time
from datetime import datetime, timezone, timedelta

import websockets
from pydantic import BaseModel

# Allow running without installing as package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from data_model import DoorState, OTData, TelemetryPacket, DeviceHealth, SensorHealth

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-7s  %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("simulator")

IST = timezone(timedelta(hours=5, minutes=30))

SCENARIOS = ["normal", "temp_drift", "pm_spike", "disconnect", "sensor_fault"]


# ─── Packet generator ─────────────────────────────────────────────────────────

def generate_packet(elapsed: float, scenario: str, seq: int, ot_id: str) -> TelemetryPacket:
    t = elapsed

    base_temp = 22.0; base_hum = 52.0
    base_pm1  = 6.0;  base_pm25 = 12.0; base_pm10 = 20.0

    temp  = base_temp + 0.5 * math.sin(t / 60) + random.gauss(0, 0.1)
    hum   = base_hum  + 2.0 * math.sin(t / 90 + 1) + random.gauss(0, 0.3)
    pm1   = base_pm1  + abs(random.gauss(0, 1.0))
    pm25  = base_pm25 + abs(random.gauss(0, 1.5))
    pm10  = base_pm10 + abs(random.gauss(0, 2.0))
    dp    = 8.0       + random.gauss(0, 0.3)
    door  = DoorState.CLOSED
    fault_temp = False; fault_pm = False

    if scenario == "temp_drift":
        temp += min(t / 30, 9.0)                           # +9 °C over 4.5 min → ALARM

    elif scenario == "pm_spike":
        if 30 <= t <= 65:
            factor = math.sin((t - 30) / 35 * math.pi)
            pm1   += 80  * factor
            pm25  += 130 * factor
            pm10  += 220 * factor
        elif 65 < t <= 130:
            decay  = 1 - (t - 65) / 65
            pm25  += max(0, 130 * decay)
            pm10  += max(0, 220 * decay)

    elif scenario == "sensor_fault":
        fault_temp = random.random() < 0.15
        fault_pm   = random.random() < 0.10

    health = DeviceHealth(
        temperature_sensor = SensorHealth(ok=not fault_temp,
                                          error_code="E_TIMEOUT" if fault_temp else None),
        pm_sensor          = SensorHealth(ok=not fault_pm,
                                          error_code="E_CRC" if fault_pm else None),
    )

    data = OTData(
        temperature_c          = None if fault_temp else round(max(15, min(40, temp)), 2),
        relative_humidity_pct  = round(max(10, min(95, hum)), 1),
        pm1_ugm3               = None if fault_pm else round(max(0, pm1), 2),
        pm25_ugm3              = None if fault_pm else round(max(0, pm25), 2),
        pm10_ugm3              = None if fault_pm else round(max(0, pm10), 2),
        diff_pressure_pa       = round(max(-5, dp), 2),
        door_state             = door,
        co2_ppm                = round(420 + 10 * math.sin(t / 120) + random.gauss(0, 5), 1),
        voc_ppb                = round(max(0, 50 + random.gauss(0, 10)), 1),
        occupancy_count        = random.choice([2, 3, 4, 4, 5]),
    )

    return TelemetryPacket(
        api_version    = "1.0",
        schema_version = "1.0",
        timestamp_iso  = datetime.now(IST).isoformat(),
        ot_id          = ot_id,
        sequence       = seq,
        data           = data,
        device_health  = health,
    )


# ─── Main send loop ───────────────────────────────────────────────────────────

async def run(url: str, scenario: str, ot_id: str, interval: float) -> None:
    elapsed = 0.0
    seq     = 0
    reconnect_delay = 2.0

    logger.info("OT Simulator  scenario=%-14s  target=%s", scenario, url)

    while True:
        try:
            async with websockets.connect(url, ping_interval=20) as ws:
                logger.info("Connected to %s", url)
                reconnect_delay = 2.0

                while True:
                    await asyncio.sleep(interval)
                    elapsed += interval
                    seq     += 1

                    if scenario == "disconnect" and int(elapsed) % 30 < 5:
                        # Simulate drop by closing connection
                        logger.info("Simulating disconnect …")
                        break

                    pkt  = generate_packet(elapsed, scenario, seq, ot_id)
                    json_str = pkt.model_dump_json()
                    await ws.send(json_str)

                    # Console preview every 5 s
                    if seq % 5 == 0:
                        d = pkt.data
                        temp_str = f"{d.temperature_c:.1f}°C" if d.temperature_c else "FAULT"
                        pm25_str = f"{d.pm25_ugm3:.1f}" if d.pm25_ugm3 else "FAULT"
                        logger.info(
                            "seq=%04d  T=%s  RH=%.0f%%  PM2.5=%s µg/m³  ΔP=%.1f Pa",
                            seq, temp_str,
                            d.relative_humidity_pct or 0,
                            pm25_str,
                            d.diff_pressure_pa or 0,
                        )

        except (OSError, websockets.exceptions.WebSocketException) as e:
            logger.warning("Disconnected (%s). Reconnect in %.1f s …", e, reconnect_delay)
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 60)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="OT Infection Monitor – Telemetry Simulator")
    parser.add_argument("--scenario",  default="normal",
                        choices=SCENARIOS, help="Simulation scenario")
    parser.add_argument("--url",       default="ws://localhost:8000/ws",
                        help="WebSocket URL of the backend")
    parser.add_argument("--ot-id",     default="OT-01", help="OT room identifier")
    parser.add_argument("--interval",  type=float, default=1.0,
                        help="Packet interval in seconds (default 1.0)")
    parser.add_argument("--list-scenarios", action="store_true",
                        help="List available scenarios and exit")
    args = parser.parse_args()

    if args.list_scenarios:
        print("Available scenarios:")
        descs = {
            "normal":       "Steady safe-range values with realistic noise",
            "temp_drift":   "Gradual temperature rise → WARNING → ALARM over ~4 min",
            "pm_spike":     "Surgical smoke PM2.5/PM10 spike at t=30s, recovery at t=65s",
            "disconnect":   "5-second connection drops every 30 s",
            "sensor_fault": "Random sensor fields set to None (15% temp, 10% PM)",
        }
        for s, d in descs.items():
            print(f"  {s:<16} {d}")
        return

    loop = asyncio.get_event_loop()

    def _stop(sig, frame):
        logger.info("Stopping simulator …")
        loop.stop()

    signal.signal(signal.SIGINT,  _stop)
    signal.signal(signal.SIGTERM, _stop)

    loop.run_until_complete(run(args.url, args.scenario, args.ot_id, args.interval))


if __name__ == "__main__":
    main()
