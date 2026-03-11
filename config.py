# config.py
# User configuration and layout constants for the MicroPython weather station.
# Edit this file to change Wi-Fi credentials, location, or display geometry.

# ── User Configuration ──────────────────────────────────────────────
WIFI_SSID     = "blinky"
WIFI_PASSWORD = "flim314flam159"
LATITUDE      = 39.08        # e.g. 25.77
LONGITUDE     = -77.16       # e.g. -80.19
LOCATION_NAME = "Rockville, MD"
REFRESH_SEC   = 600          # 10 minutes
UTC_OFFSET_H  = -4           # UTC-4 = EDT; change for your timezone

# Rotary encoder GPIO pins (update to match your hardware)
ROT_UP    = 6
ROT_DOWN  = 4
ROT_CLICK = 5

# City list — each entry: (name, lat, lon, utc_offset_h)
CITIES = [
    ("Rockville, MD",    39.08,  -77.16,  -4),
    ("Missoula, MT",     46.87, -113.99,  -6),
    ("San Francisco, CA",37.77, -122.42,  -7),
    ("San Diego, CA",    32.72, -117.16,  -7),
    ("New York, NY",     40.71,  -74.01,  -4),
]
# ────────────────────────────────────────────────────────────────────

# Display dimensions
W = 792
H = 272

# Layout breakpoints
TOP_H  = 25   # top bar height; separator hline drawn at y=24
BOT_Y  = 245  # bottom bar start; separator hline drawn here
COL1_X = 400  # left ↔ centre panel divider
COL2_X = 600  # centre ↔ right panel divider
