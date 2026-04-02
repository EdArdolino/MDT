# Motorola MDT 9100-T — Mobile Data Terminal Emulator

> **A software emulator of the Motorola MDT 9100-T police Mobile Data Terminal, built for the Saugus Police Department's restored 1989 Ford Crown Victoria LTD — Car 12, Northwest Beat.**

![Python](https://img.shields.io/badge/Python-3.7%2B-informational?logo=python&logoColor=white&color=FFB000&labelColor=0D0800)
![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi%20%7C%20Linux%20%7C%20Windows-informational?color=FFB000&labelColor=0D0800)
![Dependencies](https://img.shields.io/badge/Dependencies-None%20%28stdlib%20only%29-informational?color=FFB000&labelColor=0D0800)
![License](https://img.shields.io/badge/License-MIT-informational?color=FFB000&labelColor=0D0800)

---

## Overview

This project emulates the **Motorola MDT 9100-T**, the mobile data terminal widely deployed in police cruisers throughout the 1980s and early 1990s. It was built as part of a full restoration of a **1989 Ford Crown Victoria LTD** for the **Saugus Police Department** in Saugus, Massachusetts.

The restored cruiser is designated **Car 12**, patrolling the **Northwest Beat** — covering Lynn Fells Parkway, Penobscot Road, Mountview Road, the Oaklandvale neighborhood, and the Breakheart Reservation area.

The emulator runs entirely in Python using the standard library (`tkinter`) — no pip installs, no external dependencies. It runs on a **Raspberry Pi** mounted behind the dash or on any Windows PC.

---

## Features

### Display & Aesthetics
- Authentic **amber phosphor** CRT look (switchable to **green phosphor**)
- Monospace terminal font with period-correct styling
- CRT scanline color, glow border, and hardware bezel framing
- Motorola branding bar with agency name and terminal serial number

### Demo Mode — Full Scripted Call Scenario
The highlight of the emulator: a fully automated, **step-by-step call scenario** that walks through an entire real-world MDT workflow:

```
Dispatch assigns call → CAR-12 ACKs → 10-76 En Route →
Dispatch sends supplemental → 10-97 On Scene →
NCIC plate query → warrant hit →
NCIC person query → officer advises dispatch →
Backup requested → prisoner secured →
10-98 Clear → Assignment closed → 10-8 In Service
```

The demo scenario is set in the Northwest Beat and features a **suspicious vehicle call on Lynn Fells Pkwy at Penobscot Road**, a NCIC return with an active Essex Superior Court warrant, and a full arrest and transport sequence.

**Demo is configurable:**
- `"DEMO_MODE": True` — runs automatically after boot (after a configurable delay)
- `"DEMO_MODE": False` — disables auto-start; demo still available via `DEMO` command
- `"DEMO_DELAY": 5` — seconds after boot before auto-demo begins
- `"DEMO_STEP_MS": 4000` — milliseconds between each scenario step

### Boot Sequence
Full **hardware self-test sequence** — ROM checksum, 32K RAM test, display controller, modem/radio link, NCIC/CAD network — all with typed-out delays matching real hardware.

### Dispatch / CAD Simulation
- Automatic simulated CAD calls arrive on a configurable timer
- Priority 1/2/3 calls with appropriate alert behaviour
- Direct unit assignments requiring `ACK` acknowledgement
- Blinking alert indicator for unread priority messages
- Locations drawn from real northwest Saugus streets and landmarks

### NCIC / CJIS Queries
- **Plate/vehicle query** (`F2` or `PLATE MA/5RVW441`) — year/make/model, VIN, registration status, owner with North Shore address, wants/warrants, stolen vehicle flag
- **Person/DL query** (`F3` or `PERSON MORIARTY`) — physical description, license status, prior record, active warrants
- Simulated network delay for realism
- Caution alerts flash on wants/warrants or stolen vehicle hits

### Unit Status Management
- Full 10-code status system (10-8, 10-7, 10-6, 10-76, 10-97, 10-98, 10-19, 10-33)
- Quick-set function keys
- `F12` / **EMERGENCY button** broadcasts 10-33 with timestamp

---

## Requirements

| Requirement | Detail |
|---|---|
| Python | 3.7 or newer |
| Tkinter | Included with Python on Windows; `python3-tk` on Linux/Raspberry Pi |
| OS | Raspberry Pi OS, any Linux desktop, Windows 7+ |
| External packages | **None** — standard library only |

---

## Installation

### Raspberry Pi (recommended for in-car use)

```bash
# Install dependencies
sudo apt-get update
sudo apt-get install python3 python3-tk

# Run the emulator
python3 mdt_emulator.py
```

**Full-screen kiosk mode** (recommended for a mounted dash display):
```bash
# Edit CONFIG at top of file:
"FULLSCREEN": True

# Or set the display and launch directly:
DISPLAY=:0 python3 mdt_emulator.py
```

**Auto-start on boot** — edit `/etc/rc.local` and add before `exit 0`:
```bash
DISPLAY=:0 /home/pi/launch_mdt.sh &
```

The included `launch_mdt.sh` handles screen blanking, watchdog restart, and display setup.

### Windows

```cmd
python mdt_emulator.py
```
Tkinter is included with the standard Python Windows installer. No additional packages needed.

---

## Configuration

All settings live in the `CONFIG` dictionary at the top of `mdt_emulator.py`:

```python
CONFIG = {
    # Unit identity
    "AGENCY":            "SAUGUS PD",
    "UNIT_ID":           "CAR-12",        # Car 12 — Northwest Beat
    "BEAT":              "BEAT NW",        # Northwest Saugus patrol area
    "CHANNEL":           "CH-1 PRIMARY",
    "FREQ":              "460.125",        # MHz
    "TERMINAL_ID":       "MDT-9100T-0042",
    "CAD_SERVER":        "DISPATCH-1",

    # Display
    "PHOSPHOR":          "amber",          # "amber" or "green"
    # Set FULLSCREEN to True for Raspberry Pi kiosk / in-car use.
    # Press Escape to exit fullscreen back to a window at any time.
    "FULLSCREEN":        False,
    "WINDOW_W":          900,             # Ignored in fullscreen mode
    "WINDOW_H":          640,             # Ignored in fullscreen mode
    "SOUND":             True,

    # Background dispatch simulation
    "AUTO_DISPATCH":     True,
    "DISPATCH_INTERVAL": 45,              # Seconds between simulated calls

    # Off Duty / shutdown
    # When True, the OFF DUTY button requires a second press within 3 seconds
    # to confirm before the program exits. Set False to exit on first press.
    "CONFIRM_OFF_DUTY":  True,

    # Raspberry Pi screen preset — set True for the Hosyond 5" 800×480 DSI display
    # (or any similar small screen). Automatically enables fullscreen and scales
    # all fonts, padding, and UI elements to fit the display. Overrides FULLSCREEN,
    # WINDOW_W, and WINDOW_H.
    "PI_SCREEN":         False,

    # Demo mode
    "DEMO_MODE":         True,            # Auto-run scenario after boot
    "DEMO_DELAY":        5,               # Seconds after boot before demo starts
    "DEMO_STEP_MS":      4000,            # Milliseconds between demo steps
}
```

---

## Raspberry Pi Screen Setup (Hosyond 5" 800×480 DSI)

This emulator was designed and tested for the **Hosyond 5-inch IPS MIPI DSI display** (800×480, capacitive touch, driver-free). One config change is all that's needed:

```python
"PI_SCREEN": True
```

This single setting:
- Enables fullscreen automatically (fills the 800×480 display edge-to-edge)
- Scales all fonts down proportionally (11pt → 8pt, header 12pt → 9pt, etc.)
- Scales all padding and widget sizes to fit the smaller canvas
- Keeps the full 12-key function bar, EMER button, and OFF DUTY button visible

### Auto-scaling

The emulator computes a **scale factor** at startup based on the actual screen resolution vs. the reference design (900×640):

```
scale = min(screen_width / 900, screen_height / 640)
```

| Display | Resolution | Scale | Fonts (main / header / key) |
|---|---|---|---|
| Hosyond 5" DSI *(this screen)* | 800 × 480 | **0.75** | 8pt / 9pt / 7pt |
| Default window | 900 × 640 | 1.00 | 11pt / 12pt / 9pt |
| 1080p monitor | 1920 × 1080 | 1.40 *(capped)* | 15pt / 16pt / 12pt |

The scale is clamped between 0.60 and 1.40 so fonts stay readable at any resolution.

### Wiring the DSI display to the Pi

The Hosyond display connects via the **DSI ribbon cable** — no HDMI needed, no drivers to install. Connect the ribbon cable to the Pi's DSI port, power up, and the display is detected automatically by Raspberry Pi OS.

### Recommended `/boot/config.txt` settings

On some Pi models the DSI display may need explicit configuration. Add to `/boot/config.txt` (or `/boot/firmware/config.txt` on Pi 5):

```ini
# Hosyond 5" 800×480 DSI display
display_auto_detect=1
```

If the display isn't detected automatically:
```ini
dtoverlay=vc4-kms-dsi-7inch
```

### Touch input

The capacitive touch layer works as a mouse input with no additional drivers on Raspberry Pi OS. Tap the function key buttons to activate them. For best results with the touch display, set:
```python
"PI_SCREEN":    True,
"DEMO_STEP_MS": 6000,   # Slightly slower demo pace — easier to read on 5"
```

---

## Full-Screen Mode

Set `"FULLSCREEN": True` in CONFIG to run the terminal in kiosk mode — no title bar, no window chrome, filling the entire display. This is the recommended setting for an in-car Raspberry Pi installation.

```python
"FULLSCREEN": True    # Fills the entire screen — best for in-car Pi use
"FULLSCREEN": False   # Windowed mode — best for development / desktop use
```

**Keyboard shortcuts for fullscreen:**

| Key | Action |
|---|---|
| `Escape` | Exit fullscreen → return to windowed mode |
| `Escape` *(in windowed mode)* | Return to Main Menu |

To re-enter fullscreen after pressing Escape, either restart the program or toggle the setting and relaunch.

---

## Off Duty — Shutdown

The **OFF DUTY** button is always visible in the top-right corner of the bezel. Pressing it broadcasts a **10-42 End of Tour** message, sets the unit status to **10-7 Out of Service**, and shuts the program down after a brief pause.

### Confirmation mode (default)

When `"CONFIRM_OFF_DUTY": True`, the button requires a second press within **3 seconds** to prevent accidental shutdown:

1. First press: button turns red and displays `CONFIRM?` — a 3-second countdown begins
2. Second press within 3 seconds: 10-42 is broadcast and the program exits
3. No second press / any other key typed: confirmation is cancelled, button resets

### Immediate mode

```python
"CONFIRM_OFF_DUTY": False   # Exits on first press with no confirmation
```

### Keyboard shortcut

`Ctrl+D` triggers Off Duty from the keyboard — useful when running in fullscreen without a mouse.

---

### What it demonstrates

The demo runs a complete, realistic call lifecycle for **Car 12 (Northwest Beat)**:

| Step | Event |
|---|---|
| 1 | Dispatch assigns **Suspicious Vehicle** — Lynn Fells Pkwy @ Penobscot Rd |
| 2 | CAR-12 sets **10-76 En Route**, sends ACK to dispatch |
| 3 | Dispatch transmits supplemental (occupant possibly intoxicated) |
| 4 | CAR-12 sets **10-97 On Scene**, advises of dark green van |
| 5 | NCIC plate query — **5RVW441 MA** — registered to Moriarty, Kevin P, Mountview Rd, Saugus |
| 6 | NCIC returns **DEFAULT WARRANT — Essex Superior Ct / A&B with Dangerous Weapon** |
| 7 | NCIC person query confirms warrant, expired DL, and significant prior record |
| 8 | CAR-12 advises dispatch of warrant hit, requests backup and tow (10-51) |
| 9 | Dispatch confirms warrant, sends CAR-9, notifies tow |
| 10 | CAR-12 advises prisoner secured, transporting to station |
| 11 | CAR-12 sets **10-98 Available**; dispatch closes incident, assigns to DET-1 |
| 12 | CAR-12 sets **10-8 In Service** |

### Enabling / disabling

```python
# Auto-runs after every boot:
"DEMO_MODE": True

# Disabled — but still available via DEMO command at any time:
"DEMO_MODE": False
```

### Adjusting playback speed

```python
"DEMO_STEP_MS": 2000    # Fast — good for quick run-throughs
"DEMO_STEP_MS": 4000    # Default — comfortable reading pace
"DEMO_STEP_MS": 8000    # Slow — easier to read at car shows / events
```

---

## Function Keys & Commands

### Function Keys

These labels match the real Motorola MDT 9100-T hardware, as seen on the unit photo.

| Key | Hardware Label | Action |
|---|---|---|
| `F1` | **ACK** | Acknowledge pending message / assignment |
| `F2` | *(MSGS)* | Message log / Message Center |
| `F3` | **SCENE** | Set status 10-97 On Scene |
| `F4` | *(10-CODES)* | 10-Code quick reference |
| `F5` | **OUTSVC** | Set status 10-7 Out of Service |
| `F6` | **TRNSPT** | Set status 10-76 En Route / Transport |
| `F7` | *(CLR/10-8)* | Set status 10-8 In Service / Clear |
| `F8` | **VEH** | Vehicle / plate NCIC query |
| `F9` | **PERSON** | Person / driver license query |
| `F10` | *(CLEAR)* | Clear screen |
| `F11` | **T-STOP** | Traffic stop — sets On Scene, prompts plate/person query |
| `F12` | **ONVIEW** | On-view / self-initiated incident |
| `Ctrl+E` | **EMER** *(red button)* | Emergency — 10-33 broadcast |

### Typed Commands

| Command | Description |
|---|---|
| `PLATE MA/5RVW441` | Query plate (state/number) |
| `PERSON MORIARTY,KEVIN` | Query person by name |
| `DL M774409821` | Query by driver's license number |
| `MSG [text]` | Send free-text message to dispatch |
| `ACK` | Acknowledge pending assignment |
| `STATUS` | Open unit status selection |
| `10-8` / `10-97` / `10-76` / `10-7` / `10-33` | Set status directly |
| `SIM` | Simulate a random incoming dispatch call |
| `DEMO` | Run the full scripted call scenario |
| `TIME` | Display current date and time |
| `HELP` | Show 10-code reference |
| `CLEAR` / `CLS` | Clear the screen |
| `ABOUT` | Full command reference |
| `↑` / `↓` | Scroll command history |

---

## Northwest Beat — Local Geography

Car 12 patrols the **northwest section of Saugus, MA**, which includes:

### Primary Streets (Northwest Beat)

| Street | Area |
|---|---|
| Lynn Fells Parkway | Main NW corridor, connects to Fellsway in Melrose/Malden |
| Penobscot Road | Residential, Oaklandvale area |
| Mountview Road | Residential, northern Saugus |
| Sweetser Avenue | NW residential |
| Guild Road | Near Saugus/Wakefield line |
| Golden Hills Drive | Golden Hills subdivision |
| Roby Street | NW residential |
| Hurd Avenue | NW residential |
| Springfield Street | NW residential |
| Iron Works Road | Near Saugus River / Iron Works historic site |
| Old Essex Road | NW connector |
| Forest Street | Near Breakheart Reservation |

### Key Landmarks in Northwest Beat

- **Breakheart Reservation** — 600+ acre woodland reservation on the Saugus/Wakefield/Lynn line; frequent calls at the Lynn Fells Pkwy entrance
- **Oaklandvale** — quiet residential neighborhood in northern Saugus
- **Golden Hills** — residential subdivision in the northwest quarter
- **Saugus River / Iron Works area** — industrial history, secluded roads near Iron Works Road
- **Saugus/Lynn line** — Penobscot Road area borders Lynn; occasional cross-jurisdiction calls
- **Saugus/Wakefield line** — Guild Road area; calls sometimes require Wakefield PD coordination

### Route 1 Landmarks (Town-wide, all units)

All Saugus units reference these Route 1 landmarks in dispatch calls:

| Landmark | Address | Notes |
|---|---|---|
| Hilltop Steak House | 855 Broadway | America's busiest restaurant in the 1980s; iconic 68-ft neon cactus |
| Kowloon Restaurant | 948 Broadway | Tiki-themed landmark open since 1958 |
| Prince Pizza | Broadway (Rt. 1) | Leaning Tower of Pisa replica |
| Saugus Iron Works | Central St | First integrated iron works in North America; National Historic Site since 1968 |

---

## Simulated NCIC Data

All vehicle, plate, and person records are entirely fictional and set in the North Shore / Greater Boston area circa 1989.

### Plate Records

| Plate | Vehicle | Status | Notes |
|---|---|---|---|
| 2GHF847 MA | 1983 Ford Crown Vic | Clean | Saugus, Central St |
| 5RVW441 MA | 1978 Ford Econoline Van | **Warrant hit** | Saugus, Mountview Rd — *demo vehicle* |
| 7FPL219 MA | 1984 Dodge Diplomat | Warrant | Revere |
| 4TMB663 MA | 1979 Ford Thunderbird | **Stolen** | Saugus, Bristow St |
| 6KBN095 MA | 1977 Ford Pinto | Probation warrant | Saugus, Essex St |
| 8LWQ314 MA | 1982 Buick LeSabre | Suspended reg | Malden |
| CBJ447 NH | 1985 Plymouth Gran Fury | Clean | Manchester NH |
| 3QVZ881 MA | 1981 AMC Concord | Clean | Wakefield |

### Person Records

| Name | Status | Notes |
|---|---|---|
| MORIARTY, KEVIN P | **Active warrant, expired DL** | Essex Superior Ct, A&B DW — *demo subject* |
| DOHERTY, THOMAS J | Revoked license, default warrant | Lynn Dist Ct, OUI repeat |
| GIANFRANCESCO, ANTHONY R | Default warrant | Lynn Dist Ct |
| NEWHALL, GARY F | Probation warrant | Essex Superior, prior B&E |
| SHURTLEFF, DENNIS P | Suspended license | Outstanding fines |
| CARAVIELLO, PAUL D | Clean | — |
| MCDONOUGH, PATRICIA A | Clean | — |
| PELLEGRINO, ROSEMARIE L | Clean | — |

---

## Recommended In-Car Hardware

Designed for the 1989 Crown Victoria LTD restoration but works in any vehicle:

| Component | Recommendation | Approx. Cost |
|---|---|---|
| Computer | Raspberry Pi 4 (2GB or 4GB) | $45–55 |
| Display | 7" or 10" HDMI touchscreen | $40–80 |
| Power | 12V → USB-C step-down adapter | $15–25 |
| Keyboard | Compact backlit USB keyboard | $20–40 |

The Pi boots in approximately 30 seconds and auto-starts the MDT terminal via `launch_mdt.sh`. Mount the display in the center console where the original MDT bracket would have been located.

The **demo mode** makes the terminal immediately useful for car shows and department events — it runs the full scenario automatically after boot with no operator input required.

---

## File Structure

```
mdt9100t/
├── mdt_emulator.py     # Main emulator application (all-in-one)
├── launch_mdt.sh       # Raspberry Pi autostart / kiosk launcher
└── README.md           # This file
```

---

## Project Background

This emulator was built to complete a full restoration of a **1989 Ford Crown Victoria LTD** for the **Saugus Police Department**. The original Motorola MDT 9100-T hardware is no longer available, so this Python application running on a Raspberry Pi fills that role — preserving the authentic look and operational workflow of a 1980s police cruiser's mobile data terminal.

The cruiser, **Car 12**, is assigned to the Northwest Beat covering the Lynn Fells Parkway corridor, Oaklandvale, and the Breakheart Reservation area — the same geography simulated in the emulator's dispatch calls and demo scenario.

---

## Disclaimer

All NCIC/CJIS data, vehicle records, plate numbers, and person records in this emulator are **entirely fictional** and generated for display and demonstration purposes only. This software does not connect to any real law enforcement database, radio network, or CAD system. It is intended purely for historical vehicle restoration and educational display use.

---

## License

MIT License — free to use, modify, and distribute for personal, educational, and restoration projects.