# OT Infection Monitoring System
## Complete Hardware Installation & Setup Guide
### Raspberry Pi 4 + SCD30 + BME280 + PMS5003

---

## Table of Contents

1. [Hardware Bill of Materials](#1-hardware-bill-of-materials)
2. [GPIO & Wiring Reference](#2-gpio--wiring-reference)
3. [Raspberry Pi OS — Flash & First Boot](#3-raspberry-pi-os--flash--first-boot)
4. [Enable Interfaces (I2C, UART2, I2C Speed)](#4-enable-interfaces)
5. [Verify Hardware Connections](#5-verify-hardware-connections)
6. [Install Software Dependencies](#6-install-software-dependencies)
7. [Clone Repository & Python Environment](#7-clone-repository--python-environment)
8. [Test Each Sensor](#8-test-each-sensor)
9. [Configure for Hardware Mode](#9-configure-for-hardware-mode)
10. [Run & Verify the Backend](#10-run--verify-the-backend)
11. [Autostart on Boot (systemd)](#11-autostart-on-boot-systemd)
12. [Access Dashboard from Any Device](#12-access-dashboard-from-any-device)
13. [Display Setup (Optional)](#13-display-setup-optional)
14. [Sensor Maintenance & Calibration](#14-sensor-maintenance--calibration)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Hardware Bill of Materials

### Core

| # | Component | Specification | Notes |
|---|-----------|---------------|-------|
| 1 | **Raspberry Pi 4 Model B** | 2 GB RAM minimum (4 GB recommended) | Main compute unit |
| 1 | **MicroSD card** | 16 GB+ Class 10 / A1 rated | OS + SQLite database |
| 1 | **USB-C Power Supply** | 5V 3A (official RPi PSU) | Underpowering causes brown-outs |
| 1 | **Case with GPIO access** | Any standard RPi 4 case | Leave GPIO header accessible |

### Sensors

| # | Sensor | Interface | Measures | I²C Address |
|---|--------|-----------|----------|-------------|
| 1 | **Sensirion SCD30** | I²C @ 10 kHz | CO₂ (ppm), Temperature (°C), Humidity (%RH) | `0x61` (fixed) |
| 1 | **Bosch BME280** breakout | I²C @ 10 kHz | Barometric Pressure (hPa) | `0x76` (SDO→GND) |
| 1 | **Plantower PMS5003** | UART2 9600 baud | PM1.0, PM2.5, PM10 (µg/m³) | — |

### Accessories

| # | Item | Purpose |
|---|------|---------|
| 1 | Female-to-female jumper wires (20 cm) | Sensor connections |
| 1 | Small breadboard or terminal block | Tidy wiring / strain relief |
| 1 | HDMI monitor or Waveshare touchscreen | Dashboard display |
| 1 | USB keyboard + mouse | Initial setup only |

> **SCD30 note:** The Sensirion SCD30 breakout is available from Adafruit (#4867), Sparkfun (#SEN-15112), or Seedstudio. Ensure the breakout board exposes VCC, GND, SDA, SCL, and SEL pins.

---

## 2. GPIO & Wiring Reference

### RPi 4 GPIO Pinout (relevant pins only)

```
                    ┌────────────────────────┐
                    │   Raspberry Pi 4       │
  3.3V  ── Pin  1 ──┤ □ □ ├── Pin  2 ──  5V │
  SDA1  ── Pin  3 ──┤ □ □ ├── Pin  4 ──  5V │
  SCL1  ── Pin  5 ──┤ □ □ ├── Pin  6 ── GND │
GPIO17  ── Pin 11 ──┤ □ □ ├── Pin  9 ── GND │
UART0TX ── Pin  8 ──┤ □ □ ├── Pin 10 ── UART0RX │  (not used — no MH-Z19B)
GPIO27  ── Pin 13 ──┤ □ □ ├── Pin 14 ── GND │
UART2TX ── Pin 24 ──┤ □ □ ├── Pin 21 ── UART2RX │
                    └────────────────────────┘
```

---

### SCD30 → Raspberry Pi 4

| SCD30 Pin | RPi Pin | RPi Name | Note |
|-----------|---------|----------|------|
| VCC | Pin 1 | 3.3V | Do NOT connect to 5V |
| GND | Pin 6 | GND | |
| SDA | Pin 3 | GPIO2 / SDA1 | |
| SCL | Pin 5 | GPIO3 / SCL1 | |
| SEL | Pin 6 | GND | **Tie to GND** → selects I²C mode (not UART) |

> If your breakout has a `nRDY` pin, leave it unconnected.

---

### BME280 → Raspberry Pi 4

| BME280 Pin | RPi Pin | RPi Name | Note |
|------------|---------|----------|------|
| VCC / 3V3 | Pin 1 | 3.3V | |
| GND | Pin 6 | GND | |
| SDA | Pin 3 | GPIO2 / SDA1 | Shared with SCD30 |
| SCL | Pin 5 | GPIO3 / SCL1 | Shared with SCD30 |
| SDO / ADDR | Pin 6 | GND | **Tie to GND** → I²C address = `0x76` |
| CSB | Pin 1 | 3.3V | Tie HIGH for I²C mode |

> Both SCD30 and BME280 share the same I²C bus (SDA=Pin3, SCL=Pin5). This is normal — I²C is a multi-device bus.

---

### PMS5003 → Raspberry Pi 4

| PMS5003 Pin | Label | RPi Pin | RPi Name | Note |
|-------------|-------|---------|----------|------|
| 1 | VCC | Pin 2 | **5V** | PMS5003 requires 5V |
| 2 | GND | Pin 9 | GND | |
| 3 | SET | Pin 11 | GPIO17 | Pull HIGH = sensor enabled |
| 4 | RX | Pin 24 | GPIO8 / UART2 TX | Cross: sensor RX ← RPi TX |
| 5 | TX | Pin 21 | GPIO9 / UART2 RX | Cross: sensor TX → RPi RX |
| 6 | RESET | Pin 13 | GPIO27 | Pull HIGH = normal operation |

> **PMS5003 cable:** The sensor comes with a 1.27mm pitch ZH connector cable. Use a breakout adapter or carefully solder female jumper wires to the cable ends. Pin 1 is the side closest to the red wire.

---

### Wiring Summary Diagram

```
RPi 4                    Sensors
──────────────────────────────────────────────────────
Pin 1  (3.3V) ──────┬── SCD30 VCC
                    └── BME280 VCC / CSB (both to 3.3V)

Pin 2  (5V)   ─────── PMS5003 Pin 1 (VCC)

Pin 3  (SDA)  ──────┬── SCD30 SDA
                    └── BME280 SDA        [I²C shared bus]

Pin 5  (SCL)  ──────┬── SCD30 SCL
                    └── BME280 SCL        [I²C shared bus]

Pin 6  (GND)  ──────┬── SCD30 GND
                    ├── SCD30 SEL         (I²C mode select)
                    ├── BME280 GND
                    └── BME280 SDO        (address = 0x76)

Pin 9  (GND)  ─────── PMS5003 Pin 2 (GND)

Pin 11 (GPIO17) ──── PMS5003 Pin 3 (SET)  (HIGH = enabled)

Pin 13 (GPIO27) ──── PMS5003 Pin 6 (RESET) (HIGH = normal)

Pin 21 (GPIO9 / UART2 RX) ── PMS5003 Pin 5 (TX)
Pin 24 (GPIO8 / UART2 TX) ── PMS5003 Pin 4 (RX)
```

---

## 3. Raspberry Pi OS — Flash & First Boot

### 3.1 Flash the SD Card

1. Download **Raspberry Pi Imager**: https://www.raspberrypi.com/software/
2. Insert microSD card into your PC
3. Open Imager → Choose Device: **Raspberry Pi 4**
4. Choose OS: **Raspberry Pi OS Lite (64-bit)** — Bookworm (no desktop, saves RAM)
5. Click the **gear icon (⚙)** before writing to pre-configure:
   - Hostname: `ot-monitor`
   - Username: `pi` / Password: `(set a strong password)`
   - Enable SSH: checked
   - WiFi SSID + password (if using WiFi)
   - Locale / timezone: `Asia/Kolkata`
6. Click **Write** and wait for verification

### 3.2 First Boot

Insert the SD card into the RPi and power on. Wait ~90 seconds for first boot.

**SSH in from Windows:**
```powershell
ssh pi@ot-monitor.local
```
If `.local` does not resolve, find the IP from your router's DHCP table or use:
```powershell
ping ot-monitor.local
```

### 3.3 Update the System

```bash
sudo apt update && sudo apt full-upgrade -y
sudo reboot
```

---

## 4. Enable Interfaces

SSH back in after reboot, then run:

```bash
sudo raspi-config
```

### 4.1 Enable I²C

```
Interface Options → I2C → Enable → OK
```

### 4.2 Enable UART2 for PMS5003 and Slow I²C for SCD30

These require editing the boot config file directly:

```bash
sudo nano /boot/firmware/config.txt
```

> On older RPi OS (Bullseye or earlier) the path is `/boot/config.txt`

Scroll to the bottom and add these lines:

```ini
# Slow I2C bus to 10kHz for SCD30 clock-stretching compatibility
dtparam=i2c_arm_baudrate=10000

# Enable UART2 on GPIO8/GPIO9 for PMS5003
dtoverlay=uart2
```

Save (`Ctrl+O`, `Enter`, `Ctrl+X`) and reboot:

```bash
sudo reboot
```

### 4.3 Verify Interfaces After Reboot

```bash
# I2C tools
sudo apt install -y i2c-tools

# Scan I2C bus — should show 0x61 (SCD30) and 0x76 (BME280)
i2cdetect -y 1

# UART2 for PMS5003
ls /dev/ttyAMA1
```

**Expected `i2cdetect` output:**
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:                         -- -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- 61 -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- 76 --
```

| Address | Sensor |
|---------|--------|
| `0x61` | SCD30 — CO₂, Temperature, Humidity |
| `0x76` | BME280 — Barometric Pressure |

---

## 5. Verify Hardware Connections

Before installing software, sanity-check the wiring with a quick voltage test:

```bash
# Check 3.3V rail is alive (with voltmeter on Pin 1 vs Pin 6)
# Expected: 3.28–3.35V

# Check 5V rail (Pin 2 vs Pin 9)
# Expected: 4.9–5.1V

# If i2cdetect shows nothing:
# 1. Power off RPi completely
# 2. Re-check all SDA/SCL connections (easy to swap Pin 3 and Pin 5)
# 3. Confirm SCD30 SEL pin is tied to GND
# 4. Re-run i2cdetect -y 1
```

---

## 6. Install Software Dependencies

```bash
# System packages
sudo apt install -y python3-pip python3-venv git i2c-tools

# Add pi user to dialout (UART) and i2c groups — required for sensor access without sudo
sudo usermod -a -G dialout,i2c pi

# Apply group changes in current session (or just reboot)
newgrp dialout
```

---

## 7. Clone Repository & Python Environment

```bash
# Clone the repository
cd ~
git clone https://github.com/MSA5896/Project.git ot_monitor
cd ot_monitor/ot_monitor/backend

# Create isolated virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python backend dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install Raspberry Pi hardware sensor libraries
pip install \
    adafruit-blinka \
    adafruit-circuitpython-scd30 \
    adafruit-circuitpython-bme280 \
    pyserial \
    smbus2
```

> The hardware libraries (`adafruit-blinka`, etc.) must be installed **on the RPi only**. Do not install them on your development machine — they will fail.

---

## 8. Test Each Sensor

Run the built-in sensor test script to verify every sensor before switching to live mode. This script opens each sensor, reads one value, and prints a pass/fail summary.

```bash
cd ~/ot_monitor/ot_monitor/backend
source venv/bin/activate

# Test all three sensors at once
python sensors/test_sensors.py

# Test individual sensors
python sensors/test_sensors.py --sensor scd30
python sensors/test_sensors.py --sensor bme280
python sensors/test_sensors.py --sensor pms5003

# I2C bus scan only
python sensors/test_sensors.py --sensor i2c

# Continuous live readings — watch values update (Ctrl+C to stop)
python sensors/test_sensors.py --loop --interval 2
```

### Expected Output (all pass)

```
OT Environment Monitoring System — Sensor Hardware Test
  Date/Time : 2026-06-18 12:00:00 IST
  Mode      : One-shot
  Sensor    : all

────────────────────────────────────────────────────────────
  I2C Bus Scan (bus=1)
────────────────────────────────────────────────────────────
✓  Device at 0x61  ← SCD30 (CO₂/Temp/Humidity)
✓  Device at 0x76  ← BME280 (SDO=GND, Pressure)
✓  Total 2 device(s) found

────────────────────────────────────────────────────────────
  SCD30 — CO₂ / Temperature / Humidity (I2C 0x61)
────────────────────────────────────────────────────────────
✓  CO₂         : 423.5 ppm
✓  Temperature : 22.41 °C
✓  Humidity    : 53.7 %RH

────────────────────────────────────────────────────────────
  BME280 — Barometric Pressure (I2C 0x76)
────────────────────────────────────────────────────────────
✓  I2C address 0x76  →  Found!
✓  Pressure    : 1012.84 hPa
✓  Temperature : 23.10 °C  (reference only)
✓  Humidity    : 51.2 %RH  (reference only)

────────────────────────────────────────────────────────────
  PMS5003 — PM1.0 / PM2.5 / PM10 (UART2 /dev/ttyAMA1)
────────────────────────────────────────────────────────────
✓  PM1.0  : 3.0 µg/m³
✓  PM2.5  : 5.1 µg/m³
✓  PM10   : 6.4 µg/m³
✓  Count > 0.3µm : 621 particles/0.1L

────────────────────────────────────────────────────────────
  Test Summary
────────────────────────────────────────────────────────────
✓  SCD30      PASS
✓  BME280     PASS
✓  PMS5003    PASS

✓  All sensors passed! Switch config.yaml → data_source.type: hardware
```

**Do not proceed to step 9 until all three sensors show PASS.**

---

## 9. Configure for Hardware Mode

Open the configuration file:

```bash
nano ~/ot_monitor/ot_monitor/config/config.yaml
```

### 9.1 Switch Data Source

Find the `data_source` section and change `type`:

```yaml
data_source:
  type: hardware        # ← change from: simulator
```

### 9.2 Listen on All Network Interfaces

So you can access the dashboard from any device on the same network:

```yaml
server:
  host: "0.0.0.0"      # ← change from: 127.0.0.1
  port: 8001
```

### 9.3 Change the Session Secret (Important)

```yaml
auth:
  session_secret: "replace-with-a-long-random-string-here"
```

Generate a strong secret:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 9.4 Review Hardware Source Settings (optional)

The defaults work out of the box. Adjust only if needed:

```yaml
hardware_source:
  scd30_measurement_interval_s: 2     # polling cadence (2 s is ideal for OT)
  scd30_temperature_offset_c: 0.0     # increase if sensor reads high (e.g. 2.0)
  bme280_i2c_address: 0x76            # change to 0x77 if SDO is tied to 3.3V
  pms_port: "/dev/ttyAMA1"
  poll_interval_s: 2.0
```

**Temperature offset calibration:** Place a reference thermometer next to the SCD30. If the SCD30 reads 2°C higher than the reference (due to PCB self-heating), set `scd30_temperature_offset_c: 2.0`.

### 9.5 Change Default Passwords

Edit the users section:

```yaml
auth:
  users:
    - username: "admin"
      password: "YourNewAdminPassword"
      role: "admin"
    - username: "nurse"
      password: "YourNewNursePassword"
      role: "viewer"
```

Or add/remove users at runtime from the **Settings → User Management** panel in the dashboard.

---

## 10. Run & Verify the Backend

### 10.1 Manual Start (for testing)

```bash
cd ~/ot_monitor/ot_monitor/backend
source venv/bin/activate
python main.py
```

You should see:

```
12:00:01  INFO     SCD30 ready — CO₂, Temperature, Humidity
12:00:01  INFO     BME280 ready — Barometric Pressure
12:00:01  INFO     PMS5003 ready — PM1.0 / PM2.5 / PM10
12:00:01  INFO     HardwareSource started — 3 sensors (SCD30 + BME280 + PMS5003), polling every 2.0 s
12:00:01  INFO     OT Monitor backend started  ✓  (ot_id=OT-01, source=hardware)
```

### 10.2 Open the Dashboard

From any browser on the same network:

```
http://ot-monitor.local:8001/
```

Or using the RPi's IP address:

```
http://192.168.x.x:8001/
```

Login: `admin` / `OTAdmin2024` (or your changed password)

### 10.3 Verify Live Data

After login:
- **Monitor panel**: KPI cards should show real sensor values (not simulated)
- **CO₂ card**: will show "Warming Up…" for the first ~10 seconds after start, then a real ppm value
- **Alarms panel**: live threshold violations from the real environment
- **History panel**: real telemetry rows populating every 2 seconds

---

## 11. Autostart on Boot (systemd)

This makes the backend start automatically when the RPi powers on — no login required.

### 11.1 Create the Service File

```bash
sudo nano /etc/systemd/system/ot-monitor.service
```

Paste the following exactly:

```ini
[Unit]
Description=OT Infection Monitor Backend
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ot_monitor/ot_monitor/backend
ExecStart=/home/pi/ot_monitor/ot_monitor/backend/venv/bin/python main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

### 11.2 Enable and Start

```bash
sudo systemctl daemon-reload
sudo systemctl enable ot-monitor
sudo systemctl start ot-monitor
```

### 11.3 Verify It Is Running

```bash
sudo systemctl status ot-monitor
```

Expected:
```
● ot-monitor.service — OT Infection Monitor Backend
     Loaded: loaded (/etc/systemd/system/ot-monitor.service; enabled)
     Active: active (running) since ...
```

### 11.4 Useful Commands

```bash
# View live logs
sudo journalctl -u ot-monitor -f

# View last 100 lines
sudo journalctl -u ot-monitor -n 100

# Restart after config change
sudo systemctl restart ot-monitor

# Stop the service
sudo systemctl stop ot-monitor

# Disable autostart
sudo systemctl disable ot-monitor
```

---

## 12. Access Dashboard from Any Device

### 12.1 Find the RPi's IP Address

```bash
# On the RPi
hostname -I
```

Or from Windows:
```powershell
ping ot-monitor.local
# The IP is shown in the reply
```

### 12.2 Set a Static IP (Recommended for Production)

Prevents the IP from changing after a router restart:

```bash
sudo nano /etc/dhcpcd.conf
```

Add at the bottom (replace with your network details):

```
interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1 8.8.8.8
```

Restart networking:
```bash
sudo systemctl restart dhcpcd
```

Dashboard will now always be at:
```
http://192.168.1.100:8001/
```

### 12.3 Open Firewall Port (if needed)

RPi OS Lite has no firewall by default. If you added `ufw`:

```bash
sudo ufw allow 8001/tcp
```

---

## 13. Display Setup (Optional)

For a wall-mounted or bedside dashboard screen connected directly to the RPi.

### 13.1 Recommended Displays

| Model | Size | Resolution | Notes |
|-------|------|------------|-------|
| Waveshare 7" HDMI (B) | 7" | 1024×600 | Budget, good for testing |
| Waveshare 10.1" IPS | 10.1" | 1280×800 | Better visibility |
| **Waveshare 15.6" FHD Touch** | **15.6"** | **1920×1080** | **Recommended for OT** |
| Mimo 15.6" Antimicrobial | 15.6" | 1920×1080 | Medical-grade enclosure |

### 13.2 Auto-Launch Browser on Boot (Kiosk Mode)

Install a minimal desktop with Chromium:

```bash
sudo apt install -y --no-install-recommends xorg openbox chromium-browser unclutter
```

Create an autostart file:

```bash
mkdir -p ~/.config/openbox
nano ~/.config/openbox/autostart
```

Paste:

```bash
# Hide mouse cursor after 2 seconds of inactivity
unclutter -idle 2 &

# Launch Chromium in kiosk mode pointing to the local dashboard
chromium-browser \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --no-first-run \
    --start-fullscreen \
    "http://localhost:8001/" &
```

Enable auto-login and X session:

```bash
sudo raspi-config
# System Options → Boot / Auto Login → Desktop Autologin
```

Reboot — Chromium will open the dashboard full screen automatically.

---

## 14. Sensor Maintenance & Calibration

### SCD30 — CO₂ Sensor

**Automatic Self-Calibration (ASC):**
The SCD30 performs background ASC over 7+ continuous days of operation. It assumes the sensor sees fresh outdoor air (~420 ppm) at least once per day. This is typical for hospital corridors but may not be true in a sealed OT. If ASC is not appropriate for your installation, disable it:

```python
# Run once on the RPi from Python REPL
from sensors.scd30_driver import SCD30Driver
d = SCD30Driver(); d.open()
d._sensor.self_calibration_enabled = False
d.close()
```

**Forced Recalibration (FRC) — annual or when readings seem off:**
1. Place the SCD30 sensor in a room with fresh outdoor air (open window) for 5+ minutes
2. Run:

```bash
cd ~/ot_monitor/ot_monitor/backend
source venv/bin/activate
python3 - <<'EOF'
from sensors.scd30_driver import SCD30Driver
import time
d = SCD30Driver(); d.open()
time.sleep(15)   # wait for first reading
d.set_forced_recalibration(420)  # outdoor fresh air = ~420 ppm
print("FRC command sent at 420 ppm reference")
d.close()
EOF
```

**Temperature offset adjustment:**
If the SCD30 reads higher than a reference thermometer (common if enclosed):

```bash
nano ~/ot_monitor/ot_monitor/config/config.yaml
# Change: scd30_temperature_offset_c: 2.0  (adjust to match your measurement)
sudo systemctl restart ot-monitor
```

---

### BME280 — Pressure Sensor

No calibration required. The BME280 is factory-calibrated and stable over its lifetime. Verify the reading is within ±5 hPa of a reference barometer.

---

### PMS5003 — Particulate Matter Sensor

**Laser lifetime:** ~8,000 hours (≈3.3 years at 24/7 operation). Replace when PM readings become erratic or consistently zero despite visible particulates.

**Cleaning:** Do not blow air into the sensor inlet. Occasional light dusting of the intake grill is sufficient.

**Verification:** In a clean OT with HEPA-filtered air at rest, PM2.5 should read below 5 µg/m³. If it consistently reads 0 or >50 in a clean room, the sensor may be faulty.

---

## 15. Troubleshooting

### Sensor Issues

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `i2cdetect` shows nothing | I²C not enabled | `sudo raspi-config` → Interfaces → I²C → Enable → Reboot |
| Only one device at 0x61 | BME280 not detected | Check SDO tied to GND; check SDA/SCL shared correctly |
| Only one device at 0x76 | SCD30 not detected | Check SEL pin tied to GND on SCD30 |
| SCD30 `data_available` timeout | I²C too fast for clock stretching | Add `dtparam=i2c_arm_baudrate=10000` to `/boot/firmware/config.txt` → Reboot |
| SCD30 CO₂ stuck at 400 ppm | Sensor just powered on | Normal — ASC needs ~1 week to stabilise in a new environment |
| SCD30 CRC errors | I²C speed too high | Confirm `i2c_arm_baudrate=10000` is set |
| `/dev/ttyAMA1` not found | UART2 overlay missing | Add `dtoverlay=uart2` to `/boot/firmware/config.txt` → Reboot |
| PMS5003 checksum errors | Loose RX/TX wire | Power off; re-seat the PMS5003 cable; confirm TX→RX cross |
| `Permission denied` on `/dev/ttyAMA1` | User not in `dialout` group | `sudo usermod -a -G dialout pi` → logout and login |

---

### Backend Issues

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Dashboard shows "Backend offline" | Backend not running | `sudo systemctl status ot-monitor` → check logs |
| Dashboard unreachable from network | `host` is `127.0.0.1` | Change `server.host: "0.0.0.0"` in `config.yaml` → restart |
| "Authentication required" on every page | Cookie not set | Access via `http://` not `file://`; ensure same-origin |
| CO₂ shows "Warming Up…" | First 10 seconds after start | Normal — wait for SCD30 to initialise |
| Alarms panel empty | No threshold violations yet | Check thresholds in Settings; normal if environment is clean |
| High CO₂ alarms constantly | SCD30 needs calibration | Run FRC procedure (Section 14) |
| Logs show sensor errors after hours | I²C bus locking up | Power cycle RPi; add 100nF decoupling capacitors to SDA/SCL lines |

---

### Quick Diagnostics Command

Run this anytime to check the full system health:

```bash
# Backend service status
sudo systemctl status ot-monitor

# Last 30 log lines
sudo journalctl -u ot-monitor -n 30 --no-pager

# I2C scan
i2cdetect -y 1

# UART port
ls -la /dev/ttyAMA1

# Sensor quick test
cd ~/ot_monitor/ot_monitor/backend && source venv/bin/activate
python sensors/test_sensors.py

# API health check
curl http://localhost:8001/health | python3 -m json.tool
```

---

## Quick Reference Card

| Item | Value |
|------|-------|
| Dashboard URL (local) | `http://ot-monitor.local:8001/` |
| Dashboard URL (IP) | `http://192.168.x.x:8001/` |
| Default admin login | `admin / OTAdmin2024` |
| Default viewer login | `nurse / OTNurse2024` |
| Config file | `ot_monitor/config/config.yaml` |
| Sensor test script | `python sensors/test_sensors.py --loop` |
| Live backend logs | `sudo journalctl -u ot-monitor -f` |
| Restart backend | `sudo systemctl restart ot-monitor` |
| Switch to hardware mode | `data_source.type: hardware` in config.yaml |
| SCD30 I²C address | `0x61` |
| BME280 I²C address | `0x76` (SDO→GND) |
| PMS5003 UART port | `/dev/ttyAMA1` |
| Required I²C speed | `10000` Hz (10 kHz) — for SCD30 clock stretching |
| SCD30 warmup | ~10 seconds for first reading |

---

*Document version: June 2026 — Hardware revision: SCD30 + BME280 + PMS5003 on Raspberry Pi 4*
