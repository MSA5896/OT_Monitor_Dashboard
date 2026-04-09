"""
data_model.py – Pydantic v2 schema for OT telemetry.
This is the single contract between firmware/edge-controller and the dashboard.
Version this file; bump api_version in firmware when fields change.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator
import time


# ─── Enumerations ────────────────────────────────────────────────────────────

class DoorState(str, Enum):
    OPEN   = "OPEN"
    CLOSED = "CLOSED"
    AJAR   = "AJAR"
    UNKNOWN = "UNKNOWN"


class SystemStatus(str, Enum):
    SAFE    = "SAFE"
    WARNING = "WARNING"
    ALERT   = "ALERT"
    FAULT   = "FAULT"


class NetworkStatus(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    LOCAL_ONLY   = "LOCAL_ONLY"
    CLOUD_SYNCED = "CLOUD_SYNCED"


class AlarmLevel(str, Enum):
    NORMAL  = "NORMAL"
    WARNING = "WARNING"
    ALARM   = "ALARM"
    FAULT   = "FAULT"


# ─── Device Health ────────────────────────────────────────────────────────────

class SensorHealth(BaseModel):
    ok: bool = True
    error_code: Optional[str] = None
    last_calibration_iso: Optional[str] = None
    calibration_due: bool = False


class DeviceHealth(BaseModel):
    temperature_sensor: SensorHealth = Field(default_factory=SensorHealth)
    humidity_sensor:    SensorHealth = Field(default_factory=SensorHealth)
    pm_sensor:          SensorHealth = Field(default_factory=SensorHealth)
    pressure_sensor:    SensorHealth = Field(default_factory=SensorHealth)
    co2_sensor:         SensorHealth = Field(default_factory=SensorHealth)
    voc_sensor:         SensorHealth = Field(default_factory=SensorHealth)
    storage_ok:         bool = True
    storage_free_mb:    Optional[float] = None
    uptime_s:           Optional[float] = None


# ─── Core Data Payload ────────────────────────────────────────────────────────

class OTData(BaseModel):
    """All physical / logical signals from the OT sensors."""

    # Environmental
    temperature_c:          Optional[float] = Field(None, ge=-5, le=60,   description="Ambient temperature °C")
    relative_humidity_pct:  Optional[float] = Field(None, ge=0,  le=100,  description="Relative humidity %")

    # Particulate matter
    pm1_ugm3:               Optional[float] = Field(None, ge=0,  le=2000, description="PM1 µg/m³")
    pm25_ugm3:              Optional[float] = Field(None, ge=0,  le=2000, description="PM2.5 µg/m³")
    pm10_ugm3:              Optional[float] = Field(None, ge=0,  le=2000, description="PM10 µg/m³")

    # Optional sensors
    co2_ppm:                Optional[float] = Field(None, ge=0,  le=10000, description="CO₂ ppm")
    voc_ppb:                Optional[float] = Field(None, ge=0,  le=50000, description="VOC ppb")
    diff_pressure_pa:       Optional[float] = Field(None, ge=-50, le=200,  description="Differential pressure Pa")

    # State signals
    door_state:             DoorState = DoorState.UNKNOWN
    occupancy_count:        Optional[int] = Field(None, ge=0)

    # Extension namespace for future sensors
    ext: Dict[str, Any] = Field(default_factory=dict)


# ─── Top-Level Telemetry Packet ───────────────────────────────────────────────

class TelemetryPacket(BaseModel):
    """
    The canonical JSON envelope sent by edge controller / simulator
    and consumed by the dashboard backend.

    Example:
    {
        "api_version": "1.0",
        "schema_version": "1.0",
        "timestamp_iso": "2026-03-16T08:23:45+05:30",
        "ot_id": "OT-01",
        "data": { ... OTData fields ... },
        "device_health": { ... }
    }
    """
    api_version:    str = "1.0"
    schema_version: str = "1.0"
    timestamp_iso:  str = Field(..., description="ISO-8601 timestamp with tz offset")
    ot_id:          str = Field(..., description="Unique OT room identifier")
    sequence:       Optional[int] = None   # wrapping counter from firmware
    data:           OTData = Field(default_factory=OTData)
    device_health:  DeviceHealth = Field(default_factory=DeviceHealth)

    @field_validator("timestamp_iso")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        from datetime import datetime
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError(f"timestamp_iso must be ISO-8601, got: {v!r}")
        return v


# ─── Derived / Internal Models ────────────────────────────────────────────────

class ParameterAlarmState(BaseModel):
    parameter: str
    level:     AlarmLevel = AlarmLevel.NORMAL
    value:     Optional[float] = None
    message:   str = ""
    triggered_at: Optional[float] = None   # unix ts
    cleared_at:   Optional[float] = None


class AlarmEvent(BaseModel):
    """Persisted alarm event for the alarm log."""
    id:           Optional[int] = None
    ot_id:        str
    timestamp_iso: str
    parameter:    str
    level:        AlarmLevel
    value:        Optional[float]
    message:      str
    acknowledged: bool = False
    ack_by:       Optional[str] = None
    ack_at_iso:   Optional[str] = None
    duration_s:   Optional[float] = None   # filled on clear


class DashboardPayload(BaseModel):
    """
    The JSON pushed from Python backend → Flutter via WebSocket every second.
    Extends the raw telemetry with computed alarm states and system status.
    """
    timestamp_iso:  str
    ot_id:          str
    ot_name:        str = "Operating Theatre"
    data:           OTData
    device_health:  DeviceHealth
    system_status:  SystemStatus = SystemStatus.SAFE
    network_status: NetworkStatus = NetworkStatus.LOCAL_ONLY
    cloud_sync:     bool = False
    alarm_states:   Dict[str, ParameterAlarmState] = Field(default_factory=dict)
    active_alarms:  list[AlarmEvent] = Field(default_factory=list)
