# Hardware Integration Guide
## OT Infection Monitoring System — Raspberry Pi 4 + SCD30 + BME280 + PMS5003

> **Goal:** Take you from an unboxed Raspberry Pi to a fully running live sensor backend in the shortest path possible, with clear checkpoints and solutions to every common error.

---

## Before You Start — Prerequisites Checklist

Complete every checkbox before touching the hardware.

| # | Item | Why it matters |
|---|------|----------------|
| ☐ | Raspberry Pi 4 (2 GB RAM min) | Main compute unit |
| ☐ | MicroSD card ≥ 16 GB (Class 10 / A1) | OS + SQLite database |
| ☐ | Official 5V 3A USB-C power supply | Underpowering causes random reboots |
| ☐ | Sensirion SCD30 breakout board | CO₂, Temperature, Humidity |
| ☐ | Bosch BME280 breakout board | Barometric Pressure |
| ☐ | Plantower PMS5003 with ZH cable | PM1.0 / PM2.5 / PM10 |
| ☐ | Female-to-female jumper wires (20 cm) | I²C & UART connections |
| ☐ | PC with internet access | Flashing OS, SSH |
| ☐ | Router / switch to connect RPi | Network access for dashboard |

---

## Integration Roadmap

```
STEP 1           STEP 2           STEP 3           STEP 4           STEP 5
Wire sensors  →  Flash RPi OS  →  Enable I²C    →  Run sensor    →  Switch to
to RPi           & SSH in         & UART           test script      hardware mode
```

Each step ends with a **checkpoint** you must pass before proceeding.

---

## Step 1 — Wire the Sensors

> Power off the RPi completely before wiring. Never hot-plug sensors.

### 1.1 SCD30 → Raspberry Pi (I²C)

| SCD30 Pin | RPi Physical Pin | RPi Signal |
|-----------|-----------------|------------|
| VCC | Pin 1 | 3.3V — **not 5V** |
| GND | Pin 6 | GND |
| SDA | Pin 3 | GPIO2 / SDA1 |
| SCL | Pin 5 | GPIO3 / SCL1 |
| SEL | Pin 6 | GND — **tie here to select I²C mode** |

### 1.2 BME280 → Raspberry Pi (I²C, shared bus)

| BME280 Pin | RPi Physical Pin | RPi Signal |
|------------|-----------------|------------|
| VCC / 3V3 | Pin 1 | 3.3V |
| GND | Pin 6 | GND |
| SDA | Pin 3 | GPIO2 / SDA1 — **shared with SCD30** |
| SCL | Pin 5 | GPIO3 / SCL1 — **shared with SCD30** |
| SDO / ADDR | Pin 6 | GND → I²C address = `0x76` |
| CSB | Pin 1 | 3.3V → I²C mode |

### 1.3 PMS5003 → Raspberry Pi (UART0 — GPIO14/GPIO15)

| PMS5003 Pin | Label | RPi Physical Pin | RPi Signal |
|-------------|-------|-----------------|------------|
| 1 | VCC | Pin 2 | **5V** — PMS5003 requires 5V |
| 2 | GND | Pin 9 | GND |
| 3 | SET | Pin 11 | GPIO17 — pull HIGH = enabled |
| 4 | RX | **Pin 8** | **GPIO14 / UART0 TXD0** — cross-connect |
| 5 | TX | **Pin 10** | **GPIO15 / UART0 RXD0** — cross-connect |
| 6 | RESET | Pin 13 | GPIO27 — pull HIGH = normal |

> **UART0 setup required** — GPIO14/15 are used by Bluetooth on RPi 4 by default.
> Add to `/boot/firmware/config.txt`: `dtoverlay=disable-bt` and `enable_uart=1`.
> Also disable serial login shell via raspi-config (Interface Options → Serial Port).
> After reboot `/dev/serial0` → `/dev/ttyAMA0` is ready for the PMS5003.

### 1.4 Wiring Diagram

```
RPi 4 Pins                       Sensor
─────────────────────────────────────────────────────────
Pin  1 (3.3V)  ────┬──────────── SCD30  VCC
                   └──────────── BME280 VCC + BME280 CSB

Pin  2 (5V)    ─────────────── PMS5003 Pin 1 (VCC)

Pin  3 (SDA)   ────┬──────────── SCD30  SDA
                   └──────────── BME280 SDA

Pin  5 (SCL)   ────┬──────────── SCD30  SCL
                   └──────────── BME280 SCL

Pin  6 (GND)   ────┬──────────── SCD30  GND
                   ├──────────── SCD30  SEL   (I²C mode)
                   ├──────────── BME280 GND
                   └──────────── BME280 SDO   (addr 0x76)

Pin  9 (GND)   ─────────────── PMS5003 Pin 2 (GND)
Pin 11 (GPIO17)  ─────────────── PMS5003 Pin 3 (SET)
Pin 13 (GPIO27)  ─────────────── PMS5003 Pin 6 (RESET)
Pin  8 (GPIO14/UART0 TX) ─────── PMS5003 Pin 4 (RX)
Pin 10 (GPIO15/UART0 RX) ─────── PMS5003 Pin 5 (TX)
```

### Checkpoint 1 ✓
- All sensor pins connected to the correct RPi pins
- SCD30 SEL tied to GND
- BME280 SDO tied to GND and CSB tied to 3.3V
- PMS5003 RX and TX are **crossed** (sensor RX → RPi TX, sensor TX → RPi RX)

---

## Step 2 — Flash Raspberry Pi OS & Connect

### 2.1 Flash the SD Card (Windows / Mac / Linux)

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Insert your microSD card
3. **Choose Device:** Raspberry Pi 4
4. **Choose OS:** Raspberry Pi OS Lite (64-bit) — Bookworm
5. Click the **gear icon (⚙)** and configure:
   ```
   Hostname:  ot-monitor
   Username:  msa
   Password:  (choose a strong password)
   SSH:       Enabled
   Wi-Fi:     (your network SSID + password, if using Wi-Fi)
   Timezone:  Asia/Kolkata  (or your local zone)
   ```
6. Click **Write** — wait for verification to complete

### 2.2 First Boot

Insert SD card into RPi, power on, wait ~90 seconds, then SSH in:

```bash
ssh msa@ot-monitor.local
```

If `.local` does not resolve, find the RPi's IP from your router's DHCP list and use that directly:

```bash
ssh msa@192.168.x.x
```

### 2.3 Update the OS

```bash
sudo apt update && sudo apt full-upgrade -y
sudo reboot
```

### Checkpoint 2 ✓
- SSH login successful
- `uname -a` shows a 64-bit ARM kernel
- System is up to date

---

## Step 3 — Enable I²C and UART0

SSH back in after the reboot.

### 3.1 Enable I²C via raspi-config

```bash
sudo raspi-config
```

Navigate: `Interface Options → I2C → Enable → OK → Finish`

### 3.2 Disable Serial Login Shell (free UART0 for PMS5003)

Still inside `raspi-config`:

```
Interface Options → Serial Port
  "Login shell over serial?" → NO
  "Serial port hardware enabled?" → YES
```

### 3.3 Disable Bluetooth and Enable UART0 on GPIO14/GPIO15

Edit the boot config:

```bash
sudo nano /boot/firmware/config.txt
```

> On older Bullseye systems the path is `/boot/config.txt`

Scroll to the bottom and add these lines:

```ini
# Slow I²C to 10 kHz for SCD30 clock-stretching
dtparam=i2c_arm_baudrate=10000

# Disable Bluetooth — frees UART0 (PL011) for GPIO14/GPIO15 (PMS5003)
dtoverlay=disable-bt

# Enable full PL011 hardware UART on GPIO14 (TXD0, Pin 8) / GPIO15 (RXD0, Pin 10)
enable_uart=1
```

Save and reboot:

```bash
sudo reboot
```

### 3.4 Verify Interfaces

After reboot, SSH back in and run:

```bash
# Install I²C tools if not present
sudo apt install -y i2c-tools

# Scan I²C bus — must show 0x61 and 0x76
i2cdetect -y 1

# Check UART0 device — serial0 must point to ttyAMA0 (not ttyS0)
ls -la /dev/serial0
```

**Expected i2cdetect output:**

```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:
10:
20:
30:
40:
50:
60: -- 61 -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- 76 --
```

| Address | Sensor |
|---------|--------|
| `0x61` | SCD30 (CO₂ / Temp / Humidity) |
| `0x76` | BME280 (Pressure) |

**Expected serial0 output:**
```
lrwxrwxrwx 1 root root 7 ... /dev/serial0 -> ttyAMA0
```
If `serial0 → ttyS0`, the `dtoverlay=disable-bt` or `enable_uart=1` line is missing.

### Checkpoint 3 ✓
- `i2cdetect -y 1` shows `61` and `76`
- `ls -la /dev/serial0` shows `serial0 -> ttyAMA0`

---

## Step 4 — Install Software & Run Sensor Tests

### 4.1 Install System Packages

```bash
sudo apt install -y python3-pip python3-venv git i2c-tools

# Add msa user to hardware groups — required to access sensors without sudo
sudo usermod -a -G dialout,i2c msa

# Apply group in current session (or reboot)
newgrp dialout
```

### 4.2 Clone the Repository

```bash
cd ~
git clone https://github.com/MSA5896/OT_Monitor_Dashboard.git ot_monitor
cd ot_monitor/ot_monitor/backend
```

### 4.3 Create Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

# Install hardware-specific sensor libraries (RPi only)
pip install \
    adafruit-blinka \
    adafruit-circuitpython-scd30 \
    adafruit-circuitpython-bme280 \
    pyserial \
    smbus2
```

> Do NOT install the Adafruit libraries on your development PC — they will fail outside of a RPi environment.

### 4.4 Run the Sensor Test Script

```bash
cd ~/ot_monitor/ot_monitor/backend
source venv/bin/activate

# Test all sensors at once (recommended first run)
python sensors/test_sensors.py

# Test a single sensor
python sensors/test_sensors.py --sensor scd30
python sensors/test_sensors.py --sensor bme280
python sensors/test_sensors.py --sensor pms5003

# Continuous live readings (Ctrl+C to stop)
python sensors/test_sensors.py --loop --interval 2
```

**All three sensors must show PASS:**

```
✓  SCD30      PASS
✓  BME280     PASS
✓  PMS5003    PASS

✓  All sensors passed! Switch config.yaml → data_source.type: hardware
```

### Checkpoint 4 ✓
- All three sensors show **PASS** in the test script
- No errors in terminal output

---

## Step 5 — Switch to Hardware Mode & Start the Backend

### 5.1 Edit config.yaml

```bash
nano ~/ot_monitor/ot_monitor/config/config.yaml
```

Make these changes:

```yaml
# Change data source from simulator to real hardware
data_source:
  type: hardware          # ← was: simulator

# Listen on all network interfaces (access from any device)
server:
  host: "0.0.0.0"        # ← was: 127.0.0.1
  port: 8001

# Generate and set a strong session secret
auth:
  session_secret: "paste-your-generated-secret-here"

# Change default passwords
  users:
    - username: "admin"
      password: "YourStrongAdminPassword"
      role: "admin"
    - username: "nurse"
      password: "YourStrongNursePassword"
      role: "viewer"
```

Generate a strong secret:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 5.2 Start the Backend (Manual Test)

```bash
cd ~/ot_monitor/ot_monitor/backend
source venv/bin/activate
python main.py
```

Expected output:

```
12:00:01  INFO  SCD30 ready — CO₂, Temperature, Humidity
12:00:01  INFO  BME280 ready — Barometric Pressure
12:00:01  INFO  PMS5003 ready — PM1.0 / PM2.5 / PM10
12:00:01  INFO  HardwareSource started — 3 sensors, polling every 2.0 s
12:00:01  INFO  OT Monitor backend started  ✓  (ot_id=OT-01, source=hardware)
```

Open the dashboard from any browser on the same network:

```
http://ot-monitor.local:8001/
```

### 5.3 Enable Auto-Start on Boot (Production)

```bash
sudo nano /etc/systemd/system/ot-monitor.service
```

Paste:

```ini
[Unit]
Description=OT Infection Monitor Backend
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=msa
WorkingDirectory=/home/msa/ot_monitor/ot_monitor/backend
ExecStart=/home/msa/ot_monitor/ot_monitor/backend/venv/bin/python main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ot-monitor
sudo systemctl start ot-monitor

# Verify it is running
sudo systemctl status ot-monitor
```

### Checkpoint 5 ✓
- Dashboard loads and shows **real** sensor values
- CO₂, PM, and Pressure KPI cards all populated
- `sudo systemctl status ot-monitor` shows `active (running)`

---

## Common Errors & Solutions

### I²C Errors

---

**Error: `i2cdetect -y 1` shows no devices (blank grid)**

```
Cause:  I²C interface is not enabled on the RPi.
Fix:
  sudo raspi-config
  → Interface Options → I2C → Enable → Finish
  sudo reboot
```

---

**Error: Only one of 0x61 or 0x76 appears in i2cdetect**

```
Cause:  One sensor has a wiring fault.

If 0x61 (SCD30) is missing:
  • Check SCD30 SEL pin is tied to GND (not floating)
  • Re-seat SDA and SCL wires on the SCD30 breakout

If 0x76 (BME280) is missing:
  • Check BME280 SDO is tied to GND (gives address 0x76)
  • Check BME280 CSB is tied to 3.3V (selects I²C mode)
  • Try address 0x77 in case SDO is actually tied to 3.3V:
      python sensors/test_sensors.py --sensor bme280
    (the test script auto-probes both 0x76 and 0x77)
```

---

**Error: `SCD30 data_available timeout` or `OSError: [Errno 121] Remote I/O error`**

```
Cause:  I²C bus speed is too high for the SCD30's clock-stretching requirement.
Fix:
  sudo nano /boot/firmware/config.txt
  → Add at bottom:  dtparam=i2c_arm_baudrate=10000
  sudo reboot
  i2cdetect -y 1    # verify sensor appears again
```

---

**Error: `SCD30 CRC mismatch` errors in backend logs**

```
Cause:  I²C speed still too high, or poor quality jumper wires causing signal noise.
Fix:
  1. Confirm dtparam=i2c_arm_baudrate=10000 is in /boot/firmware/config.txt
  2. Replace jumper wires with shorter, better-quality ones (≤15 cm)
  3. Add 100 nF decoupling capacitor between SDA and GND as a last resort
```

---

**Error: `FileNotFoundError: [Errno 2] No such file or directory: '/dev/i2c-1'`**

```
Cause:  I²C kernel module not loaded.
Fix:
  sudo modprobe i2c-dev
  # To make permanent:
  echo "i2c-dev" | sudo tee -a /etc/modules
  sudo reboot
```

---

### UART / PMS5003 Errors

---

**Error: `/dev/serial0` points to `ttyS0` instead of `ttyAMA0`**

```
Cause:  Bluetooth still owns UART0, or enable_uart=1 is missing.
Fix:
  sudo nano /boot/firmware/config.txt
  → Add at bottom:
      dtoverlay=disable-bt
      enable_uart=1
  sudo reboot
  ls -la /dev/serial0    # must show: serial0 -> ttyAMA0
```

---

**Error: `PermissionError: [Errno 13] Permission denied: '/dev/serial0'`**

```
Cause:  The msa user is not in the dialout group.
Fix:
  sudo usermod -a -G dialout msa
  # Log out and back in (or reboot) for the group change to take effect
  groups msa    # should list dialout
```

---

**Error: PMS5003 `checksum error` or `timeout reading frame`**

```
Cause:  RX/TX wires are either loose, swapped, or crossed incorrectly.
Fix:
  • Power off the RPi
  • Confirm: PMS5003 TX (Pin 5) → RPi GPIO15 / UART0 RX (physical Pin 10)
             PMS5003 RX (Pin 4) → RPi GPIO14 / UART0 TX (physical Pin 8)
  • Re-seat both wires firmly
  • Power back on and retest
```

---

**Error: PMS5003 reads all zeros (PM1.0=0, PM2.5=0, PM10=0)**

```
Cause 1: Sensor is in sleep mode — SET pin not held HIGH.
Fix:     Confirm PMS5003 Pin 3 (SET) is connected to RPi Pin 11 (GPIO17).
         GPIO17 is configured HIGH by the driver at startup.

Cause 2: Sensor needs 30 seconds to warm up its fan and laser.
Fix:     Wait 30 seconds after power-on before reading.

Cause 3: Laser diode end-of-life (sensor is >3 years old at 24/7 operation).
Fix:     Replace the PMS5003.
```

---

### Python / Software Errors

---

**Error: `ModuleNotFoundError: No module named 'adafruit_blinka'` or `No module named 'board'`**

```
Cause:  Hardware sensor libraries are not installed, or wrong Python environment.
Fix:
  source ~/ot_monitor/ot_monitor/backend/venv/bin/activate
  pip install adafruit-blinka adafruit-circuitpython-scd30 adafruit-circuitpython-bme280 smbus2 pyserial
```

---

**Error: `RuntimeError: This library requires Linux` or `libgpiod` errors**

```
Cause:  You are running the script on a Windows/Mac development machine, not the RPi.
Fix:    The hardware sensor libraries only run on Raspberry Pi.
        Use 'simulator' mode on your development machine:
        data_source:
          type: simulator
```

---

**Error: `yaml.scanner.ScannerError` when starting the backend**

```
Cause:  Syntax error introduced in config.yaml (usually wrong indentation).
Fix:
  # Validate the YAML syntax:
  python3 -c "import yaml; yaml.safe_load(open('config/config.yaml'))"
  # Fix the reported line number in config.yaml
  # YAML uses 2-space indentation — do not mix tabs and spaces
```

---

**Error: `Address already in use` on port 8001**

```
Cause:  A previous backend process is still running.
Fix:
  # Find and stop the existing process
  sudo systemctl stop ot-monitor
  # Or kill by port:
  sudo lsof -ti:8001 | xargs kill -9
```

---

### Network / Dashboard Errors

---

**Error: Dashboard unreachable from another device on the network**

```
Cause:  Backend is listening only on localhost (127.0.0.1).
Fix:
  nano ~/ot_monitor/ot_monitor/config/config.yaml
  # Change:
  server:
    host: "0.0.0.0"
  sudo systemctl restart ot-monitor
```

---

**Error: Browser shows "Backend offline" banner**

```
Cause:  Backend service crashed or was not started.
Fix:
  sudo systemctl status ot-monitor       # check status
  sudo journalctl -u ot-monitor -n 50    # read last 50 log lines
  sudo systemctl restart ot-monitor      # restart after fixing the error
```

---

**Error: Dashboard shows "Warming Up…" on CO₂ card for more than 60 seconds**

```
Cause:  SCD30 sensor is not returning data.
Fix:
  1. Stop the backend
  2. Run: python sensors/test_sensors.py --sensor scd30
  3. If it fails, see I²C errors above
```

---

**Error: Login always fails / "Authentication required" on every page**

```
Cause 1: Wrong username or password.
Fix:     Check auth.users in config.yaml for the correct credentials.

Cause 2: Session cookie not saved because page is opened as a file (file://).
Fix:     Always access the dashboard via http://  not  file://
         http://ot-monitor.local:8001/
```

---

### systemd Service Errors

---

**Error: `sudo systemctl start ot-monitor` fails immediately**

```
Fix:
  sudo journalctl -u ot-monitor -n 50 --no-pager
  # Read the error. Most common causes:
  # - Virtual environment path is wrong in the service file
  # - config.yaml has a syntax error
  # - Sensor not wired (fix wiring and retry)
```

---

**Error: Service starts then stops after a few seconds (Restart=on-failure loops)**

```
Cause:  Backend throws an uncaught exception on startup.
Fix:
  sudo journalctl -u ot-monitor -n 100 --no-pager
  # Look for the Python traceback. Common root causes:
  # - I²C or UART device not found (sensor wiring issue)
  # - config.yaml missing required key
  # - Port 8001 already in use
```

---

## Quick Diagnostics — Run Any Time

Paste this block into the RPi terminal to get a full health snapshot:

```bash
echo "=== Service Status ===" && sudo systemctl status ot-monitor --no-pager
echo "" && echo "=== Last 30 Log Lines ===" && sudo journalctl -u ot-monitor -n 30 --no-pager
echo "" && echo "=== I²C Scan ===" && i2cdetect -y 1
echo "" && echo "=== UART0 ===" && ls -la /dev/serial0
echo "" && echo "=== Sensor Test ===" && cd ~/ot_monitor/ot_monitor/backend && source venv/bin/activate && python sensors/test_sensors.py
echo "" && echo "=== API Health ===" && curl -s http://localhost:8001/health | python3 -m json.tool
```

---

## Quick Reference

| Item | Value |
|------|-------|
| Dashboard (hostname) | `http://ot-monitor.local:8001/` |
| Dashboard (IP) | `http://192.168.x.x:8001/` |
| Default admin login | `admin / OTAdmin2024` |
| Default viewer login | `nurse / OTNurse2024` |
| Config file | `ot_monitor/config/config.yaml` |
| Sensor test | `python sensors/test_sensors.py --loop` |
| Live logs | `sudo journalctl -u ot-monitor -f` |
| Restart backend | `sudo systemctl restart ot-monitor` |
| Enable hardware mode | Set `data_source.type: hardware` in config.yaml |
| SCD30 I²C address | `0x61` (fixed) |
| BME280 I²C address | `0x76` (SDO → GND) or `0x77` (SDO → 3.3V) |
| PMS5003 UART port | `/dev/serial0` (UART0, GPIO14/GPIO15) |
| Required I²C speed | `10000` Hz (10 kHz) — mandatory for SCD30 |
| SCD30 first-read warmup | ~10 seconds |
| PMS5003 fan/laser warmup | ~30 seconds |

---

*Hardware Integration Guide — June 2026 | Sensors: SCD30 + BME280 + PMS5003 on Raspberry Pi 4*
