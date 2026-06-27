# OT Monitor — Power Backup System Design
## Circuit Diagram · Component Assessment · Full Power & Backup Calculations

**Project:** OT Environment Monitoring System  
**Hardware:** Raspberry Pi 4 · BME280 · PMS5003 · SCD30 · SDP819 · 2× Fan · Buzzer  
**Document Version:** 2.0  
**Date:** 2026-06-21

---

## 1. System Architecture

The system operates as a mini-UPS (Uninterruptible Power Supply):

| State | What Happens |
|-------|-------------|
| **Main ON** | Wall adapter powers all loads AND charges the Li-Ion battery through MT3608 |
| **Main OFF** | Battery discharges through BMS → Schottky D2 → LM2596S → 5 V bus (zero-interruption switchover) |
| **Battery Full** | BMS cuts charge path at 12.6 V (4.2 V/cell); load continues from main |
| **Battery Empty** | BMS cuts discharge path at 9.0 V (3.0 V/cell); system powers off cleanly |

Switchover is **fully automatic and passive** — two Schottky diodes on the LM2596S input perform "diode-OR" power-path selection with no relay or MCU involved.

---

## 2. Component Roles

| # | Your Component | Role in This Design |
|---|---|---|
| 1 | **MT3608** 2 A DC-DC Boost | Boosts 12 V main → 12.6 V regulated CC/CV charging voltage for 3S Li-Ion |
| 2 | **LM2596S-5.0** Fixed 5 V Buck (TO-263-5L) | Steps down battery/main rail (9–40 V input) → stable 5.0 V for all loads |
| 3 | **INR 18650 3S2P** 11.1 V / 5000 mAh / 3C | Energy reservoir — backup power storage |

---

## 3. Full Circuit Diagram

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                  12 V DC WALL ADAPTER   (Recommended: 3.5 A / 42 W)         ║
╚══════════════════════════════╤═════════════════════════════════════════════════╝
                               │
                          [F1: FUSE 3 A]
                               │
              ┌────────────────┴─────────────────────────────────┐
              │ CHARGING PATH                      MAIN LOAD PATH │
              │                                                    │
        [MT3608 BOOST]                           [D1: 1N5822 Schottky]
        Vin  : 12 V                               Vf ≈ 0.45 V @ 1 A
        Vout : 12.6 V ◄── set trimpot                    │
        Iout : 2 A max                                    ▼
        Eff  : ~88 %                          ┌───────────────────────┐
              │                               │    LM2596S-5.0        │
              │ 12.6 V / ≤2 A                 │    DC-DC Buck         │
              ▼                               │    Vin  : 7–40 V      │
       ┌─────────────────┐                    │    Vout : 5.0 V fixed  │
       │   3S BMS MODULE │                    │    Iout : 3 A max      │
       │ ─────────────── │                    │    Eff  : ~82 %        │
       │  B+ ←── charge  │                    └──────────┬────────────┘
       │  B− ←── GND     │                               │
       │  OVP: 12.6 V    │                    [C1: 470 µF/25V] [C2: 220 µF/10V]
       │  UVP:  9.0 V    │                          (on LM2596S Vin & Vout)
       │  OCP + SCP      │                               │
       └────────┬────────┘                               │
                │                                        │
        ┌───────┴────────┐                               │
        │  3S2P BATTERY  │                               │
        │   11.1 V nom   │                               │
        │   5000 mAh     │                               │
        │   3C / 15 A    │                               │
        └───────┬────────┘                               │
                │ DISCHARGE PATH                         │
        [BMS DISCHARGE P+]                               │
                │                                        │
        [D2: 1N5822 Schottky]  ─────────────────────────┘
         Vf ≈ 0.45 V                  (joins LM2596S Vin rail)
```

```
                               ┌──────────────────────────────────────────────────────┐
                               │                  5 V POWER BUS                        │
                               └──┬──────────┬──────────┬──────────┬──────────┬────────┘
                                  │          │          │          │          │
                            ┌─────┴────┐ ┌──┴────┐ ┌──┴──────┐ ┌─┴────┐ ┌───┴────────┐
                            │  RPi 4   │ │PMS5003│ │ Fan 1   │ │Fan 2 │ │  BUZZER    │
                            │ Pin 2/4  │ │ VCC   │ │Suction  │ │Exhaust│ │  CIRCUIT   │
                            │  (5V)    │ │  5V   │ │  5V     │ │  5V  │ └───┬────────┘
                            └────┬─────┘ └──┬────┘ └─────────┘ └──────┘    │
                                 │ (3.3V)    │ (UART)                        │
                         ┌───────┴───────┐   └─────────► RPi UART0         [Buzzer Circuit]
                         │ I2C BUS       │               (/dev/serial0)
                         │ SDA GPIO2 (3) │
                         │ SCL GPIO3 (5) │
                         │               │
                    ┌────┴────┐ ┌────────┴──┐ ┌────────┐
                    │ BME280  │ │  SCD30    │ │ SDP819 │
                    │ 0x76    │ │  0x61     │ │ 0x25   │
                    │ 3.3V    │ │  3.3V     │ │ 3.3V   │
                    └─────────┘ └───────────┘ └────────┘
                   (All powered from RPi Pin 1 — 3.3V rail)
```

### 3.1 Diode-OR Automatic Switchover Logic

```
MAIN ON :  D1 conducts  →  12.0 V − 0.45 V = 11.55 V at LM2596S input
           Battery at   →  11.1 V − 0.45 V = 10.65 V at LM2596S input (D1 wins)
           Result: Main powers load; battery charges via MT3608 path.

MAIN OFF:  D1 blocked   →  Battery 11.1 V − 0.45 V = 10.65 V at LM2596S input (D2 conducts)
           Result: Battery powers load. Switchover is instantaneous.
           Both voltages are above LM2596S minimum (7 V). ✓
```

### 3.2 MT3608 Voltage Setting

Set the MT3608 trimpot so Vout = **12.60 V exactly**, measured with a multimeter at the BMS charge input, BEFORE connecting to the battery.

```
MT3608 formula:   Vout = 0.6 V × (1 + R1/R2)
For 12.6 V  →    R1/R2 = (12.6/0.6) − 1 = 20
If R2 = 10 kΩ    → R1 = 200 kΩ  (or adjust the onboard trimpot until Vout = 12.60 V)
```

### 3.3 Buzzer Drive Circuit (RPi GPIO → 5 V Buzzer)

RPi GPIO pins output 3.3 V max — insufficient to directly drive a 5 V active buzzer. Use an NPN transistor buffer:

```
RPi GPIO (any pin, e.g. GPIO18)
         │
        [R1: 1 kΩ]
         │
    ┌────┤ BC547 NPN (or 2N2222)  Base
    │    │
    │  Collector ──────────────────────── Buzzer (−) terminal
    │                                         │
    │  [D3: 1N4007 Flyback diode]        Buzzer (+) ──── 5 V Bus
    │   Cathode to 5 V, Anode to Collector
    │
   GND (Emitter)
```

> Configure GPIO18 as output in software. Set HIGH to trigger alarm, LOW to silence.

### 3.4 Fan Connections

```
5 V Bus (+) ────────────────────────┬────────────────────────────────┐
                                    │                                │
                              Fan 1 Red (+)                    Fan 2 Red (+)
                              (Suction / Intake)               (Exhaust)
                              Fan 1 Black (−)                  Fan 2 Black (−)
                                    │                                │
GND Bus (−) ────────────────────────┴────────────────────────────────┘

Yellow wire (tach/PWM) → RPi GPIO (optional, for RPM monitoring)
```

> For RPi GPIO fan speed control: replace direct connection with a N-channel MOSFET (IRLZ44N). Gate via 10 kΩ from GPIO. Allows PWM speed control to reduce noise and power when full airflow is not required.

---

## 4. Full Wiring Reference

```
12 V Adapter (+) ──[F1: 3 A Fuse]──┬──[MT3608 Vin+]    [MT3608 Vout+]──► BMS Charge B+
12 V Adapter (−) ──────────────────────────────────────────────────────────► BMS Charge B−, GND

                                    └──[D1: 1N5822 Anode]  [D1 Cathode]──► LM2596S Vin+

BMS Discharge P+ ──[D2: 1N5822 Anode]  [D2 Cathode]──► LM2596S Vin+   (same node as D1 cathode)
BMS Discharge P− ──► GND

LM2596S Vout+ ──[C1: 470µF]──[C2: 220µF]──────────────────────────────► 5 V Bus (+)
LM2596S Vout− ──────────────────────────────────────────────────────────► GND

5 V Bus (+) ──► RPi Pin 2 or Pin 4
5 V Bus (+) ──► PMS5003 Pin 1 (VCC)
5 V Bus (+) ──► Suction Fan Red wire (+)
5 V Bus (+) ──► Exhaust Fan Red wire (+)
5 V Bus (+) ──► Buzzer (+) terminal

GND Bus ──► RPi Pin 6 / 9 / 14 (any GND)
GND Bus ──► PMS5003 Pin 2 (GND)
GND Bus ──► Both Fan Black wires (−)
GND Bus ──► BC547 Emitter
GND Bus ──► Battery BMS B−

RPi Pin 1 (3.3V) ──► BME280 VCC, SCD30 VCC, SDP819 VDD
RPi Pin 3 (SDA)  ──► BME280 SDA, SCD30 SDA, SDP819 SDA
RPi Pin 5 (SCL)  ──► BME280 SCL, SCD30 SCL, SDP819 SCL
RPi Pin 6 (GND)  ──► BME280 GND, SCD30 GND, SDP819 GND

RPi GPIO18       ──► [1kΩ] ──► BC547 Base  (Buzzer control)
RPi GPIO14 (UART0 TX / Pin 8)  ──► PMS5003 RX (Pin 4)
RPi GPIO15 (UART0 RX / Pin 10) ◄── PMS5003 TX (Pin 5)
RPi GPIO17       ──► PMS5003 SET (Pin 3)   — pull HIGH to enable
RPi GPIO27       ──► PMS5003 RESET (Pin 6) — pull HIGH for normal
```

---

## 5. Sensor Power Specifications (Actual Hardware)

All I2C sensors (BME280, SCD30, SDP819) are powered from **RPi Pin 1 (3.3 V)**.  
PMS5003 is powered directly from **5 V Bus** (external, bypasses RPi).  
Buzzer and fans are on **5 V Bus** (external).

| Sensor / Device | Supply | Active Current | Avg Current | Notes / Source |
|-----------------|--------|---------------|-------------|---------------|
| **BME280** Temp · Humidity · Pressure | 3.3 V (RPi Pin 1) | 714 µA | ~4 µA | Forced mode; sleeping between reads. Bosch BST-BME280-DS002 |
| **SCD30** CO₂ · Temp · RH | 3.3 V (RPi Pin 1) | 75 mA peak | **19 mA avg** | NDIR CO₂ — peaks every 2 s measurement cycle. Sensirion SCD30 datasheet |
| **SDP819** Differential Pressure | 3.3 V (RPi Pin 1) | 3.3 mA | **3.3 mA** | Continuous measurement mode. Sensirion SDP8xx datasheet |
| **PMS5003** PM1.0 · PM2.5 · PM10 | 5 V direct | 100 mA | **100 mA** | Laser + internal fan always on. Plantower PMS5003 datasheet |
| **5 V Suction Fan** (40 mm axial) | 5 V direct | 200 mA | **200 mA** | Always running for air intake |
| **5 V Exhaust Fan** (40 mm axial) | 5 V direct | 200 mA | **200 mA** | Always running for air exhaust |
| **Alarm Buzzer** (active magnetic, 5 V) | 5 V via BC547 | 50 mA | 5 mA avg | 50 mA when alarming. ~10% duty in standby monitoring |
| **Status LEDs** (3×, various) | 5 V via 330 Ω | 20 mA | 20 mA | Power / Status / Alarm indicators |
| **Misc** (I2C pull-ups, decoupling) | 5 V | 15 mA | 15 mA | Pull-up resistors, passive circuits |

---

## 6. Complete Power Consumption Analysis

### 6.1 Referred-to-5V Calculation for 3.3 V Sensors

All 3.3 V sensors draw current through the Raspberry Pi's internal 3.3 V regulator (part of the BCM2711 PMIC). That extra current must be sourced from the 5 V bus:

```
Formula:
  I_5V = (V_sensor × I_sensor) / (V_5V × η_regulator)
  where η_regulator (RPi internal LDO) ≈ 88 %

BME280  → (3.3 × 0.004) / (5 × 0.88) = 0.003 mA   ← negligible
SCD30   → (3.3 × 19)    / (5 × 0.88) = 14.2  mA   referred to 5 V bus
SDP819  → (3.3 × 3.3)   / (5 × 0.88) =  2.5  mA   referred to 5 V bus
                          ──────────────────────────
Total sensor 3.3V burden on 5V bus: ≈ 16.7 mA
```

### 6.2 Per-Consumer Power Table

| Consumer | 5 V Bus Current | 5 V Bus Power | Path |
|----------|----------------|--------------|------|
| **Raspberry Pi 4** (CPU, RAM, WiFi, OS) | 700 mA | 3.500 W | RPi Pin 2/4 |
| **SCD30** CO₂ sensor burden on 5V | 14.2 mA | 0.071 W | Via RPi 3.3V regulator |
| **SDP819** Diff pressure burden on 5V | 2.5 mA | 0.013 W | Via RPi 3.3V regulator |
| **BME280** Pressure/Temp/RH burden | ~0 mA | ~0 W | Negligible (µA range) |
| **PMS5003** Particulate Matter sensor | 100 mA | 0.500 W | Direct 5V |
| **Suction Fan** (40 mm, 5V) | 200 mA | 1.000 W | Direct 5V |
| **Exhaust Fan** (40 mm, 5V) | 200 mA | 1.000 W | Direct 5V |
| **Buzzer** (standby, 10% avg duty) | 5 mA | 0.025 W | Via BC547, RPi GPIO18 |
| **Status LEDs** × 3 | 20 mA | 0.100 W | Direct 5V via 330 Ω |
| **Misc** (pull-ups, RC filters) | 15 mA | 0.075 W | Passive |
| **TOTAL — NORMAL OPERATION** | **1,257 mA** | **6.284 W** | |
| **TOTAL — ALARM STATE** (buzzer full on) | **1,302 mA** | **6.510 W** | |
| **TOTAL — FANS OFF** (power save mode) | **857 mA** | **4.284 W** | No fans |
| **TOTAL — 1 FAN ONLY** | **1,057 mA** | **5.284 W** | One fan |

### 6.3 Efficiency Chain (Battery → 5 V Bus)

```
Battery (11.1 V)
    │ BMS internal resistance: ~100 mΩ (negligible at 0.7 A)
    ▼
D2 Schottky 1N5822
    │ Vf = 0.45 V → Efficiency = (11.1 − 0.45) / 11.1 = 95.9 %
    ▼
LM2596S-5.0 Buck Converter
    │ η ≈ 82 % at 1.26 A output load (from TI LM2596 datasheet curve)
    ▼
5 V Bus (1,257 mA)

Overall efficiency: 0.959 × 0.82 = 78.6 %
```

### 6.4 Power Draw from Battery per Mode

```
                 5V Bus Power      Battery Draw       Battery Current
Normal:          6.284 W     /  0.786  =  7.993 W  ÷  11.1 V  = 720 mA
Alarm:           6.510 W     /  0.786  =  8.281 W  ÷  11.1 V  = 746 mA
Fans OFF:        4.284 W     /  0.786  =  5.451 W  ÷  11.1 V  = 491 mA
1 Fan only:      5.284 W     /  0.786  =  6.722 W  ÷  11.1 V  = 606 mA
```

---

## 7. Battery & Backup Time Calculations

### 7.1 Battery Energy Budget

| Parameter | Value | Calculation |
|-----------|-------|-------------|
| Cell chemistry | INR (Li-NMC) | 18650 form factor |
| Configuration | 3S2P | 3 series × 2 parallel |
| Nominal voltage | 11.1 V | 3.7 V × 3 |
| Full charge voltage | 12.6 V | 4.2 V × 3 |
| BMS cutoff (min) | 9.0 V | 3.0 V × 3 |
| Rated capacity | 5,000 mAh | 2,500 mAh/cell × 2 parallel |
| Gross energy | **55.5 Wh** | 11.1 V × 5.0 Ah |
| Usable energy (80 % DoD) | **44.4 Wh** | 55.5 × 0.80 |
| Max safe discharge (3C) | **15 A** | 5,000 mAh × 3C — your draw is 0.72 A (0.14C ← battery barely stressed) |

### 7.2 Backup Duration per Scenario

| Scenario | 5V Power | Battery Draw | **Backup Time** | Sensor Readings During Backup |
|----------|---------|-------------|-----------------|-------------------------------|
| **Fans OFF** (RPi + all 4 sensors only) | 4.284 W | 5.451 W | **8 h 08 min** | 29,280 per sensor |
| **1 Fan running** | 5.284 W | 6.722 W | **6 h 36 min** | 23,760 per sensor |
| **Normal — both fans ON** | 6.284 W | 7.993 W | **5 h 33 min** | 19,980 per sensor |
| **Alarm — fans + buzzer full** | 6.510 W | 8.281 W | **5 h 21 min** | 19,260 per sensor |

```
Formula: Backup Time = Usable Wh ÷ Battery Draw (W)
Example (Normal): 44.4 Wh ÷ 7.993 W = 5.56 h = 5 h 33 min

Sensor readings (1-second polling interval):
  5 h 33 min = 333 min × 60 = 19,980 seconds → 19,980 readings/sensor
  × 4 sensors (BME280, SCD30, SDP819, PMS5003) = 79,920 total data points stored
```

### 7.3 Low-Battery Warning Threshold

Configure a software alert when battery voltage at BMS P+ falls below **10.2 V** (3.4 V/cell). This gives approximately **45 minutes** of remaining runtime in normal mode — enough time for the system to save data and notify maintenance.

---

## 8. Charging Analysis

### 8.1 MT3608 Charging Performance

| Parameter | Value |
|-----------|-------|
| MT3608 Vin | 12.0 V (from main adapter) |
| MT3608 Vout (set) | 12.6 V |
| MT3608 max output current | 2.0 A |
| Conversion efficiency | ~88 % |
| Effective charge current into battery | **1.76 A** (2 A × 0.88) |
| Charge rate (C-rate) | **0.35 C** (safe: Li-Ion range 0.2 C – 1 C) |
| Time to full charge (empty → full) | **(5,000 mAh ÷ 1,760 mA) × 1.15 = 3 h 16 min** |
| 1.15× accounts for | CC → CV taper (current reduces near 12.6 V cutoff) |

### 8.2 Simultaneous Load + Charge (Main ON)

```
MT3608 input draw:  (12.6 V × 2 A) ÷ (12 V × 0.88) = 2.39 A from 12 V
LM2596S input draw: 6.284 W ÷ (12 V × 0.85)         = 0.62 A from 12 V
─────────────────────────────────────────────────────────────────────────
Total from 12 V adapter:  2.39 + 0.62 = 3.01 A

Recommended adapter:  12 V / 3.5 A (42 W)  [adds 16 % headroom]
```

---

## 9. Component Sufficiency Assessment

### ✅ LM2596S-5.0 — SUFFICIENT

- Rated 3 A output → your normal load is **1.26 A** (42 % of capacity, well within limits)
- Input range 7–40 V covers: battery min 9 V, full-charge 12.6 V, and main 12 V ✓
- Fixed 5 V variant eliminates adjustment — no drift over temperature ✓

### ⚠️ MT3608 2 A Boost — SUFFICIENT WITH LIMITATION

- Correctly used as a 12 V → 12.6 V boost to set exact Li-Ion charging voltage ✓
- 2 A output → 1.76 A effective charge current (0.35 C rate) — slow but safe ✓
- **Critical gap:** MT3608 is a voltage converter only — it has NO built-in constant-current (CC) charging control. Without CC limiting, on a fully discharged battery the inrush could exceed 2 A and damage the module.
- **Minimum mitigation:** Add a 0.33 Ω / 2 W current-sense resistor in series with the charge line. This limits inrush and lets BMS OCP provide backup protection.
- **Recommended upgrade:** Replace MT3608 charging path with a **CN3722** or **TP5100** 3S dedicated charger module (₹100–150). True CC/CV with LED status, automatic cutoff — far safer.

### ✅ 3S2P INR 18650 5000 mAh — EXCELLENT CHOICE

- Your actual discharge: **0.14 C** (720 mA ÷ 5000 mAh) — battery is barely stressed
- 3C rating means 15 A peak safe — you are 20× below that
- Expected cycle life at 0.14 C, 80 % DoD: **500–800 full charge cycles** (≈ 4–7 years if discharged once a week)
- **Must have 3S BMS** — see below

### ❌ 3S BMS Module — MISSING (MANDATORY FOR SAFETY)

A Li-Ion pack without a BMS is a fire and explosion hazard. Required protections:

| Protection | Without BMS Risk |
|-----------|-----------------|
| Over-voltage (>4.2 V/cell) | Cell swelling → thermal runaway |
| Under-voltage (<3.0 V/cell) | Permanent capacity loss |
| Short-circuit | High-current fire risk |
| Cell imbalance | Cells drift → premature aging |

**Recommended:** HW-357 3S 40 A BMS module or DW01+FS8205A equivalent rated ≥ 5 A continuous.

### ❌ Schottky Diodes — MISSING (MANDATORY for switchover)

The auto-failover circuit is incomplete without 2× 1N5822 (or SS34 SMD, 3 A/40 V).

### ❌ 12 V DC Adapter — MISSING

Need a **12 V / 3.5 A** (42 W) wall adapter. A standard 12 V / 2 A adapter will work for running only (no charging simultaneously).

### ⚠️ Buzzer — NEEDS TRANSISTOR BUFFER

RPi GPIO max 16 mA per pin (3.3 V). A 5 V magnetic buzzer draws 50 mA at 5 V. Direct GPIO connection will damage the RPi GPIO pin. Use a BC547 NPN transistor + 1 kΩ base resistor + 1N4007 flyback diode as shown in Section 3.3.

### ⚠️ Fans — VERIFY 5V COMPATIBILITY

Confirm your fans are rated for 5 V operation. If they are 12 V fans, connect them directly to the 12 V main input (not the 5 V bus) and recalculate accordingly. 12 V fans draw less current (~100–150 mA each at 12 V) — **in that case, deduct 400 mA from the 5 V bus total**.

---

## 10. Additional Components Required

| Priority | Item | Qty | Approx Cost |
|----------|------|-----|-------------|
| **CRITICAL** | 3S Li-Ion BMS module, ≥ 5 A discharge (e.g. HW-357) | 1 | ₹100–150 |
| **CRITICAL** | 1N5822 Schottky diode (3 A, 40 V, DO-201AD) | 2 | ₹15–20 each |
| **CRITICAL** | 12 V / 3.5 A DC adapter (barrel connector) | 1 | ₹350–500 |
| **CRITICAL** | Inline blade fuse holder + 3 A fuse | 1 | ₹30–50 |
| **Required** | BC547 NPN transistor | 1 | ₹5 |
| **Required** | 1N4007 diode (buzzer flyback) | 1 | ₹3 |
| **Required** | 1 kΩ resistor (buzzer base) | 1 | ₹1 |
| **Required** | 330 Ω resistors (LED current limiting) | 3 | ₹1 each |
| Recommended | 0.33 Ω / 2 W resistor (charge current limiter) | 1 | ₹10 |
| Recommended | 470 µF / 25 V electrolytic capacitor (LM2596S input) | 1 | ₹10 |
| Recommended | 220 µF / 10 V electrolytic capacitor (LM2596S output) | 1 | ₹8 |
| Optional | CN3722 or TP5100 3S dedicated charger module (replaces MT3608 for charging) | 1 | ₹100–150 |
| Optional | 4-digit voltmeter display 0–30 V (battery SOC indicator) | 1 | ₹80–120 |
| Optional | IRLZ44N N-MOSFET (fan PWM speed control from RPi GPIO) | 2 | ₹25 each |

**Estimated total for missing critical parts: ₹550–800**

---

## 11. Power Scenarios Summary (Quick Reference)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    POWER BUDGET QUICK REFERENCE                      │
├──────────────┬──────────────┬─────────────┬─────────────────────────┤
│ Mode         │ 5V Bus Draw  │ Battery Draw│ Backup Time              │
├──────────────┼──────────────┼─────────────┼─────────────────────────┤
│ Fans OFF     │ 857 mA/4.28W │  5.45 W     │ 8 h 08 min              │
│ 1 Fan        │1057 mA/5.28W │  6.72 W     │ 6 h 36 min              │
│ Normal       │1257 mA/6.28W │  7.99 W     │ 5 h 33 min  ◄ TYPICAL   │
│ Alarm State  │1302 mA/6.51W │  8.28 W     │ 5 h 21 min              │
├──────────────┼──────────────┼─────────────┼─────────────────────────┤
│ Main adapter │     —        │ charging    │ 12V / 3.5A recommended   │
│ Charge time  │     —        │ 3h 16min    │ empty → full via MT3608  │
└──────────────┴──────────────┴─────────────┴─────────────────────────┘

Battery: 3S2P INR 18650 · 11.1 V · 5000 mAh · 55.5 Wh · 44.4 Wh usable
LM2596S efficiency: 82%    Schottky loss: 4%    Combined: 78.6%
```

---

## 12. Safety Checklist Before Power-On

- [ ] MT3608 output set to **exactly 12.60 V** (measure with multimeter before BMS/battery connection)
- [ ] D1 and D2 Schottky diodes oriented correctly (band/stripe = cathode = towards LM2596S)
- [ ] BMS module wired: B+ from battery positive, B− from battery negative, C+ to MT3608 output, P+ to D2 anode, P− to GND
- [ ] 3 A fuse in line on 12 V positive before any splitting
- [ ] BC547 buzzer circuit wired with flyback diode (1N4007 cathode to 5 V bus, anode to collector)
- [ ] Fan polarity confirmed (Red = +, Black = −); do not reverse
- [ ] I2C sensors: all four SDA/SCL lines on same bus (RPi Pin 3/5), separate 3.3 V power from RPi Pin 1
- [ ] Verify at first power-on: LM2596S output is 5.00 V ± 0.1 V
- [ ] Verify battery charges: BMS C+ voltage rises toward 12.6 V with adapter connected
