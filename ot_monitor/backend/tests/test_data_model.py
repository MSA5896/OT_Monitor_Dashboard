"""
test_data_model.py – Pydantic schema validation tests.
"""
import pytest
from pydantic import ValidationError
from data_model import TelemetryPacket, OTData, DoorState


def test_valid_packet():
    pkt = TelemetryPacket(
        timestamp_iso="2026-03-16T08:00:00+05:30",
        ot_id="OT-01",
        data=OTData(temperature_c=22.0, relative_humidity_pct=50.0),
    )
    assert pkt.ot_id == "OT-01"
    assert pkt.data.temperature_c == 22.0


def test_invalid_timestamp():
    with pytest.raises(ValidationError):
        TelemetryPacket(timestamp_iso="not-a-date", ot_id="OT-01")


def test_out_of_range_temperature():
    with pytest.raises(ValidationError):
        OTData(temperature_c=99.0)   # > 60 °C limit


def test_out_of_range_humidity():
    with pytest.raises(ValidationError):
        OTData(relative_humidity_pct=150.0)


def test_none_values_allowed():
    """Sensor fields may be None (sensor offline)."""
    data = OTData(temperature_c=None, pm25_ugm3=None)
    assert data.temperature_c is None


def test_door_state_enum():
    data = OTData(door_state=DoorState.OPEN)
    assert data.door_state == DoorState.OPEN


def test_ext_namespace():
    data = OTData(ext={"bacteria_cfu_m3": 12.5, "camera_risk_score": 0.3})
    assert data.ext["bacteria_cfu_m3"] == 12.5
