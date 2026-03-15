# model.py
# Network I/O: Wi-Fi connection, NTP sync, and weather data fetching.

import network
import urequests
import time

import config


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return
    wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
    deadline = time.ticks_add(time.ticks_ms(), 15_000)
    while not wlan.isconnected():
        if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
            raise OSError("WiFi connect timeout")
        time.sleep_ms(500)
    print("WiFi:", wlan.ifconfig()[0])


def sync_ntp():
    try:
        import ntptime
        ntptime.settime()
        print("NTP time synced")
        return True
    except Exception as e:
        print("NTP skipped:", e)
        return False


def update_pressure_history(city_idx, pressure_inHg):
    """Append pressure_inHg to /press_N.txt, trim to 3-hour window, return history.

    Returns list of (timestamp_secs, pressure_inHg) — oldest first.
    Returns [] if the RTC has not been synced (time.time() < 1_000_000).
    """
    now = time.time()
    if now < 1_000_000:          # clock not yet synced — skip
        return []
    cutoff = now - 10800         # 3 hours ago
    fname = "/press_{}.txt".format(city_idx)

    # Load existing readings within the 3-hour window
    history = []
    try:
        with open(fname, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(",")
                if len(parts) == 2:
                    ts = int(parts[0])
                    if ts >= cutoff:
                        history.append((ts, float(parts[1])))
    except OSError:
        pass   # file doesn't exist yet — start fresh

    # Append new reading
    history.append((now, round(pressure_inHg, 2)))

    # Rewrite file (trim applied by only writing entries within window)
    try:
        with open(fname, "w") as f:
            for ts, pr in history:
                f.write("{},{}\n".format(ts, pr))
    except OSError as e:
        print("press history write error:", e)

    return history


def fetch_weather(lat, lon, utc_offset_h=None):
    """Fetch current conditions from Open-Meteo (free, no API key).

    Returns a plain dict with unit-converted values:
        temp        float  °F  (converted from °C)
        humidity    int    %
        pressure    float  inHg
        wind_speed  float  mph
        wind_dir    int    degrees (0=N, clockwise)
        code        int    WMO weather code
        sunrise     str    "HH:MM"
        sunset      str    "HH:MM"
    """
    url = (
        "http://api.open-meteo.com/v1/forecast"
        "?latitude={}&longitude={}"
        "&current=temperature_2m,relative_humidity_2m,surface_pressure,"
        "wind_speed_10m,wind_direction_10m,wind_gusts_10m,weather_code"
        "&daily=sunrise,sunset,precipitation_probability_max,"
        "temperature_2m_max,temperature_2m_min"
        "&timezone=auto&forecast_days=1"
    ).format(lat, lon)
    print("GET", url)
    resp = urequests.get(url)
    raw  = resp.json()
    resp.close()

    c = raw["current"]
    d = raw["daily"]

    def hhmm(iso):  # "2025-08-23T05:44" → "05:44"
        return iso[11:16] if len(iso) > 10 else iso[-5:]

    temp_c     = c.get("temperature_2m",        0.0)
    speed_kmh  = c.get("wind_speed_10m",        0.0)
    gusts_kmh  = c.get("wind_gusts_10m",        0.0)
    press_hpa  = c.get("surface_pressure",      0.0)

    precip  = d["precipitation_probability_max"][0]
    high_c  = d["temperature_2m_max"][0]
    low_c   = d["temperature_2m_min"][0]
    return {
        "temp":       temp_c * 9 / 5 + 32,
        "humidity":   int(c.get("relative_humidity_2m", 0)),
        "pressure":   round(press_hpa * 0.02953, 2),
        "wind_speed": speed_kmh * 0.621371,
        "wind_gust":  gusts_kmh * 0.621371,
        "wind_dir":   int(c.get("wind_direction_10m",   0)),
        "code":       int(c.get("weather_code",         0)),
        "sunrise":    hhmm(d["sunrise"][0]),
        "sunset":     hhmm(d["sunset"][0]),
        "precip_pct": int(precip) if precip is not None else 0,
        "today_high": high_c * 9 / 5 + 32,
        "today_low":  low_c  * 9 / 5 + 32,
    }


_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def fetch_forecast(lat, lon):
    """Fetch 5-day daily forecast from Open-Meteo.

    Returns a list of 5 dicts:
        day         str    e.g. "Mon"
        high        float  °F
        low         float  °F
        precip_pct  int    %
        code        int    WMO weather code
    """
    url = (
        "http://api.open-meteo.com/v1/forecast"
        "?latitude={}&longitude={}"
        "&daily=temperature_2m_max,temperature_2m_min,"
        "weather_code,precipitation_probability_max"
        "&forecast_days=6&timezone=auto"
    ).format(lat, lon)
    print("GET", url)
    resp = urequests.get(url)
    raw  = resp.json()
    resp.close()

    d = raw["daily"]
    result = []
    for i in range(6):
        date_str = d["time"][i]          # "2026-03-12"
        year  = int(date_str[0:4])
        month = int(date_str[5:7])
        mday  = int(date_str[8:10])
        weekday = time.localtime(time.mktime((year, month, mday, 0, 0, 0, 0, 0)))[6]
        high_c = d["temperature_2m_max"][i]
        low_c  = d["temperature_2m_min"][i]
        precip = d["precipitation_probability_max"][i]
        result.append({
            "day":        _DAYS[weekday],
            "date":       "{:02d}/{:02d}".format(month, mday),
            "high":       high_c * 9 / 5 + 32,
            "low":        low_c  * 9 / 5 + 32,
            "precip_pct": int(precip) if precip is not None else 0,
            "code":       int(d["weather_code"][i]),
        })
    return result
