#!/usr/bin/env python3
"""
============================================================
  MOTOROLA MDT 9100-T  —  MOBILE DATA TERMINAL EMULATOR
  Saugus Police Department  |  Unit Emulator v1.0
  
  For use with 1989 Ford Crown Victoria LTD Restoration
  Compatible with: Raspberry Pi (Linux) / Windows PC
  Requires: Python 3.7+  |  No external dependencies
============================================================
"""

import tkinter as tk
from tkinter import font as tkfont
import threading
import time
import random
import datetime
import json
import os
import sys
import queue
import math

# ─────────────────────────────────────────────
#  CONFIGURATION  (Edit to match your unit)
# ─────────────────────────────────────────────
CONFIG = {
    "AGENCY":       "SAUGUS PD",
    "UNIT_ID":      "CAR-12",
    "BEAT":         "BEAT NW",           # Northwest Saugus patrol area
    "OFFICER":      "OFFICER UNIT",
    "CHANNEL":      "CH-1 PRIMARY",
    "FREQ":         "460.125",
    "TERMINAL_ID":  "MDT-9100T-0042",
    "CAD_SERVER":   "DISPATCH-1",
    "PHOSPHOR":     "amber",             # "amber" or "green"
    # ── Display / window ───────────────────────────────────────────────
    # Set FULLSCREEN to True for Raspberry Pi kiosk / in-car use.
    # The window will fill the entire screen with no title bar or borders.
    # Press Escape at any time to exit full-screen mode back to a window.
    "FULLSCREEN":   False,
    "WINDOW_W":     900,                 # Window width  (ignored in fullscreen)
    "WINDOW_H":     640,                 # Window height (ignored in fullscreen)
    "SCANLINES":    True,
    "CRT_EFFECT":   True,
    "SOUND":        True,
    # ── Off Duty / shutdown ─────────────────────────────────────────────
    # When True, the OFF DUTY button requires a second press within 3 seconds
    # to confirm before the program exits.  Set False to exit on first press.
    "CONFIRM_OFF_DUTY": True,
    "AUTO_DISPATCH": True,               # Simulate incoming dispatch calls
    "DISPATCH_INTERVAL": 45,            # Seconds between simulated dispatches
    # ── Demo Mode ──────────────────────────────────────────────────────
    # When True, runs a full scripted call scenario after boot:
    #   dispatch → officer ACKs → en route → on scene →
    #   plate/person query → warrant hit → clear
    # Set False to disable. Use command DEMO to trigger manually anytime.
    "DEMO_MODE":    True,
    "DEMO_DELAY":   5,                   # Seconds after boot before demo starts
    "DEMO_STEP_MS": 4000,               # Milliseconds between demo steps (4 sec default)
}

# ─────────────────────────────────────────────
#  PHOSPHOR COLOUR PALETTES
# ─────────────────────────────────────────────
PALETTES = {
    "amber": {
        "bg":          "#0D0800",
        "fg":          "#FFB000",
        "fg_dim":      "#7A5500",
        "fg_bright":   "#FFD966",
        "fg_alert":    "#FF4400",
        "fg_ok":       "#FFCC44",
        "fg_header":   "#FF8800",
        "cursor":      "#FFB000",
        "scanline":    "#0D0800",
        "glow":        "#FF990055",
        "border":      "#3A2800",
        "key_bg":      "#1A1000",
        "key_fg":      "#FFB000",
        "key_active":  "#FF8800",
        "input_bg":    "#1A1000",
        "status_ok":   "#FFB000",
        "status_warn": "#FF6600",
        "status_alert":"#FF2200",
        "bezel":       "#1C1410",
        "bezel_dark":  "#0A0604",
    },
    "green": {
        "bg":          "#000D00",
        "fg":          "#00CC44",
        "fg_dim":      "#005522",
        "fg_bright":   "#44FF88",
        "fg_alert":    "#FF4400",
        "fg_ok":       "#00FF66",
        "fg_header":   "#00FF44",
        "cursor":      "#00CC44",
        "scanline":    "#000D00",
        "glow":        "#00CC4455",
        "border":      "#003311",
        "key_bg":      "#001A00",
        "key_fg":      "#00CC44",
        "key_active":  "#00FF66",
        "input_bg":    "#001A00",
        "status_ok":   "#00CC44",
        "status_warn": "#AACC00",
        "status_alert":"#FF4400",
        "bezel":       "#101810",
        "bezel_dark":  "#040A04",
    }
}

P = PALETTES[CONFIG["PHOSPHOR"]]  # Active palette

# ─────────────────────────────────────────────
#  10-CODES & STATUS DEFINITIONS
# ─────────────────────────────────────────────
TEN_CODES = {
    "10-4":  "ACKNOWLEDGED / OK",
    "10-6":  "BUSY - STAND BY",
    "10-7":  "OUT OF SERVICE",
    "10-8":  "IN SERVICE",
    "10-9":  "REPEAT TRANSMISSION",
    "10-19": "RETURN TO STATION",
    "10-20": "LOCATION",
    "10-21": "CALL BY TELEPHONE",
    "10-22": "DISREGARD",
    "10-23": "ARRIVED AT SCENE",
    "10-24": "ASSIGNMENT COMPLETED",
    "10-25": "REPORT TO",
    "10-27": "DRIVER LICENSE INFO",
    "10-28": "VEHICLE REGISTRATION",
    "10-29": "CHECK FOR WANTED",
    "10-33": "EMERGENCY",
    "10-35": "CONFIDENTIAL INFO",
    "10-36": "CORRECT TIME",
    "10-42": "ENDING TOUR OF DUTY",
    "10-43": "BEGINNING TOUR OF DUTY",
    "10-50": "ACCIDENT",
    "10-51": "TOW TRUCK NEEDED",
    "10-52": "AMBULANCE NEEDED",
    "10-53": "ROAD BLOCKED",
    "10-54": "LIVESTOCK ON HIGHWAY",
    "10-55": "INTOXICATED DRIVER",
    "10-56": "INTOXICATED PEDESTRIAN",
    "10-57": "HIT AND RUN",
    "10-61": "PERSONNEL IN AREA",
    "10-62": "REPLY TO MESSAGE",
    "10-63": "PREPARE TO COPY",
    "10-65": "NET MESSAGE ASSIGNMENT",
    "10-70": "FIRE ALARM",
    "10-76": "EN ROUTE",
    "10-77": "ETA",
    "10-97": "ARRIVED AT SCENE",
    "10-98": "AVAILABLE / CLEAR",
    "10-99": "WANTED / STOLEN INDICATED",
}

UNIT_STATUSES = [
    ("10-8",  "IN SERVICE",          "ok"),
    ("10-7",  "OUT OF SERVICE",      "warn"),
    ("10-6",  "BUSY - STAND BY",     "warn"),
    ("10-76", "EN ROUTE",            "ok"),
    ("10-97", "ON SCENE",            "warn"),
    ("10-98", "AVAILABLE",           "ok"),
    ("10-19", "RETURN TO STATION",   "warn"),
    ("10-33", "EMERGENCY",           "alert"),
]

# ─────────────────────────────────────────────
#  SIMULATED DISPATCH / CAD DATA
# ─────────────────────────────────────────────
CALL_TYPES = [
    ("594",  "THEFT REPORT",              2),
    ("459",  "BURGLARY",                  1),
    ("211",  "ROBBERY",                   1),
    ("415",  "DISTURBANCE",               2),
    ("10-50","TRAFFIC ACCIDENT",          2),
    ("902T", "ACCIDENT - INJURY",         1),
    ("647F", "DRUNK IN PUBLIC",           3),
    ("242",  "BATTERY",                   1),
    ("487",  "GRAND THEFT",               2),
    ("11-84","TRAFFIC HAZARD",            3),
    ("11-25","TRAFFIC ENFORCEMENT",       3),
    ("245",  "ASSAULT WITH WEAPON",       1),
    ("10-70","FIRE ALARM",                1),
    ("10-52","AMBULANCE REQUESTED",       1),
    ("459A", "BURG ALARM - AUDIBLE",      2),
    ("503",  "AUTO THEFT",                2),
    ("602",  "TRESPASS",                  3),
    ("901T", "TRAFFIC ACCIDENT",          3),
    ("261",  "RAPE",                      1),
    ("11-41","REQUEST AMBULANCE",         1),
    ("WELCK","WELFARE CHECK",             3),
    ("NOISE","NOISE COMPLAINT",           3),
    ("SUSPS","SUSPICIOUS PERSON",         2),
    ("SUSVC","SUSPICIOUS VEHICLE",        2),
    ("DOMES","DOMESTIC DISPUTE",          1),
    ("VAND", "VANDALISM",                 3),
]

STREET_NAMES = [
    # ── Northwest Saugus beat (CAR-12 primary area) ──────────────────
    "LYNN FELLS PKWY",    "PENOBSCOT RD",       "MOUNTVIEW RD",
    "SWEETSER AVE",       "GUILD RD",            "GOLDEN HILLS DR",
    "SPRINGFIELD ST",     "ROBY ST",             "HURD AVE",
    "DUDLEY ST",          "TAYLOR ST",           "MAPLEWOOD AVE",
    "LEONARD ST",         "ADAMS AVE",           "APPLETON ST",
    "BIRCH HILL AVE",     "WALNUT ST",           "VINE ST",
    # ── Oaklandvale / Breakheart area ────────────────────────────────
    "FOREST ST",          "SAUGUS CENTER RD",    "IRON WORKS RD",
    "OLD ESSEX RD",       "FELLSWAY W",
    # ── Town-wide streets (for background traffic calls) ─────────────
    "CENTRAL ST",         "MAIN ST",             "WINTER ST",
    "CHESTNUT ST",        "PLEASANT ST",         "HAMILTON ST",
    "CLIFTONDALE SQ",     "BRISTOW ST",          "BALLARD ST",
    "NEWHALL ST",         "ESSEX ST",
    # ── Route 1 corridor ─────────────────────────────────────────────
    "BROADWAY (RT 1 NB)", "BROADWAY (RT 1 SB)",
]

CROSS_STREETS = [
    # Northwest beat intersections
    "@ PENOBSCOT RD",          "@ MOUNTVIEW RD",          "@ GUILD RD",
    "@ SWEETSER AVE",          "@ HURD AVE",              "@ SPRINGFIELD ST",
    "@ GOLDEN HILLS DR",       "@ ADAMS AVE",             "@ ROBY ST",
    # Oaklandvale / Breakheart area
    "NR BREAKHEART RESERVATION ENTRANCE", "@ IRON WORKS RD",
    "@ OLD ESSEX RD",          "@ SAUGUS CENTER RD",      "@ FOREST ST",
    # Lynn Fells Pkwy cross-streets
    "@ LYNN FELLS PKWY / PENOBSCOT", "@ LYNN FELLS PKWY / GUILD RD",
    # Route 1 landmark references
    "NB RT1 N/O HILLTOP STEAK HOUSE", "NB RT1 S/O KOWLOON REST",
    "SB RT1 N/O PRINCE PIZZA",        "RT1 @ LYNN FELLS PKWY",
    "RT1 @ ESSEX ST (RT107)",
    # General town anchors
    "N/O CLIFTONDALE SQ",      "S/O SAUGUS CTR",          "E/O IRON WORKS RD",
]

# Saugus PD unit designations (1989 era) — CAR-12 is northwest beat
OFFICERS = [
    "CAR-1", "CAR-3", "CAR-5", "CAR-7", "CAR-9",
    "CAR-11", "CAR-14", "CAR-17", "CAR-21",
    "SGT-1 FLANAGAN", "SGT-2 MCNULTY", "DET-1 CARAVIELLO",
    "K9-1 DEVLIN", "TRAP-1",
    CONFIG["UNIT_ID"],
]

# Simulated plate/vehicle data — Saugus MA & North Shore area, 1989
PLATE_DATA = [
    # Clean record — Saugus resident, Central St
    {"plate":"2GHF847","state":"MA","year":"1983","make":"FORD","model":"LTD CROWN VIC","color":"BLK",
     "reg":"VALID","reg_exp":"11/90","vin":"1FABP43F3GZ187241",
     "owner":"CARAVIELLO, PAUL D","addr":"114 CENTRAL ST, SAUGUS MA 01906",
     "dob":"08/22/1949","dl":"C448821563","wants":"NONE","stolen":"NO"},

    # Expired reg — Lynn resident, older Chevy
    {"plate":"1RNK492","state":"MA","year":"1980","make":"CHEVY","model":"IMPALA","color":"BLU",
     "reg":"EXPIRED","reg_exp":"04/85","vin":"1G1AL69H0AH204773",
     "owner":"DOHERTY, KATHLEEN M","addr":"47 NEWHALL ST, LYNN MA 01902",
     "dob":"03/14/1957","dl":"D331940278","wants":"NONE","stolen":"NO"},

    # Warrant hit — Revere resident, Dodge
    {"plate":"7FPL219","state":"MA","year":"1984","make":"DODGE","model":"DIPLOMAT","color":"GRY",
     "reg":"VALID","reg_exp":"09/92","vin":"1B3BJ46D8EG440019",
     "owner":"GIANFRANCESCO, ANTHONY R","addr":"23 PROSPECT AVE, REVERE MA 02151",
     "dob":"11/05/1955","dl":"G228844917","wants":"DEFAULT WARRANT - LYNN DIST COURT","stolen":"NO"},

    # Stolen vehicle — Saugus Lynnhurst neighborhood
    {"plate":"4TMB663","state":"MA","year":"1979","make":"FORD","model":"THUNDERBIRD","color":"RED",
     "reg":"VALID","reg_exp":"06/91","vin":"9A93H813889204411",
     "owner":"PELLEGRINO, ROSEMARIE","addr":"88 BRISTOW ST, SAUGUS MA 01906",
     "dob":"05/30/1961","dl":"P114508839","wants":"NONE","stolen":"YES - RPT 89-07741 SPD"},

    # NH resident at the Hilltop — Plymouth Gran Fury (cop car)
    {"plate":"CBJ447","state":"NH","year":"1985","make":"PLYMOUTH","model":"GRAN FURY","color":"WHT",
     "reg":"VALID","reg_exp":"12/91","vin":"1P4PL4GJ5FF308892",
     "owner":"BEAUMONT, RICHARD L","addr":"19 BROCK ST, MANCHESTER NH 03101",
     "dob":"07/04/1952","dl":"B551023677","wants":"NONE","stolen":"NO"},

    # Suspended reg — Malden resident, Buick
    {"plate":"8LWQ314","state":"MA","year":"1982","make":"BUICK","model":"LESABRE","color":"SLV",
     "reg":"SUSPENDED","reg_exp":"01/92","vin":"4G4AH47H2CH330124",
     "owner":"SHURTLEFF, DENNIS P","addr":"206 FERRY ST, MALDEN MA 02148",
     "dob":"09/18/1963","dl":"S770349102","wants":"NONE","stolen":"NO"},

    # Wakefield resident, clean record, AMC
    {"plate":"3QVZ881","state":"MA","year":"1981","make":"AMC","model":"CONCORD","color":"BRN",
     "reg":"VALID","reg_exp":"03/92","vin":"A1C79B7122893",
     "owner":"MCDONOUGH, PATRICIA A","addr":"7 CHESTNUT ST, WAKEFIELD MA 01880",
     "dob":"12/01/1960","dl":"M885512047","wants":"NONE","stolen":"NO"},

    # East Saugus resident, probation warrant
    {"plate":"6KBN095","state":"MA","year":"1977","make":"FORD","model":"PINTO","color":"YEL",
     "reg":"EXPIRED","reg_exp":"02/84","vin":"7T10Y201694",
     "owner":"NEWHALL, GARY F","addr":"331 ESSEX ST, SAUGUS MA 01906",
     "dob":"06/15/1958","dl":"N662017340","wants":"PROBATION WARRANT - ESSEX SUPERIOR","stolen":"NO"},
]

# Simulated person/DL data — North Shore MA, 1989
LOCATION_NOTES = [
    # Northwest Saugus beat (CAR-12 primary area)
    "BREAKHEART RESERVATION ENTRANCE / LYNN FELLS PKWY",
    "OAKLANDVALE NEIGHBORHOOD",
    "GOLDEN HILLS SUBDIVISION",
    "NEAR IRON WORKS RD / SAUGUS RIVER AREA",
    "LYNN FELLS PKWY - FELLSWAY AREA",
    "NR SAUGUS/LYNN LINE - PENOBSCOT RD AREA",
    "NR SAUGUS/WAKEFIELD LINE - GUILD RD",
    # Town-wide landmarks
    "HILLTOP STEAK HOUSE PARKING LOT",
    "KOWLOON RESTAURANT AREA",
    "PRINCE PIZZA PARKING LOT",
    "CLIFTONDALE SQUARE",
    "SAUGUS CTR - NEAR TOWN HALL",
    "SAUGUS HIGH SCHOOL AREA",
    "LYNNHURST NEIGHBORHOOD",
    "PLEASANT HILLS NEIGHBORHOOD",
    # Generic (weighted higher for variety)
    "SEE CALLER FOR DETAILS",
    "SEE CALLER FOR DETAILS",
    "SEE CALLER FOR DETAILS",
    "SEE CALLER FOR DETAILS",
]

# ─────────────────────────────────────────────────────────────────
#  DEMO MODE SCENARIO
#  A fully scripted call — played back step by step after boot.
#  Each entry is: (delay_ms_from_prev_step, "method_name", *args)
#  The engine in MDT9100T._demo_run_step() dispatches these.
# ─────────────────────────────────────────────────────────────────

# Plate and person used inside the scripted scenario
DEMO_PLATE = {
    "plate":"5RVW441","state":"MA","year":"1978","make":"FORD",
    "model":"ECONOLINE VAN","color":"DRK GRN",
    "reg":"VALID","reg_exp":"08/91","vin":"F10HRV74714",
    "owner":"MORIARTY, KEVIN P","addr":"77 MOUNTVIEW RD, SAUGUS MA 01906",
    "dob":"02/09/1953","dl":"M774409821",
    "wants":"DEFAULT WARRANT - ESSEX SUPERIOR CT / A&B DW",
    "stolen":"NO",
}
DEMO_PERSON = {
    "name":"MORIARTY, KEVIN PAUL","dob":"02/09/1953",
    "race":"W","sex":"M","ht":"600","wt":"215","eyes":"BLU","hair":"BRN",
    "dl":"M774409821","dl_state":"MA","dl_class":"3","dl_exp":"02/92",
    "dl_status":"EXPIRED",
    "wants":"DEFAULT WARRANT - ESSEX SUPERIOR CT  /  A&B WITH DANGEROUS WEAPON (1985)",
    "priors":"4 - A&B (1979), DISORDERLY (1981), A&B DW (1985), OUI LIQUOR (1983)",
}

# The scripted scenario steps.
# Format: (pause_ms, step_type, *payload)
#   step_type "dispatch"  → incoming assignment message
#   step_type "status"    → unit status change  (code, text, level)
#   step_type "outmsg"    → outbound message from unit to dispatch
#   step_type "inmsg"     → inbound message from dispatch
#   step_type "plate"     → NCIC plate query result
#   step_type "person"    → NCIC person query result
#   step_type "label"     → plain text written to screen
DEMO_STEPS = [
    # ── Step 1: Dispatch receives a call and assigns CAR-12 ──────────
    (0, "dispatch", [
        f"*** DISPATCH - ASSIGNMENT FOR {CONFIG['UNIT_ID']} ***",
        "INCIDENT: 89-14872",
        "CALL TYPE: SUSVC - SUSPICIOUS VEHICLE",
        "PRIORITY: PRIORITY 2 - URGENT",
        "LOCATION: LYNN FELLS PKWY @ PENOBSCOT RD",
        "INFO: DARK GREEN VAN PARKED 3+ HRS - MOTOR RUNNING",
        "CALLER: ANON RESIDENT - STATES OCCUPANT ACTING STRANGE",
        "ACK W/ 10-4 AND ADVISE RESPONDING",
        f"TIME DISPATCHED: {{time}}",
    ]),
    # ── Step 2: Unit acknowledges and goes en route ──────────────────
    (3500, "status", ("10-76", "EN ROUTE", "ok")),
    (500,  "outmsg", [
        f"*** {CONFIG['UNIT_ID']} TO DISPATCH ***",
        "10-4 ON INCIDENT 89-14872",
        "10-76 LYNN FELLS PKWY / PENOBSCOT",
        "ETA APPROX 3 MIN",
    ]),
    # ── Step 3: Dispatch sends supplemental info ─────────────────────
    (4000, "inmsg", [
        "*** DISPATCH SUPPLEMENTAL - INCIDENT 89-14872 ***",
        "ADDITIONAL CALLER INFO:",
        "VEH IS DRK GRN FORD VAN - OCC APPEARS SLUMPED",
        "POSSIBLE MEDICAL OR INTOXICATION",
        "CAR-9 NOTIFIED - STANDING BY",
    ]),
    # ── Step 4: Unit arrives on scene ───────────────────────────────
    (5000, "status", ("10-97", "ON SCENE", "warn")),
    (500,  "outmsg", [
        f"*** {CONFIG['UNIT_ID']} TO DISPATCH ***",
        "10-97 LYNN FELLS PKWY / PENOBSCOT",
        "ONE MALE OCC - CONSCIOUS - ODOR ETOH",
        "RUNNING PLATE ON VAN",
    ]),
    # ── Step 5: Plate query (simulated NCIC delay then response) ────
    (3000, "label",  "  QUERYING NCIC FOR PLATE: 5RVW441..."),
    (2500, "plate",  DEMO_PLATE),
    # ── Step 6: Person query ─────────────────────────────────────────
    (3000, "label",  "  QUERYING NCIC FOR: MORIARTY,KEVIN..."),
    (2500, "person", DEMO_PERSON),
    # ── Step 7: Unit advises dispatch of warrant hit ─────────────────
    (2000, "outmsg", [
        f"*** {CONFIG['UNIT_ID']} TO DISPATCH ***",
        "NCIC RETURN - WARRANT HIT ON OCC",
        "MORIARTY, KEVIN P  DOB 02/09/53",
        "DEFAULT WARRANT - ESSEX SUPERIOR - A&B DW",
        "PLACING UNDER ARREST - REQUEST BACKUP",
        "ALSO NEED TOW FOR VAN  10-51",
    ]),
    # ── Step 8: Dispatch sends backup ────────────────────────────────
    (3000, "inmsg", [
        "*** DISPATCH TO CAR-12 ***",
        "10-4  WARRANT CONFIRMED - ESSEX SUPERIOR CT",
        "CAR-9 EN ROUTE YOUR LOCATION - ETA 2 MIN",
        "TOW NOTIFIED - SAUGUS GULF STATION RT1",
        "ADVISE WHEN SECURED",
    ]),
    # ── Step 9: Unit advises prisoner secured ────────────────────────
    (7000, "outmsg", [
        f"*** {CONFIG['UNIT_ID']} TO DISPATCH ***",
        "PRISONER SECURED - MORIARTY, KEVIN P",
        "TRANSPORTING TO SPD - BOOKING",
        "CAR-9 WILL STAND BY FOR TOW",
    ]),
    # ── Step 10: Unit clears, back in service ───────────────────────
    (5000, "status", ("10-98", "AVAILABLE / CLEAR", "ok")),
    (500,  "inmsg", [
        "*** DISPATCH - INCIDENT 89-14872 CLOSED ***",
        "CAR-12 ASSIGNMENT COMPLETED",
        f"ARREST: MORIARTY, KEVIN P  -  DEFAULT WARRANT",
        "CASE ASSIGNED TO DET-1 CARAVIELLO",
        "GOOD WORK CAR-12  -  10-8 WHEN READY",
    ]),
    (2000, "status", ("10-8", "IN SERVICE", "ok")),
]

# Simulated person/DL data — North Shore MA, 1989
PERSON_DATA = [
    # Clean record, Saugus Center resident
    {"name":"CARAVIELLO, PAUL DOMINIC","dob":"08/22/1949",
     "race":"W","sex":"M","ht":"510","wt":"190","eyes":"BRN","hair":"BLK",
     "dl":"C448821563","dl_state":"MA","dl_class":"3","dl_exp":"08/92",
     "dl_status":"VALID","wants":"NONE",
     "priors":"NONE"},

    # OUI repeat, Lynn — revoked license
    {"name":"DOHERTY, THOMAS JOSEPH","dob":"06/12/1958",
     "race":"W","sex":"M","ht":"507","wt":"175","eyes":"BLU","hair":"BRN",
     "dl":"D229910048","dl_state":"MA","dl_class":"3","dl_exp":"06/92",
     "dl_status":"REVOKED - OUI REPEAT","wants":"DEFAULT WARRANT - LYNN DIST COURT",
     "priors":"3 - OUI LIQUOR (1981,1983,1985), OPER AFTER REVOC"},

    # Clean, Wakefield female resident
    {"name":"MCDONOUGH, PATRICIA ANN","dob":"12/01/1960",
     "race":"W","sex":"F","ht":"504","wt":"125","eyes":"GRN","hair":"BLN",
     "dl":"M885512047","dl_state":"MA","dl_class":"3","dl_exp":"12/92",
     "dl_status":"VALID","wants":"NONE",
     "priors":"NONE"},

    # Active warrant, Revere
    {"name":"GIANFRANCESCO, ANTHONY ROBERT","dob":"11/05/1955",
     "race":"W","sex":"M","ht":"511","wt":"210","eyes":"BRN","hair":"BLK",
     "dl":"G228844917","dl_state":"MA","dl_class":"3","dl_exp":"11/91",
     "dl_status":"VALID","wants":"DEFAULT WARRANT - LYNN DIST COURT / OPER UNINSUIRED VEH",
     "priors":"2 - DISORDERLY PERSON (1980), OUI LIQUOR (1984)"},

    # Suspended license, Malden
    {"name":"SHURTLEFF, DENNIS PAUL","dob":"09/18/1963",
     "race":"W","sex":"M","ht":"508","wt":"160","eyes":"HZL","hair":"BRN",
     "dl":"S770349102","dl_state":"MA","dl_class":"3","dl_exp":"09/92",
     "dl_status":"SUSPENDED - OUTSTANDING FINES","wants":"NONE",
     "priors":"1 - OPER MV NEGLIGENTLY (1984)"},

    # Serious priors, probation warrant, Saugus/East Saugus
    {"name":"NEWHALL, GARY FRANCIS","dob":"06/15/1958",
     "race":"W","sex":"M","ht":"601","wt":"195","eyes":"BLU","hair":"BRN",
     "dl":"N662017340","dl_state":"MA","dl_class":"3","dl_exp":"06/90",
     "dl_status":"EXPIRED","wants":"PROBATION WARRANT - ESSEX SUPERIOR CT",
     "priors":"4 - LARCENY OVER $250 (1979,1982), B&E NIGHTTIME (1983), A&B (1985)"},

    # Saugus Iron Works area, Lynnhurst resident
    {"name":"PELLEGRINO, ROSEMARIE LUCIA","dob":"05/30/1961",
     "race":"W","sex":"F","ht":"505","wt":"130","eyes":"BRN","hair":"BLK",
     "dl":"P114508839","dl_state":"MA","dl_class":"3","dl_exp":"05/92",
     "dl_status":"VALID","wants":"NONE",
     "priors":"NONE"},
]

# ─────────────────────────────────────────────
#  NCIC RESPONSE FORMATTER
# ─────────────────────────────────────────────
def format_plate_response(data):
    lines = [
        "*** NCIC / CJIS RESPONSE ***",
        f"REG: {data['plate']}/{data['state']}  {data['year']} {data['make']} {data['model']}",
        f"COLOR: {data['color']}  VIN: {data['vin']}",
        f"REG STATUS: {data['reg']}  EXP: {data['reg_exp']}",
        f"OWNER: {data['owner']}",
        f"ADDRESS: {data['addr']}",
        f"DOB: {data['dob']}  DL: {data['dl']}",
        "---",
        f"WANTS/WARRANTS: {data['wants']}",
        f"STOLEN VEHICLE: {data['stolen']}",
        "END NCIC RESPONSE",
    ]
    if data['wants'] != "NONE":
        lines.insert(0, "!!! CAUTION - WANTS/WARRANTS INDICATED !!!")
    if data['stolen'] != "NO":
        lines.insert(0, "!!! CAUTION - STOLEN VEHICLE INDICATED !!!")
    return lines

def format_person_response(data):
    lines = [
        "*** NCIC / CJIS PERSON RESPONSE ***",
        f"NAME: {data['name']}",
        f"DOB: {data['dob']}  RACE: {data['race']}  SEX: {data['sex']}",
        f"HT: {data['ht']}  WT: {data['wt']}  EYES: {data['eyes']}  HAIR: {data['hair']}",
        f"DL: {data['dl']}/{data['dl_state']}  CLASS: {data['dl_class']}",
        f"DL EXP: {data['dl_exp']}  STATUS: {data['dl_status']}",
        "---",
        f"WANTS/WARRANTS: {data['wants']}",
        f"PRIOR RECORD: {data['priors']}",
        "END NCIC RESPONSE",
    ]
    if data['wants'] != "NONE":
        lines.insert(0, "!!! CAUTION - WANTS/WARRANTS INDICATED !!!")
    return lines

def generate_dispatch_call():
    call = random.choice(CALL_TYPES)
    code, desc, priority = call
    num = random.randint(100, 9999)
    addr = f"{random.randint(1,999)} {random.choice(STREET_NAMES)}"
    cross = random.choice(CROSS_STREETS)
    unit = random.choice([u for u in OFFICERS if u != CONFIG["UNIT_ID"]])
    incident = f"89-{random.randint(10000,99999)}"
    pri_str = ["PRIORITY 1 - EMERGENCY","PRIORITY 2 - URGENT","PRIORITY 3 - ROUTINE"][priority-1]
    note = random.choice(LOCATION_NOTES)
    lines = [
        f"*** DISPATCH - CAD INCIDENT {incident} ***",
        f"CALL TYPE: {code} - {desc}",
        f"PRIORITY: {pri_str}",
        f"LOCATION: {addr} {cross}",
        f"INFO: {note}",
        f"ASSIGNED: {unit}  TIME: {datetime.datetime.now().strftime('%H:%M:%S')}",
        "RESPOND W/ 10-97 ON ARRIVAL",
    ]
    if priority == 1:
        lines.insert(0, "!!! EMERGENCY PRIORITY CALL !!!")
    return lines, priority

def generate_assignment_for_unit():
    """Generate a direct assignment to this unit"""
    call = random.choice([c for c in CALL_TYPES if c[2] <= 2])
    code, desc, priority = call
    addr = f"{random.randint(1,999)} {random.choice(STREET_NAMES)}"
    cross = random.choice(CROSS_STREETS)
    incident = f"89-{random.randint(10000,99999)}"
    pri_str = ["PRIORITY 1 - EMERGENCY","PRIORITY 2 - URGENT","PRIORITY 3 - ROUTINE"][priority-1]
    lines = [
        f"*** DISPATCH - ASSIGNMENT FOR {CONFIG['UNIT_ID']} ***",
        f"INCIDENT: {incident}",
        f"CALL TYPE: {code} - {desc}",
        f"PRIORITY: {pri_str}",
        f"LOCATION: {addr} {cross}",
        f"ADDITIONAL INFO: CALLER STATES SITUATION ONGOING",
        f"ACK W/ 10-4 AND ADVISE RESPONDING",
        f"TIME DISPATCHED: {datetime.datetime.now().strftime('%H:%M:%S')}",
    ]
    return lines, priority


# ─────────────────────────────────────────────
#  SOUND  (cross-platform bell via tkinter)
# ─────────────────────────────────────────────
def beep(root, freq=880, duration=100):
    if not CONFIG["SOUND"]:
        return
    try:
        root.bell()
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════
#  MDT MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════
class MDT9100T(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Motorola MDT 9100-T  |  {CONFIG['AGENCY']}  |  {CONFIG['UNIT_ID']}")
        self.configure(bg=P["bezel"])
        self.resizable(True, True)
        self.geometry(f"{CONFIG['WINDOW_W']}x{CONFIG['WINDOW_H']}")
        if CONFIG["FULLSCREEN"]:
            self.attributes("-fullscreen", True)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # State
        self.msg_queue       = queue.Queue()
        self.message_log     = []          # (text, tag, timestamp)
        self.current_status  = ("10-8", "IN SERVICE", "ok")
        self.current_mode    = "MAIN"      # MAIN, QUERY_PLATE, QUERY_PERSON, STATUS, MESSAGES, HELP
        self.query_buffer    = ""
        self.blink_state     = True
        self.pending_ack     = False
        self.last_incident   = None
        self.boot_done       = False
        self.scan_offset     = 0
        self.input_history   = []
        self.hist_idx        = -1
        self.unread_count    = 0
        self.demo_running    = False      # True while demo scenario is active
        self.off_duty_pending = False     # True when waiting for Off Duty confirmation

        # Fonts  (use a monospace font for authentic terminal look)
        self._load_fonts()

        # Build UI
        self._build_bezel()
        self._build_screen()
        self._build_keyboard_bar()

        # Bind keys
        self._bind_keys()

        # Start background threads
        self._start_threads()

        # Motorola splash screen → then boot sequence
        self.after(200, self._show_splash)

    # ─────────────────────────────────────────
    #  FONT LOADING
    # ─────────────────────────────────────────
    def _load_fonts(self):
        # Prefer Courier or Fixedsys for authentic terminal feel
        available = list(tkfont.families())
        mono_candidates = [
            "Fixedsys", "Courier New", "Courier", "Lucida Console",
            "Terminal", "DejaVu Sans Mono", "Liberation Mono",
            "Consolas", "Monospace",
        ]
        mono = next((f for f in mono_candidates if f in available), "Courier")
        self.font_main   = tkfont.Font(family=mono, size=11, weight="normal")
        self.font_bold   = tkfont.Font(family=mono, size=11, weight="bold")
        self.font_small  = tkfont.Font(family=mono, size=9,  weight="normal")
        self.font_header = tkfont.Font(family=mono, size=12, weight="bold")
        self.font_alert  = tkfont.Font(family=mono, size=13, weight="bold")
        self.font_title  = tkfont.Font(family=mono, size=10, weight="bold")
        self.font_key    = tkfont.Font(family=mono, size=9,  weight="bold")

    # ─────────────────────────────────────────
    #  BEZEL (outer frame)
    # ─────────────────────────────────────────
    def _build_bezel(self):
        self.bezel = tk.Frame(self, bg=P["bezel"], padx=16, pady=12)
        self.bezel.pack(fill="both", expand=True)

        # ── Top branding / control bar ───────────────────────────────
        brand = tk.Frame(self.bezel, bg=P["bezel_dark"], height=28)
        brand.pack(fill="x", pady=(0, 6))
        brand.pack_propagate(False)

        tk.Label(brand, text="MOTOROLA",
                 bg=P["bezel_dark"], fg=P["fg_dim"],
                 font=self.font_key).pack(side="left", padx=10, pady=4)
        tk.Label(brand, text=f"MDT 9100-T  ●  {CONFIG['AGENCY']}  ●  {CONFIG['TERMINAL_ID']}",
                 bg=P["bezel_dark"], fg=P["fg_dim"],
                 font=self.font_small).pack(side="left", padx=6, pady=4)

        # ── OFF DUTY button — always visible top-right ───────────────
        # A second press within 3 s confirms and exits (if CONFIRM_OFF_DUTY is True)
        self.off_duty_btn = tk.Button(
            brand,
            text="OFF DUTY",
            command=self._off_duty_pressed,
            bg=P["bezel_dark"], fg=P["fg_dim"],
            activebackground="#552200", activeforeground=P["fg_alert"],
            font=self.font_key,
            relief="raised", bd=1,
            padx=8, pady=1,
            cursor="hand2",
        )
        self.off_duty_btn.pack(side="right", padx=10, pady=3)

    # ─────────────────────────────────────────
    #  SCREEN AREA
    # ─────────────────────────────────────────
    def _build_screen(self):
        # Outer glow border
        self.screen_frame = tk.Frame(self.bezel, bg=P["border"], bd=3, relief="sunken")
        self.screen_frame.pack(fill="both", expand=True)

        inner = tk.Frame(self.screen_frame, bg=P["bg"], padx=4, pady=4)
        inner.pack(fill="both", expand=True)

        # ── HEADER ROW ──────────────────────────────────
        hdr = tk.Frame(inner, bg=P["bg"])
        hdr.pack(fill="x")

        self.lbl_agency = tk.Label(hdr, text=CONFIG["AGENCY"],
            bg=P["bg"], fg=P["fg_header"], font=self.font_header, anchor="w")
        self.lbl_agency.pack(side="left", padx=4)

        self.lbl_unit = tk.Label(hdr, text=f"UNIT: {CONFIG['UNIT_ID']}",
            bg=P["bg"], fg=P["fg_bright"], font=self.font_bold, anchor="w")
        self.lbl_unit.pack(side="left", padx=12)

        self.lbl_beat = tk.Label(hdr, text=CONFIG["BEAT"],
            bg=P["bg"], fg=P["fg_dim"], font=self.font_main, anchor="w")
        self.lbl_beat.pack(side="left", padx=4)

        self.lbl_time = tk.Label(hdr, text="00:00:00",
            bg=P["bg"], fg=P["fg_bright"], font=self.font_header, anchor="e")
        self.lbl_time.pack(side="right", padx=4)

        self.lbl_date = tk.Label(hdr, text="",
            bg=P["bg"], fg=P["fg_dim"], font=self.font_main, anchor="e")
        self.lbl_date.pack(side="right", padx=8)

        # ── STATUS ROW ──────────────────────────────────
        status_frame = tk.Frame(inner, bg=P["border"], height=2)
        status_frame.pack(fill="x", pady=(2,0))

        stat = tk.Frame(inner, bg=P["bg"])
        stat.pack(fill="x", pady=(2,4))

        tk.Label(stat, text="STATUS:", bg=P["bg"], fg=P["fg_dim"],
                 font=self.font_small).pack(side="left", padx=4)
        self.lbl_status_code = tk.Label(stat, text="10-8",
            bg=P["bg"], fg=P["status_ok"], font=self.font_bold)
        self.lbl_status_code.pack(side="left")
        self.lbl_status_text = tk.Label(stat, text="IN SERVICE",
            bg=P["bg"], fg=P["status_ok"], font=self.font_bold)
        self.lbl_status_text.pack(side="left", padx=8)

        self.lbl_channel = tk.Label(stat, text=f"{CONFIG['CHANNEL']}  {CONFIG['FREQ']}MHz",
            bg=P["bg"], fg=P["fg_dim"], font=self.font_small)
        self.lbl_channel.pack(side="left", padx=16)

        self.lbl_signal = tk.Label(stat, text="◆◆◆◆◇  SIGNAL",
            bg=P["bg"], fg=P["fg_dim"], font=self.font_small)
        self.lbl_signal.pack(side="right", padx=4)

        self.lbl_unread = tk.Label(stat, text="",
            bg=P["bg"], fg=P["fg_alert"], font=self.font_bold)
        self.lbl_unread.pack(side="right", padx=8)

        self.lbl_cad = tk.Label(stat, text=f"CAD: {CONFIG['CAD_SERVER']}  ●ONLINE",
            bg=P["bg"], fg=P["fg_dim"], font=self.font_small)
        self.lbl_cad.pack(side="right", padx=8)

        # ── SEPARATOR ──
        tk.Frame(inner, bg=P["border"], height=1).pack(fill="x")

        # ── MODE INDICATOR BAR ──────────────────────────
        self.mode_bar = tk.Frame(inner, bg=P["key_bg"], height=20)
        self.mode_bar.pack(fill="x")
        self.mode_bar.pack_propagate(False)
        self.lbl_mode = tk.Label(self.mode_bar,
            text="◀  MAIN MENU  ▶", bg=P["key_bg"], fg=P["fg_header"],
            font=self.font_title)
        self.lbl_mode.pack(side="left", padx=8)
        self.lbl_mode_hint = tk.Label(self.mode_bar,
            text="TYPE COMMAND OR F-KEY", bg=P["key_bg"], fg=P["fg_dim"],
            font=self.font_small)
        self.lbl_mode_hint.pack(side="right", padx=8)

        # ── MAIN MESSAGE / DISPLAY AREA ──────────────────
        txt_frame = tk.Frame(inner, bg=P["bg"])
        txt_frame.pack(fill="both", expand=True, pady=(2,0))

        self.txt = tk.Text(txt_frame,
            bg=P["bg"], fg=P["fg"],
            font=self.font_main,
            insertbackground=P["cursor"],
            selectbackground=P["fg_dim"],
            selectforeground=P["bg"],
            relief="flat", bd=0,
            wrap="word",
            cursor="none",
            state="disabled",
            spacing1=2, spacing3=2,
        )
        self.txt.pack(side="left", fill="both", expand=True)

        sb = tk.Scrollbar(txt_frame, orient="vertical",
                          command=self.txt.yview,
                          bg=P["key_bg"], troughcolor=P["bg"],
                          activebackground=P["fg_dim"])
        sb.pack(side="right", fill="y")
        self.txt.configure(yscrollcommand=sb.set)

        # Configure text tags
        self._setup_text_tags()

        # ── INPUT ROW ────────────────────────────────────
        tk.Frame(inner, bg=P["border"], height=1).pack(fill="x", pady=(2,0))

        inp_frame = tk.Frame(inner, bg=P["input_bg"], pady=3)
        inp_frame.pack(fill="x")

        self.lbl_prompt = tk.Label(inp_frame, text="CMD>",
            bg=P["input_bg"], fg=P["fg_header"], font=self.font_bold)
        self.lbl_prompt.pack(side="left", padx=(6,2))

        self.input_var = tk.StringVar()
        self.entry = tk.Entry(inp_frame,
            textvariable=self.input_var,
            bg=P["input_bg"], fg=P["fg"],
            insertbackground=P["cursor"],
            font=self.font_bold,
            relief="flat", bd=0,
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=4)
        self.entry.focus_set()

        self.lbl_cursor_blink = tk.Label(inp_frame, text="█",
            bg=P["input_bg"], fg=P["cursor"], font=self.font_bold)
        self.lbl_cursor_blink.pack(side="left")

    # ─────────────────────────────────────────
    #  KEYBOARD / FUNCTION KEY BAR
    #  Labels match the real MDT 9100-T hardware
    # ─────────────────────────────────────────
    def _build_keyboard_bar(self):
        kbar = tk.Frame(self.bezel, bg=P["bezel_dark"], pady=6)
        kbar.pack(fill="x", pady=(6,0))

        # Real hardware key labels from Motorola MDT 9100-T (matched from unit photo)
        self.fkey_defs = [
            ("F1",  "ACK",      self._fkey_ack),           # Acknowledge message
            ("F2",  "MSGS",     self._fkey_messages),      # Message log
            ("F3",  "SCENE",    lambda: self._set_status("10-97","ON SCENE","warn")),
            ("F4",  "10-CODES", self._fkey_tencodes),      # Reference
            ("F5",  "OUTSVC",   lambda: self._set_status("10-7","OUT OF SERVICE","warn")),
            ("F6",  "TRNSPT",   lambda: self._set_status("10-76","EN ROUTE","ok")),
            ("F7",  "CLR/10-8", lambda: self._set_status("10-8","IN SERVICE","ok")),
            ("F8",  "VEH",      self._fkey_plate),         # Vehicle / plate query
            ("F9",  "PERSON",   self._fkey_person),        # Person / DL query
            ("F10", "CLEAR",    self._fkey_clear),
            ("F11", "T-STOP",   self._fkey_tstop),         # Traffic stop
            ("F12", "ONVIEW",   self._fkey_onview),        # On-view / self-initiated
        ]
        self.fkey_btns = []
        for label, desc, cmd in self.fkey_defs:
            col = tk.Frame(kbar, bg=P["bezel_dark"])
            col.pack(side="left", padx=2)
            tk.Label(col, text=label,
                     bg=P["bezel_dark"], fg=P["fg_dim"], font=self.font_small
                     ).pack()
            btn = tk.Button(col, text=desc, command=cmd,
                bg=P["key_bg"], fg=P["key_fg"],
                activebackground=P["key_active"], activeforeground=P["bg"],
                font=self.font_key,
                relief="raised", bd=1, padx=3, pady=2,
                cursor="hand2",
            )
            btn.pack()
            self.fkey_btns.append(btn)

        # EMER button — red physical button on real hardware (right side)
        tk.Frame(kbar, bg=P["bezel_dark"]).pack(side="left", expand=True)
        em_col = tk.Frame(kbar, bg=P["bezel_dark"])
        em_col.pack(side="right", padx=8)
        tk.Label(em_col, text="EMER",
                 bg=P["bezel_dark"], fg=P["fg_alert"], font=self.font_small).pack()
        tk.Button(em_col, text="10-33",
            command=self._fkey_emergency,
            bg="#CC0000", fg="white",
            activebackground="#FF2200", activeforeground="white",
            font=self.font_key, relief="raised", bd=2,
            padx=8, pady=3, cursor="hand2",
        ).pack()

    # ─────────────────────────────────────────
    #  TEXT TAGS (colour coding)
    # ─────────────────────────────────────────
    def _setup_text_tags(self):
        self.txt.tag_config("normal",    foreground=P["fg"],        font=self.font_main)
        self.txt.tag_config("bright",    foreground=P["fg_bright"],  font=self.font_bold)
        self.txt.tag_config("dim",       foreground=P["fg_dim"],     font=self.font_small)
        self.txt.tag_config("header",    foreground=P["fg_header"],  font=self.font_bold)
        self.txt.tag_config("alert",     foreground=P["fg_alert"],   font=self.font_alert)
        self.txt.tag_config("ok",        foreground=P["fg_ok"],      font=self.font_bold)
        self.txt.tag_config("separator", foreground=P["fg_dim"],     font=self.font_small)
        self.txt.tag_config("timestamp", foreground=P["fg_dim"],     font=self.font_small)
        self.txt.tag_config("input_echo",foreground=P["fg_dim"],     font=self.font_main)
        self.txt.tag_config("warn",      foreground=P["status_warn"],font=self.font_bold)

    # ─────────────────────────────────────────
    #  KEY BINDINGS  (match real hardware layout)
    # ─────────────────────────────────────────
    def _bind_keys(self):
        self.entry.bind("<Return>",    self._on_enter)
        self.entry.bind("<Up>",        self._hist_up)
        self.entry.bind("<Down>",      self._hist_down)
        self.entry.bind("<Escape>",    self._escape_pressed)
        self.bind("<F1>",  lambda e: self._fkey_ack())       # ACK
        self.bind("<F2>",  lambda e: self._fkey_messages())  # MSGS
        self.bind("<F3>",  lambda e: self._set_status("10-97","ON SCENE","warn"))  # SCENE
        self.bind("<F4>",  lambda e: self._fkey_tencodes())  # 10-CODES
        self.bind("<F5>",  lambda e: self._set_status("10-7","OUT OF SERVICE","warn"))  # OUTSVC
        self.bind("<F6>",  lambda e: self._set_status("10-76","EN ROUTE","ok"))    # TRNSPT
        self.bind("<F7>",  lambda e: self._set_status("10-8","IN SERVICE","ok"))   # CLR
        self.bind("<F8>",  lambda e: self._fkey_plate())     # VEH
        self.bind("<F9>",  lambda e: self._fkey_person())    # PERSON
        self.bind("<F10>", lambda e: self._fkey_clear())     # CLEAR
        self.bind("<F11>", lambda e: self._fkey_tstop())     # T-STOP
        self.bind("<F12>", lambda e: self._fkey_onview())    # ONVIEW
        # Ctrl+E triggers EMER (since the red button has no F-key equivalent)
        self.bind("<Control-e>", lambda e: self._fkey_emergency())
        # Ctrl+D = Off Duty shortcut
        self.bind("<Control-d>", lambda e: self._off_duty_pressed())

    # ─────────────────────────────────────────
    #  BACKGROUND THREADS
    # ─────────────────────────────────────────
    def _start_threads(self):
        # Clock updater
        self._clock_tick()
        # Blink cursor/alerts
        self._blink_tick()
        # Dispatch simulator
        if CONFIG["AUTO_DISPATCH"]:
            self.after(CONFIG["DISPATCH_INTERVAL"] * 1000, self._dispatch_sim_tick)
        # Signal strength animator
        self._signal_tick()
        # Process incoming message queue
        self._process_msg_queue()

    def _clock_tick(self):
        now = datetime.datetime.now()
        self.lbl_time.config(text=now.strftime("%H:%M:%S"))
        self.lbl_date.config(text=now.strftime("%a %m/%d/%Y"))
        self.after(1000, self._clock_tick)

    def _blink_tick(self):
        self.blink_state = not self.blink_state
        # Cursor blink
        self.lbl_cursor_blink.config(
            text="█" if self.blink_state else " ")
        # Alert blink
        if self.pending_ack:
            col = P["fg_alert"] if self.blink_state else P["bg"]
            self.lbl_unread.config(fg=col)
        self.after(600, self._blink_tick)

    def _signal_tick(self):
        # Simulate slight signal fluctuation
        bars = random.randint(3, 5)
        full  = "◆" * bars
        empty = "◇" * (5 - bars)
        self.lbl_signal.config(text=f"{full}{empty}  SIGNAL")
        self.after(random.randint(8000, 20000), self._signal_tick)

    def _process_msg_queue(self):
        try:
            while True:
                item = self.msg_queue.get_nowait()
                lines, tag, alert = item
                self._append_message(lines, tag, alert)
        except queue.Empty:
            pass
        self.after(200, self._process_msg_queue)

    def _dispatch_sim_tick(self):
        if not self.boot_done:
            self.after(CONFIG["DISPATCH_INTERVAL"] * 1000, self._dispatch_sim_tick)
            return
        r = random.random()
        if r < 0.25:
            lines, priority = generate_assignment_for_unit()
            tag = "alert" if priority == 1 else "header"
            self.msg_queue.put((lines, tag, True))
            self.pending_ack = True
        else:
            lines, priority = generate_dispatch_call()
            tag = "alert" if priority == 1 else "normal"
            self.msg_queue.put((lines, tag, priority == 1))
        # Schedule next
        jitter = random.randint(-15, 30)
        interval = max(20, CONFIG["DISPATCH_INTERVAL"] + jitter)
        self.after(interval * 1000, self._dispatch_sim_tick)

    # ─────────────────────────────────────────
    #  TEXT OUTPUT HELPERS
    # ─────────────────────────────────────────
    def _write(self, text, tag="normal", newline=True):
        self.txt.config(state="normal")
        if newline:
            self.txt.insert("end", text + "\n", tag)
        else:
            self.txt.insert("end", text, tag)
        self.txt.config(state="disabled")
        self.txt.see("end")

    def _write_separator(self, char="─", width=64):
        self._write(char * width, "separator")

    def _write_timestamp(self):
        ts = datetime.datetime.now().strftime("[%H:%M:%S %m/%d/%Y]")
        self._write(f"  {ts}", "timestamp")

    def _append_message(self, lines, base_tag="normal", alert=False):
        self._write_separator()
        self._write_timestamp()
        for line in lines:
            if line.startswith("!!!"):
                self._write(line, "alert")
            elif line.startswith("***"):
                self._write(line, "header")
            elif line.startswith("---"):
                self._write("─" * 40, "separator")
            else:
                self._write(line, base_tag)
        self._write_separator()
        self.unread_count += 1
        self.lbl_unread.config(text=f"  ◉ {self.unread_count} UNREAD" if self.unread_count > 0 else "")
        if alert:
            beep(self)

    def _clear_screen(self):
        self.txt.config(state="normal")
        self.txt.delete("1.0", "end")
        self.txt.config(state="disabled")

    def _set_mode(self, mode, hint=""):
        self.current_mode = mode
        labels = {
            "MAIN":         "◀  MAIN MENU  ▶",
            "QUERY_PLATE":  "◀  PLATE QUERY  ▶",
            "QUERY_PERSON": "◀  PERSON / DL QUERY  ▶",
            "STATUS":       "◀  UNIT STATUS  ▶",
            "MESSAGES":     "◀  MESSAGES  ▶",
            "HELP":         "◀  10-CODES REFERENCE  ▶",
        }
        self.lbl_mode.config(text=labels.get(mode, f"◀  {mode}  ▶"))
        self.lbl_mode_hint.config(text=hint or "TYPE COMMAND OR F-KEY")
        prompts = {
            "QUERY_PLATE":  "PLATE>",
            "QUERY_PERSON": "NAME>",
            "STATUS":       "STATUS>",
        }
        self.lbl_prompt.config(text=prompts.get(mode, "CMD>"))
        self.input_var.set("")
        self.entry.focus_set()

    # ─────────────────────────────────────────
    #  STATUS MANAGEMENT
    # ─────────────────────────────────────────
    def _set_status(self, code, text, level):
        self.current_status = (code, text, level)
        color = P[f"status_{level}"]
        self.lbl_status_code.config(text=code, fg=color)
        self.lbl_status_text.config(text=text, fg=color)
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._write(f"STATUS CHANGE >> {code} - {text}  ({ts})", "bright")

    # ─────────────────────────────────────────
    #  SPLASH SCREEN
    #  Matches the real MDT 9100-T power-on screen:
    #  Motorola batwing-M logo, model, and tagline
    # ─────────────────────────────────────────
    def _show_splash(self):
        """Display the Motorola splash screen, then transition to boot sequence."""
        self._clear_screen()
        # Splash art — rendered line by line with staggered delays
        # The circle + M logo mimics the amber phosphor splash on real hardware
        art = [
            # (text,                                                          tag,      delay_ms)
            ("",                                                               "normal",  0),
            ("",                                                               "normal",  0),
            ("     ╔══════════════════════════════════════════════════════╗",  "dim",    30),
            ("     ║                                                      ║",  "dim",    20),
            ("     ║          ╭──────────────────────────╮               ║",  "bright", 30),
            ("     ║          │                          │               ║",  "bright", 20),
            ("     ║          │      |╲           /|     │               ║",  "bright", 40),
            ("     ║          │      | ╲         / |     │               ║",  "bright", 40),
            ("     ║          │      |  ╲       /  |     │               ║",  "bright", 40),
            ("     ║          │      |   ╲     /   |     │               ║",  "bright", 40),
            ("     ║          │      |    ╲   /    |     │               ║",  "bright", 40),
            ("     ║          │      |     ╲ /     |     │               ║",  "bright", 40),
            ("     ║          │      |      V      |     │               ║",  "bright", 40),
            ("     ║          │      |             |     │               ║",  "bright", 20),
            ("     ║          ╰──────────────────────────╯               ║",  "bright", 30),
            ("     ║                                                      ║",  "dim",    20),
            ("     ║         M  O  T  O  R  O  L  A                     ║",  "header", 60),
            ("     ║                                                      ║",  "dim",    20),
            ("     ║                   9 1 0 0 - T                       ║",  "bright", 60),
            ("     ║                                                      ║",  "dim",    20),
            ("     ║             Mobile  Data  Terminal                   ║",  "normal", 60),
            ("     ║                                                      ║",  "dim",    20),
            ("     ║          Copyright  (C)  1985  Motorola Inc.        ║",  "dim",    60),
            ("     ║            Schaumburg, Illinois  60196               ║",  "dim",    40),
            ("     ║                                                      ║",  "dim",    20),
            ("     ╚══════════════════════════════════════════════════════╝",  "dim",    30),
            ("",                                                               "normal",  0),
        ]
        self._run_splash(art, 0)

    def _run_splash(self, art, idx):
        if idx >= len(art):
            # Pause on the completed splash, then clear and boot
            self.after(2200, self._launch_boot)
            return
        text, tag, delay = art[idx]
        self._write(text, tag)
        self.after(delay, lambda: self._run_splash(art, idx + 1))

    def _launch_boot(self):
        """Clear splash and begin the hardware self-test boot sequence."""
        self._clear_screen()
        self.after(150, self._boot_sequence)

    # ─────────────────────────────────────────
    #  BOOT SEQUENCE
    # ─────────────────────────────────────────
    def _boot_sequence(self):
        boot_lines = [
            ("MOTOROLA COMMUNICATIONS INC.",                     "bright", 80),
            ("MDT 9100-T  MOBILE DATA TERMINAL",                 "header", 80),
            ("FIRMWARE VERSION 3.2.1  (C) 1985 MOTOROLA",        "dim",    80),
            ("",                                                  "normal", 40),
            ("INITIATING SELF-TEST...",                           "normal", 300),
            ("  ROM CHECKSUM.............. PASS",                 "ok",     150),
            ("  RAM TEST (32K)............ PASS",                 "ok",     150),
            ("  DISPLAY CONTROLLER........ PASS",                 "ok",     150),
            ("  KEYBOARD INTERFACE........ PASS",                 "ok",     150),
            ("  MODEM / RADIO LINK........ PASS",                 "ok",     200),
            ("  CAD NETWORK INTERFACE..... PASS",                 "ok",     200),
            ("  NCIC / CJIS LINK.......... PASS",                 "ok",     200),
            ("",                                                  "normal", 50),
            (f"UNIT ID:   {CONFIG['UNIT_ID']}",                   "bright", 80),
            (f"AGENCY:    {CONFIG['AGENCY']}",                    "bright", 80),
            (f"BEAT:      {CONFIG['BEAT']}",                      "bright", 80),
            (f"TERMINAL:  {CONFIG['TERMINAL_ID']}",               "dim",    80),
            (f"CAD HOST:  {CONFIG['CAD_SERVER']}",                "dim",    80),
            (f"CHANNEL:   {CONFIG['CHANNEL']}  {CONFIG['FREQ']}MHz","dim",  80),
            ("",                                                  "normal", 50),
            ("REGISTERING WITH DISPATCH...",                      "normal", 600),
            (f"DISPATCH ACKNOWLEDGES {CONFIG['UNIT_ID']} 10-8",   "ok",     80),
            ("",                                                  "normal", 50),
            ("SYSTEM READY.",                                     "bright", 100),
            ("─" * 64,                                            "separator", 80),
            ("",                                                  "normal", 200),
        ]
        self._run_boot(boot_lines, 0)

    def _run_boot(self, lines, idx):
        if idx >= len(lines):
            self.boot_done = True
            self._show_main_menu()
            # Kick off demo mode if configured
            if CONFIG["DEMO_MODE"]:
                delay_ms = CONFIG["DEMO_DELAY"] * 1000
                self.after(delay_ms, self._demo_start)
            return
        text, tag, delay = lines[idx]
        if text == "─" * 64:
            self._write_separator()
        else:
            self._write(text, tag)
        self.after(delay, lambda: self._run_boot(lines, idx + 1))

    def _show_main_menu(self):
        self._set_mode("MAIN", "SELECT OPTION OR TYPE COMMAND")
        code, txt, lvl = self.current_status
        self._write_separator("═")
        self._write(f"  MDT 9100-T  MAIN MENU  |  {CONFIG['AGENCY']}  {CONFIG['UNIT_ID']}", "header")
        self._write_separator("═")
        self._write_timestamp()
        self._write(f"  CURRENT STATUS: {code} - {txt}", "bright" if lvl == "ok" else "warn")
        self._write("")
        self._write("  ┌──────────────────────────────────────────────┐", "dim")
        self._write("  │  F1  MESSAGES          F2  PLATE QUERY       │", "normal")
        self._write("  │  F3  PERSON/DL QUERY   F4  10-CODES REF      │", "normal")
        self._write("  │  F5  CHANGE STATUS     F6  SET 10-8 CLEAR    │", "normal")
        self._write("  │  F7  SET 10-97 SCENE   F8  SET 10-76 EN RT   │", "normal")
        self._write("  │  F9  MAIN MENU         F10 CLEAR SCREEN      │", "normal")
        self._write("  │  F12 / EMERG BUTTON    EMERGENCY 10-33       │", "alert")
        self._write("  └──────────────────────────────────────────────┘", "dim")
        self._write("")
        self._write("  COMMANDS: PLATE [#], PERSON [NAME], STATUS, MSGS", "dim")
        self._write("            ACK, CLEAR, HELP, TIME, ABOUT, DEMO", "dim")
        if CONFIG["DEMO_MODE"]:
            self._write("  ◉ DEMO MODE ACTIVE  —  TYPE 'DEMO' TO RUN SCENARIO", "header")
        self._write_separator()

    # ─────────────────────────────────────────
    #  FUNCTION KEY HANDLERS
    # ─────────────────────────────────────────
    def _fkey_main(self):
        self._show_main_menu()

    def _fkey_messages(self):
        self._set_mode("MESSAGES", "PRESS ESC TO RETURN")
        self._write_separator("═")
        self._write("  MESSAGE CENTER", "header")
        self._write_separator("═")
        self._write(f"  UNIT: {CONFIG['UNIT_ID']}  |  UNREAD: {self.unread_count}", "bright")
        self._write("")
        self._write("  ALL MESSAGES ARE LOGGED ABOVE. SCROLL TO REVIEW.", "dim")
        self._write("  TYPE 'ACK' TO ACKNOWLEDGE PENDING ASSIGNMENT.", "dim")
        self._write("")
        self.unread_count = 0
        self.lbl_unread.config(text="")
        self.pending_ack = False
        self._write_separator()

    def _fkey_plate(self):
        self._set_mode("QUERY_PLATE", "ENTER: STATE/PLATE  (EX: MA/2ABC123)  ESC=BACK")
        self._write_separator()
        self._write("  PLATE / VEHICLE QUERY  —  NCIC / CJIS", "header")
        self._write("  FORMAT: [STATE]/[PLATE NUMBER]", "dim")
        self._write("  EXAMPLE: MA/2ABC123  or  just plate: 2ABC123", "dim")
        self._write_separator()

    def _fkey_person(self):
        self._set_mode("QUERY_PERSON", "ENTER: LAST,FIRST DOB  (EX: SMITH,JOHN 04/15/51)  ESC=BACK")
        self._write_separator()
        self._write("  PERSON / DRIVER LICENSE QUERY  —  NCIC / CJIS", "header")
        self._write("  FORMAT: LAST,FIRST [DOB]  or  DL [NUMBER]", "dim")
        self._write("  EXAMPLE: JONES,MICHAEL  or  DL J444112233", "dim")
        self._write_separator()

    def _fkey_tencodes(self):
        self._set_mode("HELP", "ESC=BACK")
        self._write_separator("═")
        self._write("  10-CODE QUICK REFERENCE", "header")
        self._write_separator("═")
        items = list(TEN_CODES.items())
        for i in range(0, len(items), 2):
            left  = f"  {items[i][0]:<8} {items[i][1]:<28}"
            right = f"  {items[i+1][0]:<8} {items[i+1][1]}" if i+1 < len(items) else ""
            self._write(left + right, "normal")
        self._write_separator()

    def _fkey_status(self):
        self._set_mode("STATUS", "ENTER NUMBER (1-8) TO CHANGE STATUS  ESC=BACK")
        self._write_separator("═")
        self._write("  UNIT STATUS SELECTION", "header")
        self._write_separator("═")
        for i, (code, txt, lvl) in enumerate(UNIT_STATUSES):
            mark = " ◄ CURRENT" if (code, txt, lvl) == self.current_status else ""
            tag = "bright" if (code, txt, lvl) == self.current_status else "normal"
            self._write(f"  [{i+1}]  {code:<8} {txt}{mark}", tag)
        self._write_separator()

    def _fkey_clear(self):
        self._clear_screen()
        self._write(f"  SCREEN CLEARED  {datetime.datetime.now().strftime('%H:%M:%S')}", "dim")

    def _fkey_emergency(self):
        self._set_status("10-33", "EMERGENCY", "alert")
        lines = [
            "!!! EMERGENCY — 10-33 ACTIVATED !!!",
            f"UNIT: {CONFIG['UNIT_ID']}  |  {CONFIG['BEAT']}",
            f"TIME: {datetime.datetime.now().strftime('%H:%M:%S')}",
            "DISPATCH NOTIFIED — BACKUP REQUESTED",
            "ALL AVAILABLE UNITS RESPOND",
        ]
        self._append_message(lines, "alert", alert=True)
        beep(self)

    # ─────────────────────────────────────────
    #  COMMAND INPUT HANDLER
    # ─────────────────────────────────────────
    def _on_enter(self, event=None):
        raw = self.input_var.get().strip()
        if not raw:
            return
        # Any typed command cancels a pending Off Duty confirmation
        if self.off_duty_pending:
            self._off_duty_cancel()
        cmd = raw.upper()
        self.input_history.insert(0, raw)
        self.hist_idx = -1
        self.input_var.set("")
        self._write(f"  ► {raw}", "input_echo")

        # ── MODE-SPECIFIC INPUT ──────────────────
        if self.current_mode == "QUERY_PLATE":
            self._do_plate_query(cmd)
            return
        if self.current_mode == "QUERY_PERSON":
            self._do_person_query(cmd)
            return
        if self.current_mode == "STATUS":
            if cmd.isdigit():
                idx = int(cmd) - 1
                if 0 <= idx < len(UNIT_STATUSES):
                    code, txt, lvl = UNIT_STATUSES[idx]
                    self._set_status(code, txt, lvl)
                    self._fkey_main()
                else:
                    self._write("  INVALID SELECTION", "warn")
            else:
                self._write("  ENTER NUMBER 1-8", "warn")
            return

        # ── GLOBAL COMMANDS ─────────────────────
        if cmd.startswith("PLATE "):
            self._do_plate_query(cmd[6:])
        elif cmd.startswith("PERSON ") or cmd.startswith("DL "):
            self._do_person_query(cmd.split(" ",1)[1] if " " in cmd else "")
        elif cmd in ("MSGS", "MESSAGES", "MSG"):
            self._fkey_messages()
        elif cmd in ("MENU", "MAIN"):
            self._fkey_main()
        elif cmd in ("HELP", "10CODES", "10-CODES", "CODES"):
            self._fkey_tencodes()
        elif cmd in ("STATUS", "STAT"):
            self._fkey_status()
        elif cmd in ("CLEAR", "CLS"):
            self._fkey_clear()
        elif cmd == "ACK":
            self._cmd_ack()
        elif cmd == "TIME":
            ts = datetime.datetime.now().strftime("%H:%M:%S  %A %m/%d/%Y")
            self._write(f"  CURRENT TIME: {ts}", "bright")
        elif cmd in ("10-8", "108"):
            self._set_status("10-8", "IN SERVICE", "ok")
        elif cmd in ("10-97", "1097"):
            self._set_status("10-97", "ON SCENE", "warn")
        elif cmd in ("10-98", "1098"):
            self._set_status("10-98", "AVAILABLE", "ok")
        elif cmd in ("10-76", "1076"):
            self._set_status("10-76", "EN ROUTE", "ok")
        elif cmd in ("10-7", "107"):
            self._set_status("10-7", "OUT OF SERVICE", "warn")
        elif cmd in ("10-33", "1033"):
            self._fkey_emergency()
        elif cmd == "ABOUT":
            self._cmd_about()
        elif cmd in ("10-4", "104"):
            self._write("  10-4  ACKNOWLEDGED", "ok")
        elif cmd in ("SIMULATE", "SIM"):
            lines, p = generate_assignment_for_unit()
            self._append_message(lines, "header", True)
        elif cmd in ("DEMO",):
            if self.demo_running:
                self._write("  DEMO ALREADY RUNNING — PLEASE WAIT", "warn")
            else:
                self._demo_start()
        elif cmd.startswith("MSG "):
            self._cmd_send_msg(raw[4:])
        else:
            # Check if it's a 10-code lookup
            if cmd in TEN_CODES:
                self._write(f"  {cmd}: {TEN_CODES[cmd]}", "bright")
            else:
                self._write(f"  UNKNOWN COMMAND: {raw}", "warn")
                self._write("  TYPE 'HELP' FOR 10-CODES  |  F9=MAIN MENU", "dim")

    def _hist_up(self, event):
        if self.input_history and self.hist_idx < len(self.input_history)-1:
            self.hist_idx += 1
            self.input_var.set(self.input_history[self.hist_idx])
            self.entry.icursor("end")

    def _hist_down(self, event):
        if self.hist_idx > 0:
            self.hist_idx -= 1
            self.input_var.set(self.input_history[self.hist_idx])
        elif self.hist_idx == 0:
            self.hist_idx = -1
            self.input_var.set("")
        self.entry.icursor("end")

    # ─────────────────────────────────────────
    #  PLATE QUERY
    # ─────────────────────────────────────────
    def _do_plate_query(self, query):
        if not query:
            self._write("  NO PLATE ENTERED", "warn")
            return
        # Strip state prefix if present
        plate = query.replace("/", " ").split()[-1]  # take last token
        self._write(f"  QUERYING NCIC FOR PLATE: {plate}...", "dim")
        self.after(800 + random.randint(0, 600), lambda: self._plate_response(plate))

    def _plate_response(self, plate):
        # Try to find matching plate in fake data, otherwise generate random
        match = next((d for d in PLATE_DATA if d["plate"].upper() == plate.upper()), None)
        if match is None:
            match = random.choice(PLATE_DATA)
            match = dict(match)
            match["plate"] = plate.upper()
        lines = format_plate_response(match)
        is_alert = match["wants"] != "NONE" or match["stolen"] != "NO"
        self._append_message(lines, "alert" if is_alert else "ok", is_alert)

    # ─────────────────────────────────────────
    #  PERSON QUERY
    # ─────────────────────────────────────────
    def _do_person_query(self, query):
        if not query:
            self._write("  NO NAME/DL ENTERED", "warn")
            return
        self._write(f"  QUERYING NCIC FOR: {query}...", "dim")
        self.after(900 + random.randint(0, 700), lambda: self._person_response(query))

    def _person_response(self, query):
        match = next((d for d in PERSON_DATA
                      if query.upper().split(",")[0] in d["name"].upper()), None)
        if match is None:
            match = random.choice(PERSON_DATA)
        lines = format_person_response(match)
        is_alert = match["wants"] != "NONE"
        self._append_message(lines, "alert" if is_alert else "ok", is_alert)

    # ─────────────────────────────────────────
    #  MISC COMMANDS
    # ─────────────────────────────────────────
    def _cmd_ack(self):
        self.pending_ack = False
        self.unread_count = 0
        self.lbl_unread.config(text="")
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        lines = [
            f"*** ACKNOWLEDGEMENT FROM {CONFIG['UNIT_ID']} ***",
            f"10-4  MESSAGE RECEIVED  |  TIME: {ts}",
            f"UNIT STATUS: {self.current_status[0]} - {self.current_status[1]}",
        ]
        self._append_message(lines, "ok", False)

    def _cmd_send_msg(self, text):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        lines = [
            f"*** OUTBOUND MSG - {CONFIG['UNIT_ID']} TO DISPATCH ***",
            f"TIME: {ts}",
            f"MSG: {text.upper()}",
            "MESSAGE SENT TO CAD",
        ]
        self._append_message(lines, "bright", False)

    def _cmd_about(self):
        self._write_separator("═")
        self._write("  MOTOROLA MDT 9100-T EMULATOR", "header")
        self._write_separator("═")
        self._write("  Developed for the Saugus Police Department", "normal")
        self._write("  1989 Ford Crown Victoria LTD Restoration", "normal")
        self._write("  Emulates: Motorola 9100-T MDT Unit Computer", "normal")
        self._write("")
        self._write("  ─── QUICK COMMAND REFERENCE ─────────────────", "dim")
        self._write("  PLATE [plate]       Query vehicle / NCIC", "normal")
        self._write("  PERSON [name]       Query person / DL", "normal")
        self._write("  DL [number]         Query driver's license", "normal")
        self._write("  MSG [text]          Send message to dispatch", "normal")
        self._write("  ACK                 Acknowledge assignment", "normal")
        self._write("  STATUS or F5        Change unit status", "normal")
        self._write("  10-8/97/76/7/33     Set status by code", "normal")
        self._write("  SIM                 Simulate incoming call", "normal")
        self._write("  DEMO                Run full call scenario", "normal")
        self._write("  TIME                Display current time", "normal")
        self._write("  CLEAR               Clear screen", "normal")
        demo_state = "ENABLED" if CONFIG["DEMO_MODE"] else "DISABLED"
        self._write(f"  DEMO MODE:          {demo_state} (see CONFIG)", "dim")
        self._write_separator()

    # ─────────────────────────────────────────
    #  DEMO MODE ENGINE
    # ─────────────────────────────────────────
    def _demo_start(self):
        """Entry point — announce demo, then begin stepping through DEMO_STEPS."""
        if self.demo_running:
            return
        self.demo_running = True
        self._write_separator("═")
        self._write("  ◉ DEMO MODE — SCRIPTED CALL SCENARIO STARTING", "header")
        self._write(f"  UNIT: {CONFIG['UNIT_ID']}  |  BEAT: {CONFIG['BEAT']}", "bright")
        self._write("  SCENARIO: SUSPICIOUS VEHICLE — NW SAUGUS BEAT", "normal")
        self._write("  Watch the MDT walk through a complete call cycle:", "dim")
        self._write("  Dispatch → En Route → On Scene → NCIC → Arrest → Clear", "dim")
        self._write_separator("═")
        # Kick off step 0 immediately (its own pause_ms is ignored for first step)
        self.after(1000, lambda: self._demo_run_step(0))

    def _demo_run_step(self, idx):
        """Execute one demo step then schedule the next."""
        if idx >= len(DEMO_STEPS):
            # Scenario finished
            self.demo_running = False
            self._write_separator("═")
            self._write("  ◉ DEMO SCENARIO COMPLETE", "header")
            self._write("  Type DEMO to replay  |  All other commands active", "dim")
            self._write_separator("═")
            return

        pause_ms, step_type, *payload = DEMO_STEPS[idx]
        ts = datetime.datetime.now().strftime("%H:%M:%S")

        if step_type == "dispatch":
            # Incoming assignment — fill in live timestamp placeholder
            lines = [l.replace("{time}", ts) for l in payload[0]]
            self._append_message(lines, "header", True)
            self.pending_ack = True
            self.unread_count += 1

        elif step_type == "status":
            code, text, level = payload[0]
            self._set_status(code, text, level)
            # Auto-clear ACK when going en route
            if code in ("10-76", "10-8", "10-98"):
                self.pending_ack = False
                self.unread_count = max(0, self.unread_count - 1)
                self.lbl_unread.config(text="")

        elif step_type == "outmsg":
            lines = list(payload[0])
            lines.append(f"TIME: {ts}")
            self._append_message(lines, "bright", False)

        elif step_type == "inmsg":
            lines = list(payload[0])
            lines.append(f"TIME: {ts}")
            self._append_message(lines, "normal", False)
            self.unread_count += 1

        elif step_type == "plate":
            data = payload[0]
            lines = format_plate_response(data)
            is_alert = data["wants"] != "NONE" or data["stolen"] != "NO"
            self._append_message(lines, "alert" if is_alert else "ok", is_alert)

        elif step_type == "person":
            data = payload[0]
            lines = format_person_response(data)
            is_alert = data["wants"] != "NONE"
            self._append_message(lines, "alert" if is_alert else "ok", is_alert)

        elif step_type == "label":
            self._write(payload[0], "dim")

        # Schedule next step using its own pause_ms (or default step time)
        next_idx = idx + 1
        if next_idx < len(DEMO_STEPS):
            next_pause = DEMO_STEPS[next_idx][0] or CONFIG["DEMO_STEP_MS"]
        else:
            next_pause = CONFIG["DEMO_STEP_MS"]
        self.after(next_pause, lambda: self._demo_run_step(next_idx))

    def _fkey_ack(self):
        """F1 — ACK: Acknowledge the current pending message/assignment."""
        if self.pending_ack:
            self._cmd_ack()
        else:
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self._write(f"  10-4  {CONFIG['UNIT_ID']}  ({ts})", "ok")

    def _fkey_tstop(self):
        """F11 — T-STOP: Officer has initiated a traffic stop."""
        self._set_status("10-97", "ON SCENE / T-STOP", "warn")
        ts  = datetime.datetime.now().strftime("%H:%M:%S")
        lines = [
            f"*** {CONFIG['UNIT_ID']} — TRAFFIC STOP ***",
            f"TIME: {ts}",
            f"BEAT: {CONFIG['BEAT']}",
            "USE F8 (VEH) TO RUN PLATE",
            "USE F9 (PERSON) TO RUN OPERATOR",
            "CLR W/ F7 WHEN COMPLETE",
        ]
        self._append_message(lines, "bright", False)

    def _fkey_onview(self):
        """F12 — ONVIEW: Officer self-initiating a call."""
        self._set_status("10-97", "ON SCENE / ONVIEW", "warn")
        ts  = datetime.datetime.now().strftime("%H:%M:%S")
        lines = [
            f"*** {CONFIG['UNIT_ID']} — ON VIEW INCIDENT ***",
            f"TIME: {ts}",
            f"BEAT: {CONFIG['BEAT']}",
            "OFFICER SELF-INITIATED ACTIVITY",
            "ADVISE DISPATCH WITH DETAILS",
            "USE MSG [TEXT] TO SEND INFO TO DISPATCH",
            "CLR W/ F7 WHEN COMPLETE",
        ]
        self._append_message(lines, "bright", False)

    # ─────────────────────────────────────────
    #  FULLSCREEN TOGGLE
    # ─────────────────────────────────────────
    def _escape_pressed(self, event=None):
        """Escape: exit fullscreen if active, otherwise go to main menu."""
        if self.attributes("-fullscreen"):
            self.attributes("-fullscreen", False)
            self._write("  FULLSCREEN OFF  —  PRESS Escape AGAIN TO RESTORE", "dim")
        else:
            self._fkey_main()

    # ─────────────────────────────────────────
    #  OFF DUTY — SHUTDOWN
    # ─────────────────────────────────────────
    def _off_duty_pressed(self):
        """
        OFF DUTY button / Ctrl+D handler.
        If CONFIRM_OFF_DUTY is True: first press arms the button and starts a
        3-second countdown; a second press within that window confirms shutdown.
        If CONFIRM_OFF_DUTY is False: exits immediately on first press.
        """
        if not CONFIG["CONFIRM_OFF_DUTY"]:
            self._off_duty_confirm()
            return

        if self.off_duty_pending:
            # Second press within the window — confirmed, exit now
            self._off_duty_confirm()
        else:
            # First press — arm the confirmation countdown
            self.off_duty_pending = True
            self.off_duty_btn.config(
                text="CONFIRM?",
                bg="#552200",
                fg=P["fg_alert"],
            )
            self._write_separator()
            self._write("  OFF DUTY — PRESS 'OFF DUTY' AGAIN WITHIN 3 SECONDS TO CONFIRM", "alert")
            self._write("  PRESS ANY OTHER KEY OR WAIT TO CANCEL", "dim")
            self._write_separator()
            beep(self)
            # Auto-cancel after 3 seconds
            self._off_duty_cancel_id = self.after(3000, self._off_duty_cancel)

    def _off_duty_confirm(self):
        """Confirmed — broadcast 10-42, set status, then shut down."""
        if hasattr(self, "_off_duty_cancel_id"):
            self.after_cancel(self._off_duty_cancel_id)
        self.off_duty_pending = False
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        # Broadcast end of tour
        self._set_status("10-7", "OUT OF SERVICE", "warn")
        self._write_separator("═")
        self._write(f"  *** {CONFIG['UNIT_ID']} — 10-42 END OF TOUR ***", "header")
        self._write(f"  UNIT {CONFIG['UNIT_ID']} GOING OFF DUTY", "bright")
        self._write(f"  BEAT: {CONFIG['BEAT']}  |  TIME: {ts}", "normal")
        self._write("  CAD NOTIFIED — UNIT LOGGED OFF", "dim")
        self._write_separator("═")
        self.update()
        self.after(1800, self.destroy)

    def _off_duty_cancel(self):
        """Time expired or cancelled — restore the button to normal."""
        self.off_duty_pending = False
        self.off_duty_btn.config(
            text="OFF DUTY",
            bg=P["bezel_dark"],
            fg=P["fg_dim"],
        )
        self._write("  OFF DUTY CANCELLED", "dim")

    # ─────────────────────────────────────────
    #  SHUTDOWN
    # ─────────────────────────────────────────
    def on_close(self):
        self._write("  LOGGING OFF... UNIT OUT OF SERVICE", "warn")
        self.update()
        self.after(500, self.destroy)


# ═══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print("  MOTOROLA MDT 9100-T EMULATOR")
    print(f"  Agency:  {CONFIG['AGENCY']}")
    print(f"  Unit:    {CONFIG['UNIT_ID']}")
    print(f"  Python:  {sys.version.split()[0]}")
    print("  Starting terminal...")
    print("=" * 60)
    app = MDT9100T()
    app.mainloop()

if __name__ == "__main__":
    main()