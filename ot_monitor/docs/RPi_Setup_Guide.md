# OT Monitor — Complete Hardware Installation Guide
## Raspberry Pi 4 Model B + SCD30 + BME280 + PMS5003
## Battery Powered: INR 18650 3S2P + LM2596S-5.0 + MT3608

---

## Table of Contents

1. [Hardware Shopping List](#1-hardware-shopping-list)
2. [Power System — Battery, LM2596S & MT3608](#2-power-system)
3. [Raspberry Pi 4 — GPIO Pinout Reference](#3-raspberry-pi-4--gpio-pinout-reference)
4. [Sensor 1 — SCD30 Wiring (CO₂, Temp, Humidity)](#4-sensor-1--scd30-wiring)
5. [Sensor 2 — BME280 Wiring (Barometric Pressure)](#5-sensor-2--bme280-wiring)
6. [Sensor 3 — PMS5003 Wiring (PM2.5 Air Quality)](#6-sensor-3--pms5003-wiring)
7. [Complete Wiring — All 3 Sensors + Power Together](#7-complete-wiring--all-3-sensors--power-together)
8. [Flash Raspberry Pi OS](#8-flash-raspberry-pi-os)
9. [First Boot & System Update](#9-first-boot--system-update)
10. [Enable I2C & UART2 Interfaces](#10-enable-i2c--uart2-interfaces)
11. [Verify Wiring with Software](#11-verify-wiring-with-software)
12. [Install Python Dependencies](#12-install-python-dependencies)
13. [Clone & Configure the Project](#13-clone--configure-the-project)
14. [Test All Sensors](#14-test-all-sensors)
15. [Switch to Hardware Mode](#15-switch-to-hardware-mode)
16. [Run the Backend](#16-run-the-backend)
17. [Autostart on Boot (systemd)](#17-autostart-on-boot-systemd)
18. [Access the Dashboard](#18-access-the-dashboard)
19. [Troubleshooting Guide](#19-troubleshooting-guide)

---

## 1. Hardware Shopping List

### Main Board

| # | Item | Specification | Where to Buy |
|---|------|---------------|-------------|
| 1 | **Raspberry Pi 4 Model B** | 4 GB RAM recommended | raspberrypi.com, Amazon |
| 1 | **MicroSD Card** | 32 GB, Class 10 / A1 rated | SanDisk, Samsung |
| 1 | **RPi 4 Case** | Any with GPIO header access | Amazon |

### Power System

| # | Item | Specification | Role |
|---|------|---------------|------|
| 1 | **Pro-Range INR 18650 Battery** | 11.1V, 5000mAh, 3C, 3S2P | Main power source |
| 1 | **LM2596S-5.0 Buck Module** | Step DOWN, Fixed 5V, 3A, TO-263-5L | Powers RPi 4 + PMS5003 |
| 1 | **MT3608 Boost Module** | Step UP, 2A max, adjustable up to 28V | Powers display / 12V loads |
| 1 | **5A Blade Fuse + Holder** | Inline, between battery and converters | Overcurrent protection |
| 1 | **Rocker Switch** | 15A 250V (or 10A 125V) | System on/off |

### Sensors

| # | Sensor | Measures | Interface | Buy From |
|---|--------|----------|-----------|----------|
| 1 | **Sensirion SCD30** | CO₂ (ppm), Temp (°C), Humidity (%RH) | I2C | Adafruit #4867, Sparkfun |
| 1 | **Bosch BME280 Breakout** | Pressure (hPa), Temp, Humidity | I2C | Adafruit #2652, Amazon |
| 1 | **Plantower PMS5003** | PM1.0, PM2.5, PM10 (µg/m³) | UART | Amazon, AliExpress |

### Accessories

| # | Item | Notes |
|---|------|-------|
| 20+ | Female-to-Female Jumper Wires | 20 cm length |
| 1 | Mini Breadboard | For neat multi-sensor connections |
| 1 | USB Keyboard + Mouse | Setup only |
| 1 | HDMI Monitor / TV | Setup only |

> **SCD30 Note:** Ensure the breakout board exposes VCC, GND, SDA, SCL, and SEL pins.
> **PMS5003 Note:** It comes with a ZH1.25mm cable. You need a cable adapter or solder jumper wires to it.

---

## 2. Power System

### 2.1 — Battery Specifications

```
  ┌─────────────────────────────────────────────────────────────┐
  │          PRO-RANGE INR 18650 BATTERY PACK                   │
  │                                                             │
  │  Chemistry  : INR (Li-NMC — Lithium Nickel Manganese        │
  │               Cobalt Oxide) — safer, high energy density    │
  │  Config     : 3S2P (3 cells series × 2 cells parallel)     │
  │  Voltage    : 11.1V nominal  |  12.6V full  |  9.0V cutoff │
  │  Capacity   : 5000 mAh  =  55.5 Wh                        │
  │  Max disch. : 3C × 5000mAh = 15A peak                      │
  │  Output     : + (RED) and − (BLACK) terminals               │
  │  Protection : Built-in BMS (over-current, over-voltage,     │
  │               short-circuit, deep-discharge protection)     │
  └─────────────────────────────────────────────────────────────┘

  Cell arrangement:

      [Cell A1]─[Cell B1]─[Cell C1]   ← series string 1
           ║         ║         ║
      [Cell A2]─[Cell B2]─[Cell C2]   ← series string 2
           │                   │
          (−)               (+)
        9–12.6V output
```

---

### 2.2 — Power Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │     INR 18650 3S2P BATTERY PACK             │
                    │     11.1V nominal  |  5000 mAh              │
                    └──────────────┬──────────────────────────────┘
                                   │
                           [ROCKER SWITCH]
                                   │
                           [5A BLADE FUSE]
                                   │
                  ┌────────────────┴────────────────┐
                  │                                 │
           LM2596S-5.0                          MT3608
          (STEP DOWN)                          (STEP UP)
          11.1V → 5V                         11.1V → 12V
           Fixed 5V / 3A                     2A max
                  │                                 │
          ┌───────┴──────────┐              [12V Display /
          │                  │               12V Fan /
        RPi 4            PMS5003             Optional Load]
     GPIO Pin 2/4        Pin 1 (VCC)
       (5V power)          (5V)
          │
    RPi internal
    3.3V regulator
          │
    ┌─────┴──────────┐
   SCD30          BME280
  (3.3V I2C)     (3.3V I2C)
```

---

### 2.3 — LM2596S-5.0 Wiring (Step DOWN — 11.1V → 5V)

**Module appearance:**

```
  ┌───────────────────────────────────────────────┐
  │           LM2596S-5.0 MODULE                  │
  │   (Fixed 5V output — no pot to adjust)        │
  │                                               │
  │  ┌──────┐         ┌──────┐                   │
  │  │ IN+  │  ◄────  │ OUT+ │  ────►            │
  │  │ IN−  │  ◄────  │ OUT− │  ────►            │
  │  └──────┘         └──────┘                   │
  │                                               │
  │  [Inductor]  [LM2596S chip]  [Capacitors]    │
  │                          ⚠ FIXED 5V — no pot  │
  └───────────────────────────────────────────────┘
```

**Connections:**

```
  BATTERY PACK                LM2596S-5.0 MODULE
  ┌──────────┐                ┌──────────────────┐
  │          │                │                  │
  │  (+) RED ●────────────────● IN+              │
  │          │                │                  │
  │  (−) BLK ●────────────────● IN−              │
  │          │                │                  │
  └──────────┘                │  OUT+ ●──────────┼──► 5V RAIL (RED)
                              │                  │
                              │  OUT− ●──────────┼──► GND RAIL (BLACK)
                              └──────────────────┘

  5V RAIL connects to:
    → RPi 4  Pin 2 (5V)  ← powers the entire RPi
    → RPi 4  Pin 6 (GND)
    → PMS5003 Pin 1 (VCC 5V)
    → PMS5003 Pin 2 (GND)
```

**LM2596S-5.0 Specification:**

| Parameter | Value |
|-----------|-------|
| Input voltage | 8V – 40V |
| Output voltage | **Fixed 5.0V** |
| Output current | 3A max (2A continuous recommended) |
| Efficiency | ~85% at 11V in, 5V out, 1.5A load |
| Package | TO-263-5L on PCB module |
| Operating temp | −40°C to +125°C |

> **⚠ Important:** The LM2596S chip gets **hot** under load. Ensure airflow or attach a small heatsink. Touch-test after 10 min — if too hot to touch, add heatsink.

> **⚠ Verify 5V output with a multimeter before connecting to RPi.** A wrong voltage (even 5.5V) can damage the RPi 4.

---

### 2.4 — MT3608 Wiring (Step UP — 11.1V → 12V for display/fan)

**Module appearance:**

```
  ┌───────────────────────────────────────────────┐
  │              MT3608 MODULE                    │
  │         (Adjustable boost converter)          │
  │                                               │
  │  ┌──────┐    [Pot]     ┌──────┐              │
  │  │ IN+  │  ◄────  ┌────┤ OUT+ │  ────►       │
  │  │ IN−  │  ◄────  │    │ OUT− │  ────►       │
  │  └──────┘         │    └──────┘              │
  │                   │                           │
  │              Turn CW to increase voltage      │
  │              Turn CCW to decrease voltage     │
  └───────────────────────────────────────────────┘
```

**Setting Output Voltage (do this BEFORE connecting load):**

```
  Step 1: Connect battery to MT3608 IN+ and IN−
  Step 2: Measure OUT+ to OUT− with multimeter
  Step 3: Turn the small blue potentiometer screw:
            Clockwise  ──► increases output voltage
            Counter-CW ──► decreases output voltage
  Step 4: Set to 12.0V (for display) or your required voltage
  Step 5: Disconnect multimeter, connect your load
```

**Connections:**

```
  BATTERY PACK                MT3608 MODULE
  ┌──────────┐                ┌──────────────────┐
  │          │                │                  │
  │  (+) RED ●────────────────● IN+              │
  │          │                │                  │
  │  (−) BLK ●────────────────● IN−              │
  │          │                │                  │
  └──────────┘                │  OUT+ ●──────────┼──► 12V+ to display/fan
                              │                  │
                              │  OUT− ●──────────┼──► GND to display/fan
                              └──────────────────┘
```

**MT3608 Specification:**

| Parameter | Value |
|-----------|-------|
| Input voltage | 2V – 24V |
| Output voltage | Adjustable up to 28V |
| Output current | **2A max** |
| Switching frequency | 1.2 MHz |
| Efficiency | ~93% typical |

> **⚠ Do NOT draw more than 2A from MT3608.** A 7-inch HDMI display typically draws ~500mA at 12V — well within limits.

> **⚠ Always set output voltage FIRST with a multimeter before connecting any load.**

---

### 2.5 — Complete Power Wiring with Safety Components

```
  ┌──────────────────────────────────────────────────────────────┐
  │                  FULL POWER SCHEMATIC                        │
  └──────────────────────────────────────────────────────────────┘

  BATTERY(+) ──RED──► [SWITCH] ──► [5A FUSE] ──┬────► LM2596S IN+
                                                │
                                                └────► MT3608  IN+

  BATTERY(−) ──BLK──────────────────────────────┬────► LM2596S IN−
                                                │
                                                └────► MT3608  IN−

  LM2596S OUT+ ──RED 5V──┬──────────────────────────► RPi 4  Pin 2  (5V)
                          └──────────────────────────► PMS5003 Pin1  (VCC 5V)

  LM2596S OUT− ──BLK GND─┬──────────────────────────► RPi 4  Pin 6  (GND)
                          └──────────────────────────► PMS5003 Pin2  (GND)

  MT3608  OUT+ ──RED 12V─────────────────────────────► Display (+)
  MT3608  OUT− ──BLK GND─────────────────────────────► Display (−)

  RPi 4 Pin 1 (3.3V) ──────────────────────────────► SCD30  VCC
                                                       BME280 VCC
                                                       BME280 CSB
  RPi 4 Pin 6 (GND)  ──────────────────────────────► SCD30  GND
                                                       SCD30  SEL
                                                       BME280 GND
                                                       BME280 SDO
```

---

### 2.6 — Battery Runtime Estimate

System power consumption:

| Component | Voltage | Current | Power |
|-----------|---------|---------|-------|
| Raspberry Pi 4 (typical load) | 5V | 1.2A | 6.0W |
| PMS5003 | 5V | 0.1A | 0.5W |
| SCD30 | 3.3V | 0.02A | 0.07W |
| BME280 | 3.3V | 0.001A | 0.003W |
| **Total at 5V rail** | **5V** | **~1.32A** | **~6.6W** |
| LM2596S conversion loss (~85% eff.) | — | — | +1.0W |
| **Total from battery** | **11.1V** | **~0.7A** | **~7.6W** |

**Estimated runtime:**

```
  Battery energy   = 11.1V × 5.0Ah = 55.5 Wh
  System draw      = ~7.6W (RPi + sensors only, no display)
  Runtime estimate = 55.5 ÷ 7.6 = ~7.3 hours theoretical
  Practical runtime = ~5–6 hours (accounting for BMS cutoff + aging)

  With 12V display (5W extra via MT3608):
  Total draw      = ~13W
  Runtime         = 55.5 ÷ 13 = ~4.3 hours
  Practical       = ~3–3.5 hours
```

---

### 2.7 — Power Safety Checklist

Before powering on for the first time:

```
  □  Fuse installed between battery (+) and converters
  □  Switch wired on battery (+) line
  □  LM2596S output measured at 5.0V with multimeter (nothing connected)
  □  MT3608 output set to desired voltage (12V for display)
  □  All GND connections common (battery −, LM2596S OUT−, RPi GND)
  □  RPi NOT connected to USB-C charger while powered from GPIO (never both!)
  □  LM2596S module has airflow or heatsink
  □  Battery pack BMS protection is active (check datasheet)
  □  No bare wire ends touching metal case or each other
```

> **⚠ NEVER power the RPi 4 from both USB-C AND GPIO Pin 2 at the same time.** This creates a voltage conflict and can damage the RPi.

---

## 3. Raspberry Pi 4 — GPIO Pinout Reference

This is the RPi 4 header as viewed from above (USB ports facing down).

```
                    ┌──────────────────────────────────┐
                    │         RASPBERRY PI 4 B         │
                    │   (USB ports at bottom, HDMI right)│
                    └──────────────────────────────────┘

  LEFT SIDE (odd pins)              RIGHT SIDE (even pins)
  ┌──────────────────────────────────────────────────────┐
  │ Pin  1 │ 3.3V  ●══● 5.0V  │ Pin  2 │  ← 5V POWER  │
  │ Pin  3 │ SDA1  ●══● 5.0V  │ Pin  4 │              │
  │ Pin  5 │ SCL1  ●══● GND   │ Pin  6 │  ← GROUND    │
  │ Pin  7 │ GPIO4 ●══● UART0TX│ Pin  8 │              │
  │ Pin  9 │ GND   ●══● UART0RX│ Pin 10 │              │
  │ Pin 11 │ GPIO17●══● GPIO18│ Pin 12 │              │
  │ Pin 13 │ GPIO27●══● GND   │ Pin 14 │              │
  │ Pin 15 │ GPIO22●══● GPIO23│ Pin 16 │              │
  │ Pin 17 │ 3.3V  ●══● GPIO24│ Pin 18 │              │
  │ Pin 19 │ MOSI  ●══● GND   │ Pin 20 │              │
  │ Pin 21 │ MISO  ●══● GPIO25│ Pin 22 │              │
  │ Pin 23 │ SCLK  ●══● GPIO8 │ Pin 24 │ ← UART2 TX  │
  │ Pin 25 │ GND   ●══● GPIO7 │ Pin 26 │              │
  │ Pin 27 │ ID_SD ●══● ID_SC │ Pin 28 │              │
  │ Pin 29 │ GPIO5 ●══● GND   │ Pin 30 │              │
  │ Pin 31 │ GPIO6 ●══● GPIO12│ Pin 32 │              │
  │ Pin 33 │ GPIO13●══● GND   │ Pin 34 │              │
  │ Pin 35 │ GPIO19●══● GPIO16│ Pin 36 │              │
  │ Pin 37 │ GPIO26●══● GPIO20│ Pin 38 │              │
  │ Pin 39 │ GND   ●══● GPIO21│ Pin 40 │              │
  └──────────────────────────────────────────────────────┘
```

### Pins Used by This Project

```
  ┌──────────────────────────────────────────────────────┐
  │                   PINS USED                          │
  │                                                      │
  │ Pin  1  │  3.3V      │ SCD30 VCC, BME280 VCC+CSB   │
  │ Pin  2  │  5.0V      │ PMS5003 VCC                  │
  │ Pin  3  │  GPIO2/SDA │ SCD30 SDA + BME280 SDA (I2C) │
  │ Pin  5  │  GPIO3/SCL │ SCD30 SCL + BME280 SCL (I2C) │
  │ Pin  6  │  GND       │ SCD30 GND, SCD30 SEL,        │
  │         │            │ BME280 GND, BME280 SDO        │
  │ Pin  8  │  GPIO14    │ UART0 TXD0 → PMS5003 RX      │
  │ Pin  9  │  GND       │ PMS5003 GND                  │
  │ Pin 10  │  GPIO15    │ UART0 RXD0 ← PMS5003 TX      │
  │ Pin 11  │  GPIO17    │ PMS5003 SET (HIGH=active)    │
  │ Pin 13  │  GPIO27    │ PMS5003 RESET (HIGH=normal)  │
  └──────────────────────────────────────────────────────┘
```

---

## 4. Sensor 1 — SCD30 Wiring

**Sensirion SCD30** measures CO₂, Temperature, and Humidity over I2C at address **0x61**.

### SCD30 Pin Layout

```
  ┌─────────────────────────────────┐
  │         SENSIRION SCD30         │
  │   (top view, cable facing you)  │
  │                                 │
  │  ┌─────┬─────┬─────┬─────┬─────┤
  │  │ VCC │ GND │ SDA │ SCL │ SEL │
  │  └──┬──┴──┬──┴──┬──┴──┬──┴──┬──┘
  │     │     │     │     │     │
  └─────┼─────┼─────┼─────┼─────┘
        │     │     │     │
      3.3V   GND   SDA   SCL  → also connect SEL to GND!
```

### SCD30 → Raspberry Pi 4 Connection

```
  SCD30 SENSOR              RASPBERRY PI 4
  ┌───────────┐             ┌─────────────┐
  │           │             │             │
  │  VCC  ●──┼─────RED─────┼── Pin 1  (3.3V)    │
  │           │             │             │
  │  GND  ●──┼────BLACK────┼── Pin 6  (GND)     │
  │           │             │             │
  │  SDA  ●──┼────BLUE─────┼── Pin 3  (GPIO2/SDA1)│
  │           │             │             │
  │  SCL  ●──┼────YELLOW───┼── Pin 5  (GPIO3/SCL1)│
  │           │             │             │
  │  SEL  ●──┼────BLACK────┼── Pin 6  (GND)  ⚠️ MUST!│
  │           │             │             │
  │  nRDY ●  │  (leave unconnected)       │
  └───────────┘             └─────────────┘
```

### SCD30 Wiring Table

| SCD30 Pin | Wire Color | RPi Pin | RPi Function | Critical? |
|-----------|-----------|---------|--------------|-----------|
| VCC | Red | Pin 1 | 3.3V | Yes — **3.3V only, never 5V** |
| GND | Black | Pin 6 | GND | Yes |
| SDA | Blue | Pin 3 | GPIO2 / SDA1 | Yes |
| SCL | Yellow | Pin 5 | GPIO3 / SCL1 | Yes |
| SEL | Black | Pin 6 | GND | **Yes — must be tied LOW for I2C mode** |
| nRDY | — | — | Not connected | Leave floating |

> **IMPORTANT:** The SCD30 SEL pin selects communication mode. Tie it to GND to use I2C. If left floating, the sensor may use UART and will not respond on I2C.

> **IMPORTANT:** The SCD30 requires the I2C bus slowed to **10 kHz** (not the default 100 kHz). This is configured in Step 9.

---

## 5. Sensor 2 — BME280 Wiring

**Bosch BME280** measures Barometric Pressure, Temperature, and Humidity over I2C at address **0x76**.

### BME280 Breakout Pin Layout

```
  ┌──────────────────────────────────────┐
  │           BME280 BREAKOUT            │
  │       (Adafruit or generic)          │
  │                                      │
  │  ┌─────┬─────┬─────┬─────┬─────┬────┤
  │  │ VIN │ GND │ SCK │ SDI │ SDO │ CS │
  │  │     │     │(SCL)│(SDA)│(ADR)│    │
  │  └──┬──┴──┬──┴──┬──┴──┬──┴──┬──┴──┬─┘
         │     │     │     │     │     │
       3.3V  GND   SCL   SDA   GND  3.3V
                               (→0x76) (I2C mode)
```

> Different breakout brands label pins differently. Common labels: VIN/VCC/3V3, GND, SCK/SCL, SDI/SDA, SDO/ADDR, CS/CSB.

### BME280 → Raspberry Pi 4 Connection

```
  BME280 SENSOR             RASPBERRY PI 4
  ┌───────────┐             ┌─────────────┐
  │           │             │             │
  │  VIN  ●──┼─────RED─────┼── Pin 1  (3.3V)    │
  │  (VCC)    │             │             │
  │  GND  ●──┼────BLACK────┼── Pin 6  (GND)     │
  │           │             │             │
  │  SDI  ●──┼────BLUE─────┼── Pin 3  (GPIO2/SDA1)│ ← shares with SCD30
  │  (SDA)    │             │             │
  │  SCK  ●──┼────YELLOW───┼── Pin 5  (GPIO3/SCL1)│ ← shares with SCD30
  │  (SCL)    │             │             │
  │  SDO  ●──┼────BLACK────┼── Pin 6  (GND)  → sets address 0x76│
  │  (ADDR)   │             │             │
  │  CS   ●──┼─────RED─────┼── Pin 1  (3.3V) → selects I2C mode│
  │  (CSB)    │             │             │
  └───────────┘             └─────────────┘
```

### BME280 Wiring Table

| BME280 Pin | Wire Color | RPi Pin | RPi Function | Critical? |
|------------|-----------|---------|--------------|-----------|
| VIN / VCC / 3V3 | Red | Pin 1 | 3.3V | Yes |
| GND | Black | Pin 6 | GND | Yes |
| SDI / SDA | Blue | Pin 3 | GPIO2 / SDA1 | Yes — shares bus with SCD30 |
| SCK / SCL | Yellow | Pin 5 | GPIO3 / SCL1 | Yes — shares bus with SCD30 |
| SDO / ADDR | Black | Pin 6 | GND | **Yes — sets I2C address to 0x76** |
| CS / CSB | Red | Pin 1 | 3.3V | **Yes — selects I2C mode (not SPI)** |

> **NOTE:** SCD30 and BME280 share the same SDA (Pin 3) and SCL (Pin 5). This is normal — I2C supports multiple devices on one bus.

---

## 6. Sensor 3 — PMS5003 Wiring

**Plantower PMS5003** measures PM1.0, PM2.5, PM10 particulate matter over UART0 serial (GPIO14/GPIO15).

### PMS5003 Pin Layout

The PMS5003 comes with a ZH1.25mm 8-pin flat cable. The cable's red wire (Pin 1) is on the side closest to the sensor's laser lens.

```
  PMS5003 (front view, connector on bottom)
  ┌─────────────────────────────────────────┐
  │  ╔══════════════════════════════════╗   │
  │  ║          LASER SENSOR            ║   │
  │  ║         (do not block)           ║   │
  │  ╚══════════════════════════════════╝   │
  │  AIR IN ──────────────────── AIR OUT   │
  └────────────────┬────────────────────────┘
                   │
          ZH1.25mm CABLE (8 pins)
          Pin numbering (left to right):

    ┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
    │  1  │  2  │  3  │  4  │  5  │  6  │  7  │  8  │
    │ VCC │ GND │ SET │ RX  │ TX  │RESET│ NC  │ NC  │
    └─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
      RED  BLK  WHT  YEL  GRN  BLU  —    —
      5V   GND  ON   RX   TX  RESET unused
```

### PMS5003 → Raspberry Pi 4 Connection

```
  PMS5003 SENSOR            RASPBERRY PI 4
  ┌───────────┐             ┌─────────────┐
  │           │             │             │
  │ Pin1 VCC●─┼─────RED─────┼── Pin 2  (5V)  ← MUST be 5V │
  │           │             │             │
  │ Pin2 GND●─┼────BLACK────┼── Pin 9  (GND)  │
  │           │             │             │
  │ Pin3 SET●─┼────WHITE────┼── Pin 11 (GPIO17) HIGH=active │
  │           │             │             │
  │  Pin4 RX●─┼────YELLOW───┼── Pin 8  (GPIO14/UART0 TXD0) │
  │           │             │      ↑ RPi TRANSMITS → Sensor RECEIVES │
  │  Pin5 TX●─┼────GREEN────┼── Pin 10 (GPIO15/UART0 RXD0) │
  │           │             │      ↑ Sensor TRANSMITS → RPi RECEIVES │
  │ Pin6 RST●─┼────BLUE─────┼── Pin 13 (GPIO27) HIGH=normal │
  │           │             │             │
  │ Pin7  NC  │  (not connected)          │
  │ Pin8  NC  │  (not connected)          │
  └───────────┘             └─────────────┘
```

### PMS5003 Wiring Table

| PMS5003 Pin | Label | Wire Color | RPi Pin | RPi Function | Critical? |
|-------------|-------|-----------|---------|--------------|-----------|
| 1 | VCC | Red | Pin 2 | **5V** | Yes — **must be 5V, NOT 3.3V** |
| 2 | GND | Black | Pin 9 | GND | Yes |
| 3 | SET | White | Pin 11 | GPIO17 | Yes — must be HIGH to enable sensor |
| 4 | RX | Yellow | **Pin 8** | **GPIO14 / UART0 TXD0** | Yes — **CROSSED: RPi TX → Sensor RX** |
| 5 | TX | Green | **Pin 10** | **GPIO15 / UART0 RXD0** | Yes — **CROSSED: Sensor TX → RPi RX** |
| 6 | RESET | Blue | Pin 13 | GPIO27 | Yes — must be HIGH for normal operation |
| 7 | NC | — | — | Not connected | — |
| 8 | NC | — | — | Not connected | — |

> **CRITICAL:** RX and TX are **crossed**. The PMS5003's TX (what it sends out) connects to the RPi's RX (what it reads in), and vice versa. Getting this backwards is the most common PMS5003 wiring mistake.

> **CRITICAL:** The PMS5003 needs **5V power** (Pin 2 on RPi). Running it on 3.3V will give no output or corrupted frames.

---

## 7. Complete Wiring — All 3 Sensors + Power Together

### Overview Diagram

```
╔══════════════════════════════════════════════════════════════════╗
║               RASPBERRY PI 4 MODEL B                           ║
║                  GPIO HEADER (top view)                        ║
╠═══════════════════════════════════════════════════════╦═════════╣
║  Pin 1  [3.3V ] ●══════════════════════╗             ║         ║
║  Pin 2  [5.0V ] ●════════════════════╗ ║             ║  USB    ║
║  Pin 3  [SDA1 ] ●══════════════════╗ ║ ║             ║  PORTS  ║
║  Pin 4  [5.0V ]                    ║ ║ ║             ║         ║
║  Pin 5  [SCL1 ] ●════════════════╗ ║ ║ ║             ╠═════════╣
║  Pin 6  [GND  ] ●══════════════╗ ║ ║ ║ ║             ║         ║
║  Pin 7  [GPIO4]                ║ ║ ║ ║ ║             ║  ETH    ║
║  Pin 8  [TX0  ] ●════════════╗ ║ ║ ║ ║ ║  ← UART0 TX ║         ║
║  Pin 9  [GND  ] ●══════════╗ ║ ║ ║ ║ ║ ║             ╠═════════╣
║  Pin 10 [RX0  ] ●════════╗ ║ ║ ║ ║ ║ ║ ║  ← UART0 RX ║         ║
║  Pin 11 [GPIO17]●════════╗ ║ ║ ║ ║ ║ ║ ║             ║  HDMI   ║
║  Pin 12 [GPIO18]           ║ ║ ║ ║ ║ ║ ║             ║         ║
║  Pin 13 [GPIO27]●══════╗ ║ ║ ║ ║ ║ ║ ║             ╚═════════╣
║  Pin 14 [GND  ]        ║ ║ ║ ║ ║ ║ ║ ║                       ║
║  Pin 15 [GPIO22]       ║ ║ ║ ║ ║ ║ ║ ║                       ║
║  Pin 16 [GPIO23]       ║ ║ ║ ║ ║ ║ ║ ║                       ║
║  Pin 17 [3.3V ]        ║ ║ ║ ║ ║ ║ ║ ║                       ║
║  Pin 18 [GPIO24]       ║ ║ ║ ║ ║ ║ ║ ║                       ║
║  Pin 19 [MOSI ]        ║ ║ ║ ║ ║ ║ ║ ║                       ║
║  Pin 20 [GND  ]        ║ ║ ║ ║ ║ ║ ║ ║                       ║
║  Pin 21 [MISO ]        ║ ║ ║ ║ ║ ║ ║ ║                       ║
║  Pin 22 [GPIO25]       ║ ║ ║ ║ ║ ║ ║ ║                       ║
║  Pin 23 [SCLK ]        ║ ║ ║ ║ ║ ║ ║ ║                       ║
║  Pin 24 [GPIO8]        ║ ║ ║ ║ ║ ║ ║ ║                       ║
╚═══════════════════╪════╪═╪═╪═╪═╪═╪═╪═╪═╝                     ║
                    ║    ║ ║ ║ ║ ║ ║ ║ ║
            UART0TX ╝    ║ ║ ║ ║ ║ ║ ║ ╚══════ SCD30 VCC (3.3V)
            UART0RX ─────╝ ║ ║ ║ ║ ║ ║ ╚══════╗ BME280 VCC
                           ║ ║ ║ ║ ║ ║         ╠═ BME280 CSB
                           ║ ║ ║ ║ ║ ╚═════════╝
                           ║ ║ ║ ║ ╚═══════════ PMS5003 GND
                           ║ ║ ║ ╚═════════════ SCD30 GND
                  GPIO27 ──╝ ║ ║                SCD30 SEL (→GND)
                             ║ ║                BME280 GND
                  GPIO17 ────╝ ║                BME280 SDO (→GND)
                               ╚═════════════── PMS5003 SET
```

### Simplified Wiring Map

```
RPi 4 Pin          Wire           Destination
─────────────────────────────────────────────────────
Pin 1  (3.3V) ────RED──────────┬─ SCD30  VCC
                                ├─ BME280 VCC
                                └─ BME280 CSB (HIGH = I2C mode)

Pin 2  (5V)   ────RED──────────── PMS5003 Pin1 (VCC)

Pin 3  (SDA1) ────BLUE─────────┬─ SCD30  SDA
                                └─ BME280 SDA (SDI)

Pin 5  (SCL1) ────YELLOW───────┬─ SCD30  SCL
                                └─ BME280 SCL (SCK)

Pin 6  (GND)  ────BLACK────────┬─ SCD30  GND
                                ├─ SCD30  SEL  ← I2C mode select
                                ├─ BME280 GND
                                └─ BME280 SDO  ← sets address 0x76

Pin  8 (UART0TX)──YELLOW────────── PMS5003 Pin4 (RX)   RPi→sensor

Pin  9 (GND)  ────BLACK────────── PMS5003 Pin2 (GND)

Pin 10 (UART0RX)──GREEN─────────── PMS5003 Pin5 (TX)   sensor→RPi

Pin 11 (GPIO17)───WHITE─────────── PMS5003 Pin3 (SET)  = HIGH enable

Pin 13 (GPIO27)───BLUE──────────── PMS5003 Pin6 (RESET) = HIGH normal
─────────────────────────────────────────────────────
```

### Breadboard Layout (Recommended)

Using a mini breadboard makes the I2C shared connections clean:

```
                    MINI BREADBOARD
  ┌─────────────────────────────────────────────┐
  │  + rail (3.3V from Pin 1) ──────────────────│── RED
  │  - rail (GND   from Pin 6) ─────────────────│── BLACK
  │                                              │
  │  Row A:  SCD30  SDA ──┬── BME280 SDA        │
  │          (all to Pin 3 via Blue wire)        │
  │                        │                    │
  │  Row B:  SCD30  SCL ──┴── BME280 SCL        │
  │          (all to Pin 5 via Yellow wire)      │
  └─────────────────────────────────────────────┘
```

---

## 8. Flash Raspberry Pi OS

### Step 8.1 — Download Raspberry Pi Imager

Go to: **https://www.raspberrypi.com/software/**
Download and install the Imager for your PC (Windows/Mac/Linux).

### Step 8.2 — Write the OS

1. Insert microSD card into your PC
2. Open Raspberry Pi Imager
3. Click **"CHOOSE DEVICE"** → Select **Raspberry Pi 4**
4. Click **"CHOOSE OS"** → **Raspberry Pi OS Lite (64-bit)** (Bookworm)
   - "Lite" = no desktop, saves RAM for sensors
5. Click **"CHOOSE STORAGE"** → Select your microSD card
6. Click the **⚙ gear icon** (Advanced Options) and set:

```
  ┌─────────────────────────────────────────────┐
  │          ADVANCED OPTIONS                   │
  │                                             │
  │  ☑ Set hostname:     ot-monitor             │
  │  ☑ Enable SSH:       Use password auth      │
  │  ☑ Set username:     msa                    │
  │     Set password:    (choose a strong one)  │
  │  ☑ Configure WiFi:   (your SSID + password) │
  │  ☑ Set locale:                              │
  │     Timezone:        Asia/Kolkata           │
  │     Keyboard:        gb                     │
  └─────────────────────────────────────────────┘
```

7. Click **Save**, then **Write** and confirm
8. Wait for writing + verification to complete (~5 min)
9. Eject the card safely

---

## 9. First Boot & System Update

### Step 8.1 — Power On

1. Insert microSD into Raspberry Pi 4
2. Connect Ethernet cable (recommended over WiFi for setup)
3. Connect USB-C power supply
4. Wait **90 seconds** for first boot

### Step 8.2 — Connect via SSH

**From Windows (PowerShell or Command Prompt):**
```powershell
ssh msa@ot-monitor.local
```

If `ot-monitor.local` doesn't resolve, find the IP from your router's DHCP list, then:
```powershell
ssh msa@192.168.x.x
```

Type `yes` to accept the fingerprint, then enter your password.

### Step 8.3 — Update Everything

```bash
sudo apt update && sudo apt full-upgrade -y
sudo reboot
```

SSH back in after ~60 seconds.

---

## 10. Enable I2C & UART0 Interfaces

### Step 9.1 — Enable I2C via raspi-config

```bash
sudo raspi-config
```

Navigate through the menus:
```
  Interface Options
    └── I2C
          └── Would you like the ARM I2C interface enabled? → YES
                └── OK → Finish
```

### Step 9.2 — Disable Serial Login Shell (free UART0 for PMS5003)

Still inside `raspi-config`, navigate:
```
  Interface Options
    └── Serial Port
          ├── "Would you like a login shell to be accessible over the serial port?" → NO
          └── "Would you like the serial port hardware to be enabled?" → YES
```

Select **Finish** and let it reboot, or continue to the next step and reboot once at the end.

### Step 9.3 — Edit Boot Config File

This disables Bluetooth (to free UART0 for GPIO14/15), enables PL011 on GPIO14/15, and slows I2C to 10 kHz (required for SCD30).

```bash
sudo nano /boot/firmware/config.txt
```

> **Note:** On older RPi OS (Bullseye or earlier), the path is `/boot/config.txt`

Scroll to the very **bottom** of the file and add these lines:

```ini
# ── OT Monitor sensor config ───────────────────────────────
# Slow I2C bus to 10 kHz — required for SCD30 clock stretching
dtparam=i2c_arm_baudrate=10000

# Disable Bluetooth — frees UART0 (PL011) for GPIO14/GPIO15
# Required so PMS5003 can use /dev/serial0 on Pin 8 (TXD0) and Pin 10 (RXD0)
dtoverlay=disable-bt

# Enable hardware UART (PL011) on GPIO14/GPIO15
enable_uart=1
```

Save the file: `Ctrl+O` → `Enter` → `Ctrl+X`

> **Why disable Bluetooth?** On RPi 4, Bluetooth occupies the full PL011 UART (UART0) which is connected to GPIO14/15 by default. `dtoverlay=disable-bt` detaches Bluetooth and gives PMS5003 exclusive access to the reliable PL011 hardware UART. Bluetooth is not needed for this embedded OT monitoring application.

### Step 9.4 — Reboot

```bash
sudo reboot
```

SSH back in after reboot.

### Step 9.5 — Add User to Required Groups

This allows the `msa` user to access I2C and UART without `sudo`:

```bash
sudo usermod -a -G dialout,i2c msa
sudo reboot
```

SSH back in after reboot.

---

## 11. Verify Wiring with Software

Before installing any Python libraries, verify the hardware is correctly wired.

### Step 10.1 — Install I2C Tools

```bash
sudo apt install -y i2c-tools
```

### Step 10.2 — Scan I2C Bus

```bash
i2cdetect -y 1
```

### Expected Output

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

| You See | Meaning | If Missing |
|---------|---------|-----------|
| `61` at position 0x61 | SCD30 detected ✓ | Check SDA/SCL wires; confirm SEL→GND |
| `76` at position 0x76 | BME280 detected ✓ | Check SDO→GND and CSB→3.3V |

### Step 10.3 — Verify UART0 for PMS5003

```bash
ls -la /dev/serial0
ls -la /dev/ttyAMA0
```

Expected:
```
lrwxrwxrwx 1 root root    7 Jun 21 12:00 /dev/serial0 -> ttyAMA0
crw-rw---- 1 root dialout 204, 64 Jun 21 12:00 /dev/ttyAMA0
```

`/dev/serial0` must be a symlink pointing to `ttyAMA0` (the full PL011 UART).

If `/dev/serial0` points to `ttyS0` instead → `dtoverlay=disable-bt` or `enable_uart=1` is missing from config.txt.

**Confirm Bluetooth is detached:**
```bash
sudo systemctl status hciuart
```
Expected: `inactive (dead)` — Bluetooth is off. This is correct for our use case.

**Stop here if `/dev/serial0` → `ttyAMA0` is not confirmed. Fix config.txt and reboot first.**

---

## 12. Install Python Dependencies

### Step 11.1 — Install System Packages

```bash
sudo apt install -y python3-pip python3-venv git
```

### Step 11.2 — Clone the Repository

```bash
cd ~/Desktop
git clone https://github.com/MSA5896/OT_Monitor_Dashboard.git ot_monitor
cd ~/Desktop/ot_monitor/backend
```

### Step 11.3 — Create Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

Your prompt should now show `(venv)` prefix.

### Step 11.4 — Install All Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip

# Backend server dependencies
pip install -r requirements.txt

# Raspberry Pi hardware sensor libraries
pip install -r requirements-rpi.txt
```

What `requirements-rpi.txt` installs:

```
  smbus2                         — I2C bus access for scanning
  adafruit-blinka                — CircuitPython hardware layer for Linux/RPi
  adafruit-circuitpython-scd30   — SCD30 CO₂ sensor driver
  adafruit-circuitpython-bme280  — BME280 pressure sensor driver
  (pyserial already in requirements.txt) — PMS5003 UART driver
```

### Step 11.5 — Verify Installation

```bash
python3 -c "
import board
import busio
import adafruit_scd30
import adafruit_bme280.advanced
import serial
import smbus2
print('All sensor libraries OK')
"
```

Expected: `All sensor libraries OK`

If any import fails, install that specific library manually:

```bash
pip install adafruit-blinka adafruit-circuitpython-scd30 adafruit-circuitpython-bme280 pyserial smbus2
```

---

## 13. Clone & Configure the Project

### Step 12.1 — Verify Project Structure

```bash
ls ~/Desktop/ot_monitor/backend/
```

Expected output:
```
alarm_engine.py  app_state.py  auth.py  config.py
data_model.py    data_sources/ main.py  requirements.txt
requirements-rpi.txt  sensors/  storage.py  data/
```

```bash
ls ~/Desktop/ot_monitor/backend/sensors/
```

Expected:
```
__init__.py        bme280_driver.py   mhz19_driver.py
pms5003_driver.py  scd30_driver.py    sdp810_driver.py
test_sensors.py
```

---

## 14. Test All Sensors

Run the built-in test script from the **backend** directory.

```bash
cd ~/Desktop/ot_monitor/backend
source venv/bin/activate

# Test all sensors at once
python -m sensors.test_sensors
```

> **Important:** Always run from `backend/` using `python -m sensors.test_sensors`.
> Do **NOT** `cd sensors/` and run `python test_sensors.py` — this causes `No module named 'sensors'` error.

### Individual Sensor Tests

```bash
# SCD30 only
python -m sensors.test_sensors --sensor scd30

# BME280 only
python -m sensors.test_sensors --sensor bme280

# PMS5003 only
python -m sensors.test_sensors --sensor pms5003

# I2C scan only
python -m sensors.test_sensors --sensor i2c

# Continuous live readings (Ctrl+C to stop)
python -m sensors.test_sensors --loop --interval 2
```

### Expected Output — All Pass

```
OT Environment Monitoring System — Sensor Hardware Test
  Date/Time : 2026-06-21 21:30:00 IST
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
  Waiting for first measurement (up to 15 seconds)…
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
  Waiting for first frame (up to 3 seconds)…
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

**Do not go to Step 14 until all three sensors show PASS.**

---

## 15. Switch to Hardware Mode

```bash
nano ~/Desktop/ot_monitor/config/config.yaml
```

Make these changes:

### 14.1 — Change Data Source

```yaml
data_source:
  type: hardware        # ← change from: simulator
```

### 14.2 — Allow Network Access to Dashboard

```yaml
server:
  host: "0.0.0.0"      # ← change from: 127.0.0.1
  port: 8001
```

### 14.3 — Generate a Secure Session Secret

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and paste it into config:

```yaml
auth:
  session_secret: "paste-your-generated-secret-here"
```

### 14.4 — Change Default Passwords

```yaml
auth:
  users:
    - username: "admin"
      password: "YourStrongAdminPassword"
      role: "admin"
    - username: "nurse"
      password: "YourStrongNursePassword"
      role: "viewer"
```

### 14.5 — Hardware Settings (optional tweaks)

```yaml
hardware_source:
  scd30_measurement_interval_s: 2    # seconds between CO₂ readings (min 2)
  scd30_temperature_offset_c: 0.0    # increase if SCD30 reads higher than reference thermometer
  bme280_i2c_address: 0x76           # change to 0x77 if you wired SDO to 3.3V instead
  pms_port: "/dev/ttyAMA1"           # UART2 port — should not change on RPi 4
  poll_interval_s: 2.0               # how often all sensors are polled
```

Save: `Ctrl+O` → `Enter` → `Ctrl+X`

---

## 16. Run the Backend

### Manual Start (test mode)

```bash
cd ~/Desktop/ot_monitor/backend
source venv/bin/activate
python main.py
```

You should see:

```
12:00:01  INFO  SCD30 ready — CO₂, Temperature, Humidity
12:00:01  INFO  BME280 ready — Barometric Pressure
12:00:01  INFO  PMS5003 ready — PM1.0 / PM2.5 / PM10
12:00:01  INFO  HardwareSource started — 3 sensors (SCD30 + BME280 + PMS5003), polling every 2.0 s
12:00:01  INFO  OT Monitor backend started ✓  (ot_id=OT-01, source=hardware)
```

Open in browser: **http://ot-monitor.local:8001/**

Press `Ctrl+C` to stop.

---

## 17. Autostart on Boot (systemd)

Runs the backend automatically whenever the Pi powers on.

### Step 16.1 — Create the Service File

```bash
sudo nano /etc/systemd/system/ot-monitor.service
```

Paste exactly:

```ini
[Unit]
Description=OT Infection Monitor Backend
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=msa
WorkingDirectory=/home/msa/Desktop/ot_monitor/backend
ExecStart=/home/msa/Desktop/ot_monitor/backend/venv/bin/python main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Save: `Ctrl+O` → `Enter` → `Ctrl+X`

### Step 16.2 — Enable and Start

```bash
sudo systemctl daemon-reload
sudo systemctl enable ot-monitor
sudo systemctl start ot-monitor
```

### Step 16.3 — Verify

```bash
sudo systemctl status ot-monitor
```

Expected:
```
● ot-monitor.service — OT Infection Monitor Backend
     Loaded: loaded (/etc/systemd/system/ot-monitor.service; enabled)
     Active: active (running) since Sat 2026-06-21 12:00:00 IST; 5s ago
```

### Useful Commands

```bash
sudo journalctl -u ot-monitor -f          # live logs
sudo journalctl -u ot-monitor -n 50       # last 50 lines
sudo systemctl restart ot-monitor         # restart after config changes
sudo systemctl stop ot-monitor            # stop service
sudo systemctl disable ot-monitor         # remove from autostart
```

---

## 18. Access the Dashboard

### Find the RPi's IP

```bash
hostname -I
```

### Open Dashboard

From **any browser on the same WiFi/LAN**:

```
http://ot-monitor.local:8001/
```

Or by IP address:

```
http://192.168.x.x:8001/
```

### Login

| Role | Username | Password |
|------|----------|----------|
| Admin (full access) | `admin` | `OTAdmin2024` (change this!) |
| Viewer (monitor only) | `nurse` | `OTNurse2024` (change this!) |

### Set a Static IP (Recommended)

So the dashboard URL never changes:

```bash
sudo nano /etc/dhcpcd.conf
```

Add at the bottom:

```
interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 8.8.4.4
```

```bash
sudo systemctl restart dhcpcd
```

Dashboard will always be at `http://192.168.1.100:8001/`

---

## 19. Troubleshooting Guide

### Error: `No module named 'sensors'`

```
Cause:  Running test_sensors.py from inside the sensors/ folder.

Wrong:
  cd ~/Desktop/ot_monitor/backend/sensors
  python3 test_sensors.py               ← FAILS

Correct:
  cd ~/Desktop/ot_monitor/backend
  python -m sensors.test_sensors        ← WORKS
```

---

### I2C shows nothing — no devices found

```bash
i2cdetect -y 1
# All dashes, no 61 or 76
```

| Check | Command |
|-------|---------|
| Is I2C enabled? | `sudo raspi-config` → Interface Options → I2C → should be enabled |
| Is i2c-arm in config? | `grep i2c /boot/firmware/config.txt` |
| Did you reboot? | `sudo reboot` after changing config.txt |
| Check physical wires | SDA = Pin 3, SCL = Pin 5, GND = Pin 6 |

---

### SCD30 missing (0x61 not shown)

```
Likely causes:
  1. SEL pin is NOT connected to GND  ← most common
  2. VCC wired to 5V instead of 3.3V
  3. SDA or SCL wire loose

Fix:
  - Power off RPi
  - Confirm SCD30 SEL → RPi Pin 6 (GND)
  - Confirm SCD30 VCC → RPi Pin 1 (3.3V)
  - Re-seat SDA and SCL wires
  - Power on and run i2cdetect -y 1
```

---

### BME280 missing (0x76 not shown)

```
Likely causes:
  1. SDO pin is NOT connected (address floats, not 0x76)
  2. CSB pin is NOT connected to 3.3V (SPI mode instead of I2C)
  3. Sharing bus wrong — SDA/SCL wires not joined to SCD30

Fix:
  - Confirm BME280 SDO → RPi Pin 6 (GND)   → address 0x76
  - Confirm BME280 CSB → RPi Pin 1 (3.3V)   → I2C mode
  - Both SDA wires (SCD30 + BME280) must connect to Pin 3
  - Both SCL wires (SCD30 + BME280) must connect to Pin 5
```

---

### SCD30 timeout / CRC errors

```
Cause: I2C bus speed too fast. SCD30 uses clock stretching and requires 10 kHz.

Verify /boot/firmware/config.txt contains:
  dtparam=i2c_arm_baudrate=10000

Check:
  grep baudrate /boot/firmware/config.txt

If missing, add it and reboot.
```

---

### PMS5003 timeout — no frame received

```
Likely causes:
  1. TX and RX wires are swapped  ← most common
  2. VCC on 3.3V instead of 5V
  3. dtoverlay=uart2 missing from config.txt
  4. /dev/ttyAMA1 doesn't exist

Fix step by step:
  1. ls /dev/ttyAMA1            (must exist)
  2. grep uart2 /boot/firmware/config.txt   (must be present)
  3. Check PMS5003 VCC → RPi Pin 2 (5V), NOT Pin 1 (3.3V)
  4. Check RX/TX cross:
     PMS5003 Pin5 TX → RPi Pin21 (UART2 RX)
     PMS5003 Pin4 RX → RPi Pin24 (UART2 TX)
```

---

### `Permission denied` on `/dev/ttyAMA1`

```bash
sudo usermod -a -G dialout pi
sudo reboot
```

---

### Sensor libraries not installing

```bash
# Check you're in the venv
which python          # should show .../venv/bin/python

# Install manually
pip install adafruit-blinka
pip install adafruit-circuitpython-scd30
pip install adafruit-circuitpython-bme280
pip install pyserial smbus2

# Verify
python3 -c "import board; print(board.SCL)"
```

---

### Quick Full System Health Check

Run all of these at once:

```bash
echo "=== Service Status ==="
sudo systemctl status ot-monitor --no-pager

echo "=== Last 20 Log Lines ==="
sudo journalctl -u ot-monitor -n 20 --no-pager

echo "=== I2C Scan ==="
i2cdetect -y 1

echo "=== UART2 Port ==="
ls -la /dev/ttyAMA1

echo "=== Sensor Test ==="
cd ~/Desktop/ot_monitor/backend && source venv/bin/activate
python -m sensors.test_sensors
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│                    OT MONITOR — QUICK REF                   │
├─────────────────────┬───────────────────────────────────────┤
│ Dashboard URL       │ http://ot-monitor.local:8001/         │
│ Admin login         │ admin / OTAdmin2024                   │
│ Viewer login        │ nurse / OTNurse2024                   │
├─────────────────────┼───────────────────────────────────────┤
│ SCD30 I2C address   │ 0x61  (fixed)                        │
│ BME280 I2C address  │ 0x76  (SDO → GND)                    │
│ PMS5003 UART port   │ /dev/ttyAMA1                         │
│ I2C bus speed       │ 10,000 Hz (10 kHz)                   │
│ SCD30 warmup        │ ~10–15 seconds                        │
├─────────────────────┼───────────────────────────────────────┤
│ Run sensor test     │ python -m sensors.test_sensors        │
│                     │ (from backend/ directory)             │
│ View live logs      │ sudo journalctl -u ot-monitor -f      │
│ Restart backend     │ sudo systemctl restart ot-monitor     │
│ Config file         │ ~/Desktop/ot_monitor/config/config.yaml│
├─────────────────────┼───────────────────────────────────────┤
│ I2C verify          │ i2cdetect -y 1                       │
│ UART verify         │ ls /dev/ttyAMA1                      │
│ Group membership    │ groups msa  (must include dialout,i2c) │
└─────────────────────┴───────────────────────────────────────┘
```

---

*Last updated: June 2026 — Verified on Raspberry Pi 4 Model B (4GB) + RPi OS Bookworm 64-bit*
*Sensors: Sensirion SCD30 rev.2 + Bosch BME280 + Plantower PMS5003*
