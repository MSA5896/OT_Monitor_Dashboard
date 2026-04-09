"""
test_alarm_engine.py – pytest unit tests for AlarmEngine.
Run: cd backend && pytest tests/ -v
"""
from __future__ import annotations

import asyncio
import pytest

from data_model import DoorState, OTData
from alarm_engine import AlarmEngine, AlarmLevel
from config import AppConfig, ThresholdConfig, ParameterThreshold, AlarmEngineConfig


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def make_config(trigger_delay=0.0, hysteresis=0.0):
    """Minimal config with zero timing delays for synchronous testing."""
    cfg = AppConfig()
    cfg.alarm_engine = AlarmEngineConfig(
        trigger_delay_s=trigger_delay,
        hysteresis_clear_s=hysteresis,
        enable_combination_rules=True,
        pm_spike_delta_ugm3=20.0,
    )
    cfg.thresholds = ThresholdConfig(
        temperature_c=ParameterThreshold(
            warning_low=20.0, warning_high=24.0,
            alarm_low=18.0,   alarm_high=25.0,
            unit="°C",
        ),
        relative_humidity_pct=ParameterThreshold(
            warning_low=40.0, warning_high=60.0,
            alarm_low=30.0,   alarm_high=70.0,
            unit="%",
        ),
        pm25_ugm3=ParameterThreshold(
            warning_high=35.0, alarm_high=50.0, unit="µg/m³"
        ),
        pm10_ugm3=ParameterThreshold(
            warning_high=75.0, alarm_high=100.0, unit="µg/m³"
        ),
        pm1_ugm3=ParameterThreshold(
            warning_high=30.0, alarm_high=50.0, unit="µg/m³"
        ),
        diff_pressure_pa=ParameterThreshold(
            warning_low=2.0, alarm_low=0.0, unit="Pa"
        ),
    )
    return cfg


def make_data(**kwargs) -> OTData:
    defaults = dict(
        temperature_c=22.0,
        relative_humidity_pct=52.0,
        pm1_ugm3=10.0,
        pm25_ugm3=12.0,
        pm10_ugm3=20.0,
        diff_pressure_pa=8.0,
        door_state=DoorState.CLOSED,
    )
    defaults.update(kwargs)
    return OTData(**defaults)


TS = "2026-03-16T08:00:00+05:30"


# ─── Tests: Normal operating range ────────────────────────────────────────────

def test_all_normal():
    engine = AlarmEngine(make_config())
    data   = make_data()
    states, status, combos = asyncio.get_event_loop().run_until_complete(
        engine.evaluate(data, "OT-01", TS)
    )
    assert states["temperature_c"].level    == AlarmLevel.NORMAL
    assert states["relative_humidity_pct"].level == AlarmLevel.NORMAL
    assert states["pm25_ugm3"].level        == AlarmLevel.NORMAL
    assert status.value == "SAFE"
    assert combos == []


# ─── Tests: Warning thresholds ────────────────────────────────────────────────

def test_temp_warning_high():
    engine = AlarmEngine(make_config())
    data   = make_data(temperature_c=24.5)   # > 24 warning_high
    states, status, _ = asyncio.get_event_loop().run_until_complete(
        engine.evaluate(data, "OT-01", TS)
    )
    assert states["temperature_c"].level == AlarmLevel.WARNING
    assert status.value == "WARNING"


def test_humidity_warning_low():
    engine = AlarmEngine(make_config())
    data   = make_data(relative_humidity_pct=38.0)  # < 40 warning_low
    states, status, _ = asyncio.get_event_loop().run_until_complete(
        engine.evaluate(data, "OT-01", TS)
    )
    assert states["relative_humidity_pct"].level == AlarmLevel.WARNING


# ─── Tests: Alarm thresholds ──────────────────────────────────────────────────

def test_temp_alarm_high():
    engine = AlarmEngine(make_config())
    data   = make_data(temperature_c=26.0)   # > 25 alarm_high
    states, status, _ = asyncio.get_event_loop().run_until_complete(
        engine.evaluate(data, "OT-01", TS)
    )
    assert states["temperature_c"].level == AlarmLevel.ALARM
    assert status.value == "ALERT"


def test_pm25_alarm():
    engine = AlarmEngine(make_config())
    data   = make_data(pm25_ugm3=60.0)  # > 50 alarm_high
    states, status, _ = asyncio.get_event_loop().run_until_complete(
        engine.evaluate(data, "OT-01", TS)
    )
    assert states["pm25_ugm3"].level == AlarmLevel.ALARM
    assert status.value == "ALERT"


# ─── Tests: Sensor fault (None value) ────────────────────────────────────────

def test_sensor_fault_none():
    engine = AlarmEngine(make_config())
    data   = make_data(temperature_c=None)
    states, status, _ = asyncio.get_event_loop().run_until_complete(
        engine.evaluate(data, "OT-01", TS)
    )
    assert states["temperature_c"].level == AlarmLevel.FAULT
    assert states["temperature_c"].value is None


# ─── Tests: Hysteresis – alarm should not clear immediately ───────────────────

def test_hysteresis_holds_alarm():
    """Even when value returns to normal, alarm holds until hysteresis elapses."""
    import time, unittest.mock
    # Set hysteresis = 10 s so it won't clear in the same call
    engine = AlarmEngine(make_config(trigger_delay=0.0, hysteresis=10.0))

    # First call – trigger alarm
    data_alarm = make_data(temperature_c=26.0)
    states, _, _ = asyncio.get_event_loop().run_until_complete(
        engine.evaluate(data_alarm, "OT-01", TS)
    )
    assert states["temperature_c"].level == AlarmLevel.ALARM

    # Second call – value recovers but hysteresis not elapsed
    data_ok = make_data(temperature_c=22.0)
    states2, status2, _ = asyncio.get_event_loop().run_until_complete(
        engine.evaluate(data_ok, "OT-01", TS)
    )
    # Should still be ALARM (hysteresis holding)
    assert states2["temperature_c"].level == AlarmLevel.ALARM


# ─── Tests: Combination rules ─────────────────────────────────────────────────

def test_combination_door_open_low_pressure():
    engine = AlarmEngine(make_config())
    data   = make_data(door_state=DoorState.OPEN, diff_pressure_pa=0.5)
    _, _, combos = asyncio.get_event_loop().run_until_complete(
        engine.evaluate(data, "OT-01", TS)
    )
    params = [e.parameter for e in combos]
    assert "combination.door_pressure" in params


def test_combination_pm_spike():
    engine = AlarmEngine(make_config())

    # First reading – baseline
    asyncio.get_event_loop().run_until_complete(
        engine.evaluate(make_data(pm25_ugm3=10.0), "OT-01", TS)
    )
    # Spike: +25 µg/m³ immediately
    _, _, combos = asyncio.get_event_loop().run_until_complete(
        engine.evaluate(make_data(pm25_ugm3=35.0), "OT-01", TS)
    )
    params = [e.parameter for e in combos]
    assert "combination.pm_spike" in params


# ─── Tests: Alarm callback fires ─────────────────────────────────────────────

def test_alarm_callback_fired():
    engine = AlarmEngine(make_config())
    fired_events = []

    async def capture(event):
        fired_events.append(event)

    engine.register_alarm_callback(capture)

    data = make_data(temperature_c=26.0)  # alarm
    asyncio.get_event_loop().run_until_complete(
        engine.evaluate(data, "OT-01", TS)
    )
    assert any(e.parameter == "temperature_c" for e in fired_events)
