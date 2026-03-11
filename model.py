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
        "wind_speed_10m,wind_direction_10m,weather_code"
        "&daily=sunrise,sunset"
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

    temp_c    = c.get("temperature_2m",        0.0)
    speed_kmh = c.get("wind_speed_10m",        0.0)
    press_hpa = c.get("surface_pressure",      0.0)

    return {
        "temp":       temp_c * 9 / 5 + 32,
        "humidity":   int(c.get("relative_humidity_2m", 0)),
        "pressure":   round(press_hpa * 0.02953, 2),
        "wind_speed": speed_kmh * 0.621371,
        "wind_dir":   int(c.get("wind_direction_10m",   0)),
        "code":       int(c.get("weather_code",         0)),
        "sunrise":    hhmm(d["sunrise"][0]),
        "sunset":     hhmm(d["sunset"][0]),
    }
