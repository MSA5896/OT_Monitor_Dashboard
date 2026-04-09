"""
app_state.py – Module-level singleton references for shared backend objects.
Route handlers and background tasks import from here instead of reaching
into request.app.state, which avoids the messy request-threading pattern.
"""
from __future__ import annotations
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from config import AppConfig
    from storage import Storage
    from alarm_engine import AlarmEngine
    from data_model import DashboardPayload

config:          Optional["AppConfig"]        = None
storage:         Optional["Storage"]          = None
alarm_engine:    Optional["AlarmEngine"]      = None
latest_payload:  Optional["DashboardPayload"] = None
