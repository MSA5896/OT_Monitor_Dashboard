# OT Environment Monitoring System
# Raspberry Pi Setup Guide — Step by Step
### Version 1.1 | Updated: March 2026 | Suitable for beginners

---

> **Before you start:** Read every step fully before doing it. Do not skip any step. Each step must be completed before moving to the next one.

---

## What Hardware You Need

Before starting, make sure you have all of these items physically in hand:

| Item | Quantity | Notes |
|---|---|---|
| Raspberry Pi 4 Model B | 1 | 4 GB RAM recommended |
| MicroSD Card | 1 | 32 GB or 64 GB — **SanDisk Ultra or Samsung Pro Endurance only** |
| USB-C Power Supply (5V 3A) | 1 | Use the official Raspberry Pi 4 charger. Generic phone chargers will cause problems. |
| BME280 Sensor Breakout Board | 1 | Temperature + Humidity + Atmospheric Pressure |
| MH-Z19B CO₂ Sensor | 1 | Measures carbon dioxide in the room |
| PMS5003 Particle Sensor | 1 | Measures dust particles (PM1.0, PM2.5, PM10) |
| Jumper Wires (Female to Female) | 20+ | For connecting sensors to the RPi GPIO header |
| HDMI Cable + Monitor | 1 | For the first-time setup only |
| USB Keyboard + Mouse | 1 set | For the first-time setup only |
| Your Laptop | 1 | Windows laptop with the ot_monitor project files |
| Internet Connection | — | The RPi needs internet during setup |
| MicroSD Card Reader | 1 | To write the OS onto the SD card from your laptop |

> **About the pressure sensor:** The BME280 sensor already measures atmospheric barometric pressure (hPa) — the environmental air pressure of the OT room. A separate differential pressure sensor (SDP810) is **not needed** and has been removed from the system.

---

## PART 1 — Prepare the Raspberry Pi (Done on Your Laptop)

### Step 1 — Download Raspberry Pi Imager on your Laptop

1. On your **laptop**, open a web browser
2. Go to: **https://www.raspberrypi.com/software/**
3. Click **Download for Windows**
4. Install the downloaded file (it's like any normal Windows installer)

### Step 2 — Write the Operating System onto the MicroSD Card

1. Insert your MicroSD card into your laptop using the card reader
2. Open **Raspberry Pi Imager** (search for it in the Start Menu)
3. Click **"Choose Device"** → Select **Raspberry Pi 4**
4. Click **"Choose OS"** → Select **Raspberry Pi OS (64-bit)** — the first option
5. Click **"Choose Storage"** → Select your MicroSD card

> ⚠️ **WARNING:** Everything currently on the MicroSD card will be permanently erased. Make sure you selected the right storage device.

6. Click **Next**
7. A popup will ask **"Would you like to apply OS customisation settings?"** — Click **Edit Settings**
8. Fill in the following:
   - **Set hostname:** `ot-monitor`
   - **Set username:** `pi` and set a password you will remember
   - **Configure wireless LAN:** Enter your WiFi name and password (so RPi connects to your network automatically)
   - **Set locale settings:** Select your timezone — `Asia/Kolkata`
9. Click **Save**, then click **Yes**
10. Click **Yes** again to confirm erasing the card
11. Wait for the writing and verification to complete (5–10 minutes)
12. Remove the MicroSD card from your laptop

### Step 3 — Insert the SD Card and First Boot

1. Insert the MicroSD card into the Raspberry Pi (slot is on the bottom side)
2. Connect the monitor via HDMI
3. Connect the USB keyboard and mouse
4. Plug in the USB-C power supply last — this starts the RPi

> The RPi will boot up and show a desktop. The first boot takes about 2–3 minutes. This is normal.

5. The desktop will appear. You will see the Raspberry Pi OS desktop.

---

## PART 2 — Initial Configuration (Done on the Raspberry Pi)

> **You are now working directly on the Raspberry Pi.** Use its keyboard and monitor for Steps 4–9.

### Step 4 — Find the Raspberry Pi's IP Address

You need the IP address to connect to the RPi from your laptop later.

1. Click on the **Terminal** icon in the taskbar (it looks like a black screen with `>_`)
2. Type this command and press Enter:
   ```
   hostname -I
   ```
3. You will see something like: `192.168.1.105`
4. **Write this number down.** You will need it later.

### Step 5 — Enable I2C (for the BME280 sensor)

The BME280 sensor communicates using a protocol called I2C. You need to enable it first.

1. In the Terminal, type:
   ```
   sudo raspi-config
   ```
2. A blue menu screen will appear. Use the **arrow keys** to navigate, **Enter** to select.
3. Go to: **Interface Options**
4. Go to: **I2C**
5. Select **Yes** when asked "Would you like the ARM I2C interface to be enabled?"
6. Press **Enter** on OK
7. You are back at the main menu — **do not exit yet**, continue to Step 6.

### Step 6 — Enable UART Serial Port (for the MH-Z19B CO₂ sensor)

The CO₂ sensor communicates using a serial UART connection. You need to free the RPi's UART port.

1. Still in the **raspi-config** blue menu, go to: **Interface Options**
2. Go to: **Serial Port**
3. Question: **"Would you like a login shell to be accessible over the serial port?"** → Select **No**

   > This is important. Selecting No frees the serial port for the CO₂ sensor. If you select Yes, the sensor cannot use the port.

4. Question: **"Would you like the serial port hardware to be enabled?"** → Select **Yes**
5. Press **Enter** on OK
6. Now press the right arrow key to highlight **Finish** and press Enter
7. It will ask **"Would you like to reboot now?"** → Select **Yes**

> The RPi will now restart. Wait for it to boot back to the desktop (about 1 minute).

### Step 7 — Enable UART2 (for the PMS5003 particle sensor)

The particle sensor uses a second UART port (UART2). This is not enabled by default. You need to add one line to a system file.

1. Open the Terminal again
2. Type this command **exactly as shown** and press Enter:
   ```
   echo "dtoverlay=uart2" | sudo tee -a /boot/firmware/config.txt
   ```

   > If you get an error saying "No such file or directory", try this instead:
   > ```
   > echo "dtoverlay=uart2" | sudo tee -a /boot/config.txt
   > ```

3. Now restart the RPi:
   ```
   sudo reboot
   ```

> Wait for it to boot back to the desktop.

### Step 8 — Verify Everything is Enabled (Smoke Test)

After the RPi restarts, open the Terminal and run these checks one by one:

**Check 1 — I2C bus:**
```
ls /dev/i2c-1
```
You should see: `/dev/i2c-1`
If you see "No such file", go back to Step 5.

**Check 2 — UART0 (CO₂ sensor port):**
```
ls /dev/serial0
```
You should see: `/dev/serial0`
If not, go back to Step 6.

**Check 3 — UART2 (PMS5003 particle sensor port):**
```
ls /dev/ttyAMA1
```
You should see: `/dev/ttyAMA1`
If not, go back to Step 7.

> ✅ If all three checks pass, you are ready to wire the sensors.

---

## PART 3 — Wire the Sensors to the Raspberry Pi

> ⚠️ **CRITICAL:** Before connecting any sensor, **UNPLUG the RPi's power supply**. Never connect or disconnect sensors while the RPi is powered on. This can permanently damage both the sensor and the RPi.

The Raspberry Pi has a 40-pin header (two rows of 20 pins). Pins are numbered 1 to 40. Pin 1 is at the corner nearest the SD card slot.

```
RPi GPIO Header — Top View

 Pin 1  [3.3V]  ●  ● [5V]     Pin 2
 Pin 3  [SDA1]  ●  ● [5V]     Pin 4
 Pin 5  [SCL1]  ●  ● [GND]    Pin 6
 Pin 7  [GPIO4] ●  ● [GPIO14] Pin 8  (TX)
 Pin 9  [GND]   ●  ● [GPIO15] Pin 10 (RX)
 Pin 11 [GPIO17]●  ● [GPIO18] Pin 12
 Pin 13 [GPIO27]●  ● [GND]    Pin 14
 ...
 Pin 21 [GPIO9] ●  ● [GPIO25] Pin 22
 Pin 23 [GPIO11]●  ● [GPIO8]  Pin 24 (TX2)
 Pin 25 [GND]   ●  ● [GPIO7]  Pin 26
```

---

### Sensor 1 — BME280 (Temperature, Humidity, Atmospheric Pressure)

The BME280 uses the I2C protocol. It shares the I2C bus with no conflict.

| BME280 Pin Label | Wire Colour (usual) | Connect to RPi Pin |
|---|---|---|
| VCC or 3V3 | Red | **Pin 1 (3.3V)** |
| GND | Black | **Pin 6 (GND)** |
| SDA | Yellow or White | **Pin 3 (SDA1)** |
| SCL | Orange or Green | **Pin 5 (SCL1)** |
| SDO | — | Connect to GND (Pin 6) → sets address to 0x76 |

> ⚠️ **CRITICAL:** The BME280 runs on **3.3V only.** Never connect VCC to Pin 2 or Pin 4 (which are 5V). Connecting 5V will permanently destroy the BME280.

> **SDO pin:** Some BME280 breakout boards have an SDO or ADDR pin. Connect it to GND. If your board only has 4 pins (VCC, GND, SDA, SCL), just connect those 4 — the SDO is already handled internally.

---

### Sensor 2 — MH-Z19B (CO₂ Sensor)

The MH-Z19B uses UART serial communication and runs on 5V.

| MH-Z19B Pin Label | Wire Colour (usual) | Connect to RPi Pin |
|---|---|---|
| Vin or 5V | Red | **Pin 4 (5V)** |
| GND | Black | **Pin 14 (GND)** |
| TX (sensor sends) | Green | **Pin 10 (GPIO15 / RX)** |
| RX (sensor receives) | Blue | **Pin 8 (GPIO14 / TX)** |

> **Note on TX/RX:** TX from the sensor must go to RX on the RPi, and vice versa. This is called "crossover" wiring — it is always done this way with serial sensors.

> ⚠️ **CRITICAL:** The MH-Z19B has PWM and HD pins on some versions — **do not connect** those. Only connect VIN, GND, TX, and RX.

> ⚠️ **Warm-up time:** After powering on, the MH-Z19B needs exactly **3 minutes** before it returns valid CO₂ readings. During this time, the dashboard will show "Warming Up…" — this is normal and expected. Do not turn off and on the sensor repeatedly.

---

### Sensor 3 — PMS5003 (PM1.0 / PM2.5 / PM10 Particle Sensor)

The PMS5003 uses an 8-pin JST connector. The cable usually comes with the sensor.

| PMS5003 Pin Number | What it is | Connect to RPi Pin |
|---|---|---|
| Pin 1 (VCC) | Power | **Pin 2 (5V)** |
| Pin 2 (GND) | Ground | **Pin 9 (GND)** |
| Pin 3 (SET) | Enable | **Pin 11 (GPIO17)** — pull HIGH to keep sensor on |
| Pin 4 (RX) | Sensor receives data | **Pin 24 (GPIO8 / UART2 TX)** |
| Pin 5 (TX) | Sensor sends data | **Pin 21 (GPIO9 / UART2 RX)** |
| Pin 6 (RESET) | Reset | **Pin 13 (GPIO27)** — pull HIGH for normal |
| Pin 7 | Not connected | Leave unconnected |
| Pin 8 | Not connected | Leave unconnected |

> **Note:** If you do not have Pin 3 (SET) and Pin 6 (RESET) connected, the sensor may not start correctly. These pins must be pulled HIGH (connected to 3.3V or the GPIO pins listed above).

> ⚠️ **CRITICAL:** The PMS5003 sends 3.3V logic level output even though it runs on 5V power. This means it is directly compatible with the RPi — no voltage converter is needed.

---

### Complete Connection Summary

```
                    ┌────────────────────────────────────────┐
                    │         Raspberry Pi 4 GPIO            │
                    │                                        │
  BME280 VCC  ──── │ Pin 1  (3.3V)                          │
  BME280 SDA  ──── │ Pin 3  (SDA1  I2C)                     │
  BME280 SCL  ──── │ Pin 5  (SCL1  I2C)                     │
  BME280 GND  ──┐                                           │
  BME280 SDO  ──┘─ │ Pin 6  (GND)                           │
                    │                                        │
  MH-Z19B TX  ──── │ Pin 10 (GPIO15 / UART0 RX)             │
  MH-Z19B RX  ──── │ Pin 8  (GPIO14 / UART0 TX)             │
  MH-Z19B GND ──── │ Pin 14 (GND)                           │
  MH-Z19B Vin ──── │ Pin 4  (5V)                            │
                    │                                        │
  PMS5003 TX  ──── │ Pin 21 (GPIO9  / UART2 RX)             │
  PMS5003 RX  ──── │ Pin 24 (GPIO8  / UART2 TX)             │
  PMS5003 SET ──── │ Pin 11 (GPIO17)                        │
  PMS5003 RST ──── │ Pin 13 (GPIO27)                        │
  PMS5003 GND ──── │ Pin 9  (GND)                           │
  PMS5003 VCC ──── │ Pin 2  (5V)                            │
                    └────────────────────────────────────────┘
```

---

## PART 4 — Install the Software on Raspberry Pi (From Your Laptop via SSH)

> From this point, you will **not need the keyboard, mouse, or monitor connected to the RPi**. You will control the RPi remotely from your laptop using SSH — this is like remotely typing commands inside the RPi.

### Step 9 — Connect to RPi from Your Laptop via SSH

1. On your **laptop**, open **Windows PowerShell** (search for it in Start menu)
2. Type the following, replacing `192.168.1.105` with **your RPi's IP address** from Step 4:
   ```
   ssh pi@192.168.1.105
   ```
3. First time connecting: It will ask "Are you sure you want to continue?" → Type `yes` and press Enter
4. It will ask for your password → Type the password you set in Step 2 (characters will not appear — this is normal)
5. You will see a prompt like: `pi@ot-monitor:~ $`

> ✅ You are now inside the Raspberry Pi. Every command you type from now runs on the RPi, not on your laptop.

### Step 10 — Update the RPi System

Run this to make sure the RPi has the latest system software:

```bash
sudo apt update && sudo apt upgrade -y
```

> This may take 5–10 minutes. Let it finish completely.

### Step 11 — Install Required System Packages

```bash
sudo apt install -y python3-pip python3-venv git i2c-tools
```

### Step 12 — Verify Sensors are Detected on I2C

Plug in the power, then run:

```bash
i2cdetect -y 1
```

You should see a grid with **`76`** appearing (that is the BME280 at address 0x76).

```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:
...
70: -- -- -- -- -- -- 76 --
```

> If `76` does not appear: check your BME280 wiring. Most likely the SDA or SCL jumper wire is not connected firmly.

### Step 13 — Copy the Project to the Raspberry Pi

On your **laptop**, open a new PowerShell window (keep the SSH one open too) and run:

```powershell
scp -r "D:\Private\Development\ot_monitor" pi@192.168.1.105:/home/pi/
```

> Replace the IP address and the path `D:\Private\Development\ot_monitor` with the actual folder path on your laptop.

This copies all your project files to the RPi. Wait for it to finish.

### Step 14 — Install Python Packages on RPi

Switch back to your **SSH terminal** (the one where you are inside the RPi) and run:

```bash
cd /home/pi/ot_monitor/backend
pip3 install -r requirements.txt
pip3 install -r requirements-rpi.txt
```

> This installs all the Python libraries needed to communicate with the sensors. It may take 5–10 minutes.

> ⚠️ **CRITICAL:** Run `requirements-rpi.txt` **only on the Raspberry Pi**, not on your laptop. Those packages only work on RPi hardware.

---

## PART 5 — Test Each Sensor (Still via SSH)

This is the most important part. Test one sensor at a time before running the full system.

### Step 15 — Add Your User to the Serial Port Group

This allows Python to access the UART serial ports without needing "sudo" every time:

```bash
sudo usermod -a -G dialout pi
```

Then log out and log back in for the change to take effect:

```bash
exit
```

Then SSH back in (repeat Step 9).

### Step 16 — Run the Sensor Test Script

```bash
cd /home/pi/ot_monitor/backend
python3 sensors/test_sensors.py
```

The script will test all three sensors and print results in colour:
- ✅ Green = sensor is working
- ⚠️ Yellow = working but a warning (e.g. CO₂ sensor is warming up — this is normal)
- ❌ Red = sensor not detected — wiring problem

### Step 17 — Test Sensors Individually (If Any Fails)

```bash
# Test only BME280
python3 sensors/test_sensors.py --sensor bme280

# Test only CO₂ sensor
python3 sensors/test_sensors.py --sensor co2

# Test only PMS5003 particle sensor
python3 sensors/test_sensors.py --sensor pms5003

# Scan I2C bus
python3 sensors/test_sensors.py --sensor i2c
```

### Step 18 — Run a Live Continuous Test

```bash
python3 sensors/test_sensors.py --loop --interval 5
```

This shows live readings every 5 seconds. Press **Ctrl+C** to stop.

> ✅ When all three sensors show ✅ green, proceed to Part 6.

---

## PART 6 — Switch from Simulator to Real Hardware

### Step 19 — Edit config.yaml

```bash
nano /home/pi/ot_monitor/config/config.yaml
```

Find the line that says:
```yaml
  type: simulator
```

Change it to:
```yaml
  type: hardware
```

Save the file: Press **Ctrl+X**, then **Y**, then **Enter**.

### Step 20 — Start the Backend

```bash
cd /home/pi/ot_monitor/backend
python3 main.py
```

You should see output like:
```
14:22:01  INFO  BME280 ready — Temperature, Humidity, Pressure
14:22:01  INFO  MH-Z19B ready — CO₂ (warm-up: 180 s)
14:22:01  INFO  PMS5003 ready — PM1.0 / PM2.5 / PM10
14:22:01  INFO  HardwareSource started — 3 sensors, polling every 2.0 s
14:22:01  INFO  OT Monitor backend started ✓
INFO:     Uvicorn running on http://127.0.0.1:8000
```

> ✅ The backend is now running and reading real sensor data.

---

## PART 7 — Access the Dashboard from Your Laptop

### Step 21 — Open a New SSH Tunnel (For Dashboard Access)

The backend runs on the RPi at `127.0.0.1:8000`. To access it from your laptop browser, run this in a **new PowerShell window** on your laptop:

```powershell
ssh -L 8000:127.0.0.1:8000 pi@192.168.1.105
```

Now on your laptop browser, go to: **http://localhost:8000**

Or, if you are running the Flutter dashboard locally on your laptop, it will automatically connect to the backend via WebSocket at `ws://127.0.0.1:8000/ws`.

---

## PART 8 — Make the Backend Start Automatically on Boot

Right now if the RPi restarts, you have to manually run `python3 main.py` again. This step makes it start automatically.

### Step 22 — Create a Systemd Service

```bash
sudo nano /etc/systemd/system/ot-monitor.service
```

Paste this content exactly:

```ini
[Unit]
Description=OT Environment Monitoring Backend
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ot_monitor/backend
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Save: **Ctrl+X** → **Y** → **Enter**

Enable and start the service:

```bash
sudo systemctl enable ot-monitor
sudo systemctl start ot-monitor
```

Check that it started correctly:

```bash
sudo systemctl status ot-monitor
```

You should see `Active: active (running)` in green text.

> ✅ From now on, the backend starts automatically every time the RPi powers on — even after a power cut.

---

## Troubleshooting — Common Problems

| Problem | Symptom | Solution |
|---|---|---|
| BME280 not detected | `i2cdetect` shows no `76` | Check SDA→Pin3, SCL→Pin5. Make sure VCC is 3.3V (Pin 1), not 5V |
| CO₂ sensor not responding | `test_sensors` shows red for CO₂ | Check TX/RX crossover wiring. Verify serial is enabled in raspi-config. Run: `ls /dev/serial0` |
| PMS5003 not responding | `test_sensors` shows red for PM | Verify `ls /dev/ttyAMA1` exists. Check dtoverlay=uart2 was added to config.txt |
| CO₂ reads 0 or very low | Low/zero value | Sensor needs 3-minute warm-up. Wait 3 minutes after power-on |
| Permission denied on serial port | Python error says "Permission denied" | Run: `sudo usermod -a -G dialout pi` then log out and back in |
| Backend crashes immediately | Error in terminal | Check if config.yaml has `type: hardware`. Run test_sensors.py first |
| Dashboard shows "--" for all values | Flutter dashboard | Backend is not running. SSH in and check: `sudo systemctl status ot-monitor` |

---

## Checklist — Quick Reference

Use this as a final confirmation before each session:

- [ ] RPi powered on and connected to WiFi
- [ ] `i2cdetect -y 1` shows `76` (BME280)
- [ ] `ls /dev/serial0` returns without error (UART0)
- [ ] `ls /dev/ttyAMA1` returns without error (UART2)
- [ ] `sudo systemctl status ot-monitor` shows **active (running)**
- [ ] Dashboard is showing live values (wait 3 min for CO₂ to warm up)

---

*OT Environment Monitoring System | RPi Setup Guide v1.1 | March 2026*
