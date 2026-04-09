# OT Infection Monitoring System

A complete real-time monitoring solution for Operating Theatre (OT) environments, designed to run natively on a Raspberry Pi / industrial panel PC as a standalone application — **not a web app**.

---

## 📁 Project Structure

```
ot_monitor/
├── backend/            ← Python FastAPI gateway + alarm engine + REST API
│   ├── main.py         ← Entry point (start this first)
│   ├── config.py       ← YAML config loader
│   ├── data_model.py   ← Pydantic v2 telemetry schema
│   ├── alarm_engine.py ← Rules engine (hysteresis, combination rules)
│   ├── storage.py      ← SQLite time-series + alarm log
│   ├── data_sources/   ← Pluggable: simulator | websocket | serial
│   ├── api/routes.py   ← REST: history, export CSV, alarms, settings
│   ├── tests/          ← pytest unit tests
│   └── requirements.txt
├── simulator/
│   └── simulator.py    ← Standalone CLI telemetry generator
├── config/
│   └── config.yaml     ← All thresholds & connection params (edit here)
└── dashboard/          ← Flutter desktop app
    └── lib/
        ├── main.dart
        ├── models/     ← Dart data models
        ├── services/   ← WebSocket service
        ├── providers/  ← DashboardProvider (state)
        ├── screens/    ← dashboard, alarms, history, settings
        ├── widgets/    ← header, kpi_card, trend_chart, pm_bar_chart, status_bar, alarm_banner
        └── theme/      ← Dark medical theme
```

---

## 🖥️ Display Recommendations

| Use Case | Model | Resolution |
|----------|-------|-----------|
| Testing (Budget) | Waveshare 7" HDMI LCD (B) | 1024×600 |
| Testing (Better) | Waveshare 10.1" HDMI IPS | 1280×800 |
| **Production** | Waveshare 15.6" FHD Touch | **1920×1080** |
| Production (Medical) | Mimo 15.6" Antimicrobial | 1920×1080 |

---

## ⚙️ Prerequisites

### Python 3.10+
```powershell
python --version
```

### Flutter SDK (desktop)
1. Install Flutter: https://docs.flutter.dev/get-started/install/windows
2. Enable Windows desktop:
   ```powershell
   flutter config --enable-windows-desktop
   ```
3. On Raspberry Pi (Linux), enable Linux desktop:
   ```bash
   flutter config --enable-linux-desktop
   ```
4. Verify:
   ```bash
   flutter doctor
   ```

> **Fonts**: The dashboard uses the Inter font. Either add the font files to `dashboard/assets/fonts/` or change `pubspec.yaml` to use a Google Fonts package instead.

---

## 🚀 Quick Start (Development Mode)

### 1. Install Python dependencies
```powershell
cd d:\Private\Development\ot_monitor\backend
pip install -r requirements.txt
```

### 2. Start the backend (with built-in simulator)
```powershell
python main.py
```
> The backend starts with `data_source.type: simulator` by default (see `config/config.yaml`).
> Backend runs at `http://localhost:8000`. WebSocket at `ws://localhost:8000/ws`.

### 3. Run the Flutter dashboard
```powershell
cd d:\Private\Development\ot_monitor\dashboard
flutter pub get
flutter run -d windows
```

### 4. (Optional) Run the standalone simulator
```powershell
cd d:\Private\Development\ot_monitor\simulator
python simulator.py --scenario pm_spike
```

---

## 🧪 Test Scenarios

```powershell
# Normal operating range
python simulator.py --scenario normal

# Temperature slowly rises → WARNING → ALARM
python simulator.py --scenario temp_drift

# PM2.5/PM10 spike (surgical smoke at t=30s)
python simulator.py --scenario pm_spike

# Simulated 5-second network dropouts every 30 s
python simulator.py --scenario disconnect

# Random sensor faults (null values injected)
python simulator.py --scenario sensor_fault

# List all scenarios
python simulator.py --list-scenarios
```

---

## 🧪 Backend Unit Tests
```powershell
cd d:\Private\Development\ot_monitor\backend
pytest tests/ -v
```
Tests cover: alarm engine transitions, hysteresis, combination rules (door+pressure, PM spike), Pydantic validation, fault injection.

---

## 🔌 Connecting Real Hardware

Edit `config/config.yaml`:

**Serial/USB (STM32/ESP32 via USB CDC):**
```yaml
data_source:
  type: serial
  serial_port: COM3        # or /dev/ttyUSB0 on Linux
  serial_baud: 115200
```
Then install pyserial:
```bash
pip install pyserial pyserial-asyncio
```

**WebSocket (MCU gateway):**
```yaml
data_source:
  type: websocket
  ws_url: "ws://192.168.1.100:8001/ws/telemetry"
```

**MQTT (e.g., Mosquitto broker):**
```yaml
data_source:
  type: mqtt
  mqtt_broker: "192.168.1.50"
  mqtt_port: 1883
  mqtt_topic: "ot/OT-01/telemetry"
```
Then install paho-mqtt:
```bash
pip install paho-mqtt
```

---

## 📡 JSON Telemetry Schema (v1.0)

The firmware/edge controller must publish newline-delimited JSON in this format:

```json
{
  "api_version": "1.0",
  "schema_version": "1.0",
  "timestamp_iso": "2026-03-16T08:23:45+05:30",
  "ot_id": "OT-01",
  "sequence": 1234,
  "data": {
    "temperature_c": 22.4,
    "relative_humidity_pct": 52.1,
    "pm1_ugm3": 8.2,
    "pm25_ugm3": 14.6,
    "pm10_ugm3": 22.3,
    "diff_pressure_pa": 7.8,
    "door_state": "CLOSED",
    "co2_ppm": 425.0,
    "voc_ppb": 48.0,
    "occupancy_count": 4,
    "ext": {}
  },
  "device_health": {
    "temperature_sensor": {"ok": true},
    "pm_sensor": {"ok": true},
    "storage_ok": true
  }
}
```

Set any field to `null` to indicate sensor offline — the dashboard shows `—` with fault badge.

---

## 📊 REST API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/health` | Device diagnostics |
| `GET`  | `/history?hours=1` | Time-series data |
| `GET`  | `/export/csv?hours=24` | CSV download for audits |
| `GET`  | `/alarms?limit=100` | Alarm log |
| `POST` | `/alarms/{id}/acknowledge` | Acknowledge alarm |
| `GET`  | `/settings/thresholds` | Read thresholds |
| `POST` | `/settings/thresholds` | Update thresholds (Basic Auth) |
| `POST` | `/settings/reload` | Reload config.yaml |

---

## ⚙️ Configuration

All settings in `config/config.yaml`:

- **`thresholds`** – Per-parameter `warning_low/high`, `alarm_low/high`
- **`alarm_engine`** – `trigger_delay_s` (avoid false alarms) + `hysteresis_clear_s` (avoid chattering)
- **`auth.settings_password`** – Admin password for settings screen (change before deployment!)
- **`storage.retention_days`** – How long to keep telemetry (default 90 days)
- **`cloud.enabled`** – Future remote sync toggle

---

## 🏥 Clinical Reference Thresholds (NABH / ASHRAE 170)

| Parameter | Nominal | Warning | Alarm |
|-----------|---------|---------|-------|
| Temperature | 21°C | 20–24°C | <18 or >25°C |
| Humidity | 50–55% | 40–60% | <30 or >70% |
| PM2.5 | <10 µg/m³ | >35 µg/m³ | >50 µg/m³ |
| PM10 | <20 µg/m³ | >75 µg/m³ | >100 µg/m³ |
| Diff Pressure | +8 Pa | <2 Pa | ≤0 Pa (loss of positive pressure) |

---

## 🔮 Future Extensions (Phase 2)

- MQTT data source (paho-mqtt)
- Camera-based analytics (occupancy, PPE compliance)
- BMS integration (send ACH increase commands)
- Fleet dashboard (multiple OTs)
- Cloud archival + compliance reports

---

## 📋 Compliance Notes

- All timestamps in ISO-8601 with timezone offset (IST: +05:30)
- Alarm events logged with timestamp, parameter, value, duration, acknowledgement — suitable for regulatory reporting
- CSV export for NABH audit documentation
- Admin actions (threshold changes) logged with `ack_by` field
