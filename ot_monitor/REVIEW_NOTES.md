# OT Monitor — Dashboard Redesign · Review Notes

**Date:** 2026-06-22
**For:** review when you're back. I worked autonomously (you were out and couldn't give yes/no),
made the best, most defensible choices, and listed every decision + open question below.
Nothing destructive was done; all changes are in version control and easy to adjust.

---

## 1. What you asked for → what I did

| # | Your requirement (Requirement.txt) | Status | Notes |
|---|------------------------------------|--------|-------|
| 1 | Two windows: a public monitor view + an admin settings view | ✅ Done | Nav has **Monitor** and **Settings**. Settings is admin-gated. |
| 2 | Designed for 9.7" / iPad Air 2 display (the device panel size) | ✅ Done | Layout targets **1024×768 logical (4:3)**. Dev window set to this size (`windows/runner/main.cpp`). |
| 3 | Lightweight, **no scrollable window** on the monitor | ✅ Done | Monitor screen is a fixed, no-scroll layout that always fits the screen (computed with LayoutBuilder). |
| 4 | Cards + live graph; **slider data NOT in main window**; graph full width; cards smaller, two rows | ✅ Done | 8 parameter cards in **2 rows × 4**, smaller height; **live graph spans full width** below them. The detailed per-sensor "slider" view moved to **Settings → Sensors**. |
| 5 | Nav bug: showed two selected. Want only **Monitor + Settings**; Settings opens **admin login popup**; after login, more options appear | ✅ Done | Fixed. Only Monitor + Settings show by default. Clicking Settings opens a login dialog; after admin sign-in, **Alarms** and **History** appear (admin-only). |
| 6 | **Battery in the top**, not in a card | ✅ Done | Battery % + power source (Mains/Battery) now shown in the **header**, colour-coded. Battery card removed. |
| 7 | Nurse/steward selects from a **list of critical locations**; admin can **add locations** | ✅ Done (UI) | Monitor has a location selector; admin manages locations in **Settings → Locations**. ⚠️ See "Open items #1" about live data per location. |
| 8 | Left nav **hidden**, appears **above** the monitor (overlay) without resizing it | ✅ Done | Nav is hidden by default and opens as a **floating overlay** from the header menu (☰); it does not resize the monitor content. (You said to keep a nav for now — this is the overlay version you described.) |
| 9 | Background not plain white — an **appealing bluish gradient**; logo is bluish | ✅ Done | Replaced flat white with a **soft bluish gradient** + a faint logo watermark. Accent colour shifted to **clinical blue** to match your (bluish) logo. |
| 10 | Use **real medical software** UI conventions, not generic AI design; follow ISO/FDA/IEC | ✅ Researched + applied | Grounded in real ICU monitors (Philips IntelliVue, GE CARESCAPE) and OR environmental systems (STERIS SONICU). See "Compliance" below. |

---

## 2. Design decisions I made for you (and why)

- **Colour = clinical blue + IEC alarm colours.** Real ICU monitors standardise on
  **IEC 60601‑1‑8**: red = critical, amber = warning, green = normal, cyan = info/fault.
  I kept these exactly (clinicians are trained on them) and made the *brand/UI* colour a
  calm blue to match your logo. Strong colours are reserved only for alarms.
- **No-scroll layout via proportional sizing.** The monitor screen divides the available
  height between the card grid (~46%) and the graph, so it always fits 1024×768 without
  scrolling — and adapts if the panel size changes slightly.
- **Battery thresholds (header colour):** green ≥50%, amber 20–49%, red <20% (standard UPS
  convention). This is a device-health metric, not a medical threshold.
- **Admin gating:** anything beyond the public Monitor (Settings, Alarms, History) requires
  an admin login. Default credentials (from the backend `config.yaml`):
  - admin / `OTAdmin2024`  (full access)
  - nurse / `OTNurse2024`  (viewer)
  **➡ Change these before real deployment** (see Compliance).
- **Locations persist locally** (on the panel) for now — admins can add OT-02, ICU-01, etc.

---

## 3. RESOLVED since first draft

- ✅ **Architecture: one backend per panel** (your call, 2026-06-22). Implemented: each critical
  location now carries its **own backend host + port**. Selecting a location on the Monitor
  screen **reconnects the live WebSocket/REST to that location's backend**, so each location's
  data is fully segregated and easy to diagnose. Admins set a location's host/port in
  **Settings → Locations → Add**. The default `OT-01` points at `localhost:8001`.
  - *To use across the hospital:* run the backend on each panel/RPi, then add a location per
    panel with that panel's IP (e.g. `OT-02` → `192.168.1.23:8001`). The viewer switches between
    them from the Monitor location dropdown.
- ✅ **Logo integrated.** The MSA Intelligent Healthcare logo (`docs/LOGO.png` → `assets/logo.png`)
  now appears in the header, the admin login dialog, and as a faint background watermark.

## 4. OPEN ITEMS — still need your input

1. **Nav style for production.** You said "for now keep the nav, we'll change it later." I built
   the **overlay** version you described (hidden, opens above content). If you'd prefer a
   permanent slim rail for now instead, say the word — it's a 10-minute change.

2. **Threshold editing.** Admins can currently *view* the safe/warning/alarm zones (Settings →
   Sensors). Letting admins *edit* thresholds live (the backend already supports it) is easy to
   add — confirm you want per-location editable thresholds and I'll wire it up.

3. **The "small robot" subsystem** (maintenance of the critical location) — noted from your
   requirement. Not started; it's a separate module. Tell me when you want to scope it.

---

## 5. Compliance posture (ISO / FDA / IEC) — status & gaps

This is a **monitoring aid**; regulatory class depends on intended use claims. What's in place
vs. what still needs sign-off:

**Already followed**
- **IEC 60601‑1‑8** alarm colour semantics (red/amber/green/cyan) and clear priority labelling.
- At-a-glance, no-scroll display with large legible numerals (real-monitor convention).
- Role-based access (public view vs admin config) — matches healthcare dashboard practice.
- Audit-friendly backend: alarms logged with timestamp/parameter/value/acknowledgement; CSV export.
- Thresholds sourced from WHO 2021 AQG / ASHRAE 170 / NABH (documented in `config.yaml`).

**Gaps to close before clinical/production use (need your org's input)**
- **Change default passwords** and set a real `session_secret`; enable **TLS** (`config.yaml`).
- **Audible alarm** + alarm latching/escalation per IEC 60601‑1‑8 (currently visual only).
- **Intended-use statement + risk analysis (ISO 14971)** and, if marketed as a medical device,
  the relevant **FDA / CE / CDSCO** pathway. This needs your regulatory lead — I can prepare the
  technical documentation (alarm tables, data flow, threshold rationale) to support it.
- **IEC 62304** (software lifecycle) if it's classified as medical device software — needs a
  documented dev/test process. I've kept code modular + added unit tests as a starting point.

> I did **not** skip these — they require organisational/regulatory decisions, so I've flagged
> them rather than assume. Happy to draft the documentation for any of them.

---

## 6. How to preview it yourself

1. Start the backend (one time): in `ot_monitor/backend` run `python main.py` (serves on :8001).
2. Run the dashboard: in `ot_monitor/dashboard` run `flutter run -d windows`
   (or launch the built `build/windows/x64/runner/Debug/ot_monitor_dashboard.exe`).
3. Click the **☰ menu → Settings** → sign in as `admin` / `OTAdmin2024` to see Alarms, History,
   Sensors (slider view), and Locations.

A screenshot of the new monitor screen is in the PR. The window opens at the 9.7" panel size.

---

## 7. Where the code is

- All changes are committed and pushed (see the PR linked in chat). Key files:
  - Theme/gradient: `dashboard/lib/theme/app_theme.dart`, `dashboard/lib/widgets/app_background.dart`
  - Shell/nav/header/battery/login: `dashboard/lib/main.dart`
  - Monitor (no-scroll, cards + graph + location): `dashboard/lib/screens/dashboard_screen.dart`
  - Admin settings (sensors/locations/account): `dashboard/lib/screens/settings_screen.dart`
  - Locations model/persistence: `dashboard/lib/models/location.dart`, `dashboard/lib/services/locations_service.dart`

**Tell me your answers to the Open Items (esp. #1 and #3) and I'll continue.**
