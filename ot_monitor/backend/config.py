"""
config.py – Loads and validates config/config.yaml.
All backend modules import from here; never read YAML directly.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml


# ─── Default config path ─────────────────────────────────────────────────────
_DEFAULT_CONFIG = Path(__file__).parent.parent / "config" / "config.yaml"
_USERS_FILE     = Path(__file__).parent / "data" / "users.json"


# ─── Threshold dataclasses ────────────────────────────────────────────────────

@dataclass
class ParameterThreshold:
    nominal:      Optional[float] = None
    warning_low:  Optional[float] = None
    warning_high: Optional[float] = None
    alarm_low:    Optional[float] = None
    alarm_high:   Optional[float] = None
    unit:         str = ""
    max_display:  Optional[float] = None  # for bar chart 100% ref


@dataclass
class ThresholdConfig:
    temperature_c:         ParameterThreshold = field(default_factory=ParameterThreshold)
    relative_humidity_pct: ParameterThreshold = field(default_factory=ParameterThreshold)
    pm1_ugm3:              ParameterThreshold = field(default_factory=ParameterThreshold)
    pm25_ugm3:             ParameterThreshold = field(default_factory=ParameterThreshold)
    pm10_ugm3:             ParameterThreshold = field(default_factory=ParameterThreshold)
    diff_pressure_pa:      ParameterThreshold = field(default_factory=ParameterThreshold)
    co2_ppm:               ParameterThreshold = field(default_factory=ParameterThreshold)
    voc_ppb:               ParameterThreshold = field(default_factory=ParameterThreshold)


@dataclass
class DataSourceConfig:
    type:                     str   = "simulator"
    ws_url:                   str   = "ws://localhost:8001/ws/telemetry"
    mqtt_broker:              str   = "localhost"
    mqtt_port:                int   = 1883
    mqtt_topic:               str   = "ot/OT-01/telemetry"
    mqtt_username:            str   = ""
    mqtt_password:            str   = ""
    serial_port:              str   = "/dev/ttyUSB0"
    serial_baud:              int   = 115200
    reconnect_initial_delay_s: float = 2.0
    reconnect_max_delay_s:    float = 60.0
    reconnect_multiplier:     float = 2.0


@dataclass
class AlarmEngineConfig:
    trigger_delay_s:           float = 5.0
    hysteresis_clear_s:        float = 10.0
    enable_combination_rules:  bool  = True
    pm_spike_delta_ugm3:       float = 20.0


@dataclass
class ServerConfig:
    host:                   str   = "0.0.0.0"
    port:                   int   = 8000
    ws_broadcast_interval_s: float = 1.0


@dataclass
class StorageConfig:
    db_path:             str = "./data/ot_monitor.db"
    retention_days:      int = 90
    prune_interval_hours: int = 6


@dataclass
class UserConfig:
    username: str = ""
    password: str = ""
    role:     str = "viewer"   # "admin" | "viewer"


@dataclass
class AuthConfig:
    users:                  list = field(default_factory=list)  # List[UserConfig]
    session_secret:         str  = "change-this-secret"
    session_expire_minutes: int  = 60
    enable_tls:             bool = False
    cert_path:              str  = ""
    key_path:               str  = ""


@dataclass
class CloudConfig:
    enabled:         bool  = False
    endpoint:        str   = ""
    api_key:         str   = ""
    sync_interval_s: float = 60.0


@dataclass
class AppConfig:
    ot_id:       str = "OT-01"
    ot_name:     str = "Operating Theatre 1"
    data_source: DataSourceConfig    = field(default_factory=DataSourceConfig)
    thresholds:  ThresholdConfig     = field(default_factory=ThresholdConfig)
    alarm_engine: AlarmEngineConfig  = field(default_factory=AlarmEngineConfig)
    server:      ServerConfig        = field(default_factory=ServerConfig)
    storage:     StorageConfig       = field(default_factory=StorageConfig)
    auth:        AuthConfig          = field(default_factory=AuthConfig)
    cloud:       CloudConfig         = field(default_factory=CloudConfig)


# ─── Loader ───────────────────────────────────────────────────────────────────

def _load_threshold(raw: dict) -> ParameterThreshold:
    return ParameterThreshold(**{k: v for k, v in raw.items() if k in ParameterThreshold.__dataclass_fields__})


def load_config(path: Path = _DEFAULT_CONFIG) -> AppConfig:
    env_override = os.environ.get("OT_CONFIG_PATH")
    if env_override:
        path = Path(env_override)
    with open(path, "r", encoding="utf-8") as f:
        raw: dict = yaml.safe_load(f)

    cfg = AppConfig()
    cfg.ot_id   = raw.get("ot_id", cfg.ot_id)
    cfg.ot_name = raw.get("ot_name", cfg.ot_name)

    # Data source
    ds = raw.get("data_source", {})
    cfg.data_source = DataSourceConfig(
        type=ds.get("type", "simulator"),
        ws_url=ds.get("ws_url", "ws://localhost:8001/ws/telemetry"),
        mqtt_broker=ds.get("mqtt_broker", "localhost"),
        mqtt_port=ds.get("mqtt_port", 1883),
        mqtt_topic=ds.get("mqtt_topic", "ot/OT-01/telemetry"),
        mqtt_username=ds.get("mqtt_username", ""),
        mqtt_password=ds.get("mqtt_password", ""),
        serial_port=ds.get("serial_port", "/dev/ttyUSB0"),
        serial_baud=ds.get("serial_baud", 115200),
        reconnect_initial_delay_s=ds.get("reconnect_initial_delay_s", 2.0),
        reconnect_max_delay_s=ds.get("reconnect_max_delay_s", 60.0),
        reconnect_multiplier=ds.get("reconnect_multiplier", 2.0),
    )

    # Thresholds
    th = raw.get("thresholds", {})
    cfg.thresholds = ThresholdConfig(
        temperature_c         = _load_threshold(th.get("temperature_c", {})),
        relative_humidity_pct = _load_threshold(th.get("relative_humidity_pct", {})),
        pm1_ugm3              = _load_threshold(th.get("pm1_ugm3", {})),
        pm25_ugm3             = _load_threshold(th.get("pm25_ugm3", {})),
        pm10_ugm3             = _load_threshold(th.get("pm10_ugm3", {})),
        diff_pressure_pa      = _load_threshold(th.get("diff_pressure_pa", {})),
        co2_ppm               = _load_threshold(th.get("co2_ppm", {})),
        voc_ppb               = _load_threshold(th.get("voc_ppb", {})),
    )

    # Alarm engine
    ae = raw.get("alarm_engine", {})
    cfg.alarm_engine = AlarmEngineConfig(
        trigger_delay_s=ae.get("trigger_delay_s", 5.0),
        hysteresis_clear_s=ae.get("hysteresis_clear_s", 10.0),
        enable_combination_rules=ae.get("enable_combination_rules", True),
        pm_spike_delta_ugm3=ae.get("pm_spike_delta_ugm3", 20.0),
    )

    # Server
    sv = raw.get("server", {})
    cfg.server = ServerConfig(
        host=sv.get("host", "0.0.0.0"),
        port=sv.get("port", 8000),
        ws_broadcast_interval_s=sv.get("ws_broadcast_interval_s", 1.0),
    )

    # Storage
    st = raw.get("storage", {})
    cfg.storage = StorageConfig(
        db_path=st.get("db_path", "./data/ot_monitor.db"),
        retention_days=st.get("retention_days", 90),
        prune_interval_hours=st.get("prune_interval_hours", 6),
    )

    # Auth
    au = raw.get("auth", {})
    raw_users = au.get("users", [])
    if raw_users:
        users = [
            UserConfig(
                username=u.get("username", ""),
                password=u.get("password", ""),
                role=u.get("role", "viewer"),
            )
            for u in raw_users
        ]
    else:
        # Legacy single-admin fallback
        users = [UserConfig(
            username=au.get("admin_username", "admin"),
            password=au.get("settings_password", "OTAdmin2024"),
            role="admin",
        )]
    # If users.json sidecar exists, it takes precedence (runtime additions/removals)
    file_users = _load_users_from_file()
    if file_users is not None:
        users = file_users

    cfg.auth = AuthConfig(
        users=users,
        session_secret=au.get("session_secret", "change-this-secret"),
        session_expire_minutes=int(au.get("session_expire_minutes", 60)),
        enable_tls=au.get("enable_tls", False),
        cert_path=au.get("cert_path", ""),
        key_path=au.get("key_path", ""),
    )

    # Cloud
    cl = raw.get("cloud", {})
    cfg.cloud = CloudConfig(
        enabled=cl.get("enabled", False),
        endpoint=cl.get("endpoint", ""),
        api_key=cl.get("api_key", ""),
        sync_interval_s=cl.get("sync_interval_s", 60.0),
    )

    return cfg


# ─── User persistence helpers ─────────────────────────────────────────────────

def save_users(users: list, path: Path = _USERS_FILE) -> None:
    """Persist user list to JSON sidecar so changes survive reload."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [{"username": u.username, "password": u.password, "role": u.role} for u in users]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _load_users_from_file(path: Path = _USERS_FILE) -> Optional[list]:
    """Return UserConfig list from JSON sidecar, or None if file absent."""
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        UserConfig(username=u["username"], password=u["password"], role=u.get("role", "viewer"))
        for u in raw
    ]


# ─── Singleton-style cached config ────────────────────────────────────────────
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config() -> AppConfig:
    global _config
    _config = load_config()
    return _config
