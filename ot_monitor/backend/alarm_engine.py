"""
alarm_engine.py – Rules engine for OT parameter alarms.

Design:
- Stateless evaluator per call + stateful tracker dict for timing/hysteresis.
- Decoupled from UI and hardware: only depends on data_model and config.
- Thread-safe for asyncio (single event loop, no locks needed).
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from data_model import (
    AlarmEvent,
    AlarmLevel,
    OTData,
    ParameterAlarmState,
    SystemStatus,
)
from config import AppConfig, ParameterThreshold

logger = logging.getLogger(__name__)


# ─── Per-parameter runtime tracker ────────────────────────────────────────────

@dataclass
class _ParameterTracker:
    """Tracks timing state for a single parameter's threshold evaluation."""
    current_level:          AlarmLevel = AlarmLevel.NORMAL
    candidate_level:        AlarmLevel = AlarmLevel.NORMAL  # what it WANTS to be
    candidate_since:        Optional[float] = None          # unix ts candidate started
    clear_since:            Optional[float] = None          # unix ts back in safe zone
    last_value:             Optional[float] = None
    triggered_at:           Optional[float] = None
    alarm_event_open:       bool = False


# ─── Main alarm engine ────────────────────────────────────────────────────────

class AlarmEngine:
    """
    Evaluates each telemetry packet against configured thresholds.
    Applies:
      - Configurable trigger delay (avoids false alarms on transient spikes)
      - Hysteresis clearing (avoids chattering at boundary)
      - Combination rules (e.g. PM spike + occupancy, door open + low pressure)
    """

    def __init__(self, config: AppConfig):
        self.cfg = config
        self._trackers: Dict[str, _ParameterTracker] = {}
        self._pm25_history: List[Tuple[float, float]] = []  # (ts, value) for spike detection
        self._alarm_callbacks: List = []   # async callables → (AlarmEvent)

    def register_alarm_callback(self, callback) -> None:
        """Register an async callback(alarm_event: AlarmEvent) for new/cleared alarms."""
        self._alarm_callbacks.append(callback)

    async def _fire_alarm(self, event: AlarmEvent) -> None:
        for cb in self._alarm_callbacks:
            try:
                await cb(event)
            except Exception as e:
                logger.error("Alarm callback error: %s", e)

    def _tracker(self, param: str) -> _ParameterTracker:
        if param not in self._trackers:
            self._trackers[param] = _ParameterTracker()
        return self._trackers[param]

    # ── Core threshold check ──────────────────────────────────────────────────

    def _evaluate_level(self, value: float, th: ParameterThreshold) -> AlarmLevel:
        """Return the raw alarm level ignoring timing."""
        if th.alarm_low is not None and value <= th.alarm_low:
            return AlarmLevel.ALARM
        if th.alarm_high is not None and value >= th.alarm_high:
            return AlarmLevel.ALARM
        if th.warning_low is not None and value <= th.warning_low:
            return AlarmLevel.WARNING
        if th.warning_high is not None and value >= th.warning_high:
            return AlarmLevel.WARNING
        return AlarmLevel.NORMAL

    def _apply_timing(
        self,
        tracker: _ParameterTracker,
        raw_level: AlarmLevel,
        now: float,
    ) -> AlarmLevel:
        """Applies trigger delay and hysteresis to produce the confirmed level."""
        trigger_delay = self.cfg.alarm_engine.trigger_delay_s
        hysteresis    = self.cfg.alarm_engine.hysteresis_clear_s

        if raw_level != AlarmLevel.NORMAL:
            # Reset clear timer
            tracker.clear_since = None

            if raw_level != tracker.candidate_level:
                tracker.candidate_level = raw_level
                tracker.candidate_since = now

            # Promote to confirmed after trigger_delay
            if (now - (tracker.candidate_since or now)) >= trigger_delay:
                return raw_level
            else:
                # Still in candidate phase → keep current level
                return tracker.current_level
        else:
            # Value is back in safe range
            tracker.candidate_level = AlarmLevel.NORMAL
            tracker.candidate_since = None

            if tracker.current_level == AlarmLevel.NORMAL:
                return AlarmLevel.NORMAL

            # Start or check hysteresis timer
            if tracker.clear_since is None:
                tracker.clear_since = now

            if (now - tracker.clear_since) >= hysteresis:
                return AlarmLevel.NORMAL
            else:
                return tracker.current_level  # hold until hysteresis elapsed

    # ── Single-parameter evaluation ───────────────────────────────────────────

    async def _check_param(
        self,
        param: str,
        value: Optional[float],
        th: ParameterThreshold,
        ot_id: str,
        timestamp_iso: str,
        now: float,
    ) -> ParameterAlarmState:
        tracker = self._tracker(param)
        tracker.last_value = value

        if value is None:
            # Sensor missing / invalid
            state = ParameterAlarmState(
                parameter=param,
                level=AlarmLevel.FAULT,
                value=None,
                message=f"{param}: sensor data unavailable",
            )
            if tracker.current_level != AlarmLevel.FAULT:
                tracker.current_level = AlarmLevel.FAULT
                tracker.triggered_at  = now
                await self._fire_alarm(AlarmEvent(
                    ot_id=ot_id,
                    timestamp_iso=timestamp_iso,
                    parameter=param,
                    level=AlarmLevel.FAULT,
                    value=None,
                    message=state.message,
                ))
            return state

        raw_level      = self._evaluate_level(value, th)
        confirmed_level = self._apply_timing(tracker, raw_level, now)

        # Transition detected
        if confirmed_level != tracker.current_level:
            prev = tracker.current_level
            tracker.current_level = confirmed_level

            unit = th.unit or ""
            if confirmed_level != AlarmLevel.NORMAL:
                tracker.triggered_at      = now
                tracker.alarm_event_open  = True
                msg = f"{param.upper().replace('_', ' ')}: {confirmed_level.value} – {value:.1f} {unit}"
                await self._fire_alarm(AlarmEvent(
                    ot_id=ot_id,
                    timestamp_iso=timestamp_iso,
                    parameter=param,
                    level=confirmed_level,
                    value=value,
                    message=msg,
                ))
                logger.warning("ALARM: %s", msg)
            else:
                # Cleared
                duration = now - (tracker.triggered_at or now)
                tracker.alarm_event_open = False
                msg = f"{param.upper().replace('_', ' ')}: cleared"
                await self._fire_alarm(AlarmEvent(
                    ot_id=ot_id,
                    timestamp_iso=timestamp_iso,
                    parameter=param,
                    level=AlarmLevel.NORMAL,
                    value=value,
                    message=msg,
                    duration_s=duration,
                ))
                logger.info("CLEARED: %s", msg)
                tracker.triggered_at = None

        unit     = th.unit or ""
        msg_text = ""
        if confirmed_level != AlarmLevel.NORMAL:
            msg_text = f"{param.upper().replace('_',' ')}: {confirmed_level.value} – {value:.1f} {unit}"

        return ParameterAlarmState(
            parameter=param,
            level=confirmed_level,
            value=value,
            message=msg_text,
            triggered_at=tracker.triggered_at,
        )

    # ── Combination rules ─────────────────────────────────────────────────────

    async def _check_combination_rules(
        self,
        data: OTData,
        alarm_states: Dict[str, ParameterAlarmState],
        ot_id: str,
        timestamp_iso: str,
        now: float,
    ) -> List[AlarmEvent]:
        """Emit synthetic alarm events for compound conditions."""
        events: List[AlarmEvent] = []
        ae = self.cfg.alarm_engine

        # Rule 1: Door open + low differential pressure
        if (data.door_state.value == "OPEN" and
                data.diff_pressure_pa is not None and
                data.diff_pressure_pa < 2.0):
            events.append(AlarmEvent(
                ot_id=ot_id,
                timestamp_iso=timestamp_iso,
                parameter="combination.door_pressure",
                level=AlarmLevel.ALARM,
                value=data.diff_pressure_pa,
                message=f"CRITICAL: Door OPEN with low differential pressure ({data.diff_pressure_pa:.1f} Pa) – OT contamination risk!",
            ))

        # Rule 2: PM2.5 spike detection (rapid rise within 30 s)
        if data.pm25_ugm3 is not None:
            self._pm25_history.append((now, data.pm25_ugm3))
            cutoff = now - 30
            self._pm25_history = [(t, v) for t, v in self._pm25_history if t >= cutoff]
            if len(self._pm25_history) >= 2:
                oldest_val = self._pm25_history[0][1]
                delta = data.pm25_ugm3 - oldest_val
                if delta >= ae.pm_spike_delta_ugm3:
                    events.append(AlarmEvent(
                        ot_id=ot_id,
                        timestamp_iso=timestamp_iso,
                        parameter="combination.pm_spike",
                        level=AlarmLevel.WARNING,
                        value=delta,
                        message=f"PM2.5 SPIKE: +{delta:.1f} µg/m³ in 30 s – possible surgical smoke",
                    ))

        return events

    # ── Main evaluate entry point ──────────────────────────────────────────────

    async def evaluate(
        self,
        data: OTData,
        ot_id: str,
        timestamp_iso: str,
    ) -> Tuple[Dict[str, ParameterAlarmState], SystemStatus, List[AlarmEvent]]:
        """
        Evaluate a full OTData reading.
        Returns (alarm_states_dict, system_status, combination_events).
        """
        now = time.monotonic()
        th  = self.cfg.thresholds
        alarm_states: Dict[str, ParameterAlarmState] = {}

        checks = [
            ("temperature_c",         data.temperature_c,         th.temperature_c),
            ("relative_humidity_pct", data.relative_humidity_pct, th.relative_humidity_pct),
            ("pm1_ugm3",              data.pm1_ugm3,              th.pm1_ugm3),
            ("pm25_ugm3",             data.pm25_ugm3,             th.pm25_ugm3),
            ("pm10_ugm3",             data.pm10_ugm3,             th.pm10_ugm3),
            ("diff_pressure_pa",      data.diff_pressure_pa,      th.diff_pressure_pa),
            ("co2_ppm",               data.co2_ppm,               th.co2_ppm),
            ("voc_ppb",               data.voc_ppb,               th.voc_ppb),
        ]

        for param, value, threshold in checks:
            state = await self._check_param(param, value, threshold, ot_id, timestamp_iso, now)
            alarm_states[param] = state

        combo_events: List[AlarmEvent] = []
        if self.cfg.alarm_engine.enable_combination_rules:
            combo_events = await self._check_combination_rules(
                data, alarm_states, ot_id, timestamp_iso, now
            )

        # Derive global system status from worst alarm
        system_status = SystemStatus.SAFE
        for state in alarm_states.values():
            if state.level == AlarmLevel.FAULT or state.level == AlarmLevel.ALARM:
                system_status = SystemStatus.ALERT
                break
            elif state.level == AlarmLevel.WARNING:
                system_status = SystemStatus.WARNING

        if combo_events:
            worst_combo = max(
                combo_events,
                key=lambda e: {AlarmLevel.ALARM: 3, AlarmLevel.WARNING: 2,
                               AlarmLevel.NORMAL: 1, AlarmLevel.FAULT: 4}.get(e.level, 0)
            )
            if worst_combo.level == AlarmLevel.ALARM and system_status != SystemStatus.ALERT:
                system_status = SystemStatus.ALERT
            elif worst_combo.level == AlarmLevel.WARNING and system_status == SystemStatus.SAFE:
                system_status = SystemStatus.WARNING

        return alarm_states, system_status, combo_events
