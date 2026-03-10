# config.py
# User configuration and layout constants for the MicroPython weather station.
# Edit this file to change WiFi credentials, location, or display geometry.

# ── User Configuration ──────────────────────────────────────────────
WIFI_SSID     = "blinky"
WIFI_PASSWORD = "flim314flam159"
LATITUDE      = 39.08        # e.g. 25.77
LONGITUDE     = -77.16       # e.g. -80.19
LOCATION_NAME = "Rockville, MD"
REFRESH_SEC   = 600          # 10 minutes
UTC_OFFSET_H  = -4           # UTC-4 = EDT; change for your timezone
# ────────────────────────────────────────────────────────────────────

# Display dimensions
W = 792
H = 272

# Layout breakpoints
TOP_H  = 25   # top bar height; separator hline drawn at y=24
BOT_Y  = 245  # bottom bar start; separator hline drawn here
COL1_X = 400  # left ↔ centre panel divider
COL2_X = 600  # centre ↔ right panel divider
