# viewmodel.py
# Transforms raw model data into display-ready strings and values.
# No screen access here — pure data formatting.

import time

import config


def _format_temperature(temp_f):
    """Return a 7-segment-compatible temperature string, e.g. '72oF' or '-5oF'."""
    t = int(round(temp_f))
    if t >= 0:
        return "{}oF".format(t)
    return "-{}oF".format(abs(t))


def format_city_temp(temp_f):
    """Return a plain-text temperature string for city-select list, e.g. '72F'."""
    t = int(round(temp_f))
    return "{}F".format(t)


def wmo_condition(code):
    """Return a short plain-text description for a WMO weather code."""
    if code == 0:
        return "Clear"
    if 1 <= code <= 3:
        return "Cloudy"
    if code in (45, 48):
        return "Fog"
    if (51 <= code <= 67) or (80 <= code <= 82):
        return "Rain"
    if 71 <= code <= 77:
        return "Snow"
    if code in (95, 96, 99):
        return "Thunder"
    return "Cloudy"


def _format_pressure(press_inHg):
    """Return pressure formatted to two decimal places, e.g. '29.92'."""
    return "{:.2f}".format(press_inHg)


def _pressure_trend(history):
    """Return a pressure trend label using linear regression over all readings.

    Requires at least 4 readings (≈40 min at 10-min refresh) before reporting
    a trend.  Using the best-fit slope across all points makes the result
    resistant to single-reading noise/outliers.

    Threshold: if the slope projects a total change of > 0.06 inHg
    (≈ 2 hPa — the standard meteorological 'rising/falling' threshold for a
    3-hour window) → Rising/Falling; otherwise Steady.
    """
    n = len(history)
    if n < 4:
        return "Pressure"
    # Simple linear regression: y = slope*x + c, x = sample index
    sx = sy = sxy = sx2 = 0
    for i, (_, pr) in enumerate(history):
        sx  += i
        sy  += pr
        sxy += i * pr
        sx2 += i * i
    denom = n * sx2 - sx * sx
    if denom == 0:
        return "Pressure-Steady"
    slope = (n * sxy - sx * sy) / denom   # inHg per step
    projected = slope * (n - 1)           # total fitted change over window
    if projected > 0.06:
        return "Pressure-Rising"
    if projected < -0.06:
        return "Pressure-Falling"
    return "Pressure-Steady"


def _format_wind_speed(mph):
    """Return wind speed string, e.g. '12.3 mph'."""
    return "{:.1f} mph".format(mph)


def _format_wind_gust(mph):
    """Return wind gust string, e.g. '18.5 mph'."""
    return "{:.1f} mph".format(mph)


def _format_time(utc_offset_h):
    """Return (time_str, date_str) shifted by utc_offset_h hours.

    RTC holds UTC after NTP sync; this converts to local time without
    requiring a full timezone library.
    Returns:
        time_str  e.g. "08:32:15 AM"
        date_str  e.g. "03/10/2026"
    """
    local = time.localtime(time.mktime(time.localtime()) + utc_offset_h * 3600)
    h    = local[3]
    am_pm = "AM" if h < 12 else "PM"
    h12  = h % 12 or 12
    time_str = "{:02d}:{:02d}:{:02d} {}".format(h12, local[4], local[5], am_pm)
    date_str = "{:02d}/{:02d}/{}".format(local[1], local[2], local[0])
    return time_str, date_str


def _format_12h(hhmm):
    """Convert "HH:MM" 24-hour string to zero-padded 12-hour "HH:MM AM/PM"."""
    h = int(hhmm[:2])
    m = hhmm[3:]
    am_pm = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return "{:02d}:{} {}".format(h12, m, am_pm)


def build_forecast_state(forecast_raw, city_name=None, utc_offset_h=None):
    """Convert a list of daily forecast dicts into a display-state dict for draw_forecast().

    Args:
        forecast_raw:  list returned by model.fetch_forecast()
        city_name:     display name for the location
        utc_offset_h:  UTC offset in hours for time formatting

    Returns:
        location  str
        time_str  str
        date_str  str
        days      list of dicts with keys: day, high_str, low_str, precip_str, condition_str
    """
    if city_name is None:
        city_name = config.LOCATION_NAME
    if utc_offset_h is None:
        utc_offset_h = config.UTC_OFFSET_H
    time_str, date_str = _format_time(utc_offset_h)
    days = []
    for d in forecast_raw:
        days.append({
            "day":           d["day"],
            "date":          d["date"],
            "high_str":      str(int(round(d["high"]))) + "F",
            "low_str":       str(int(round(d["low"])))  + "F",
            "precip_str":    str(d["precip_pct"]) + "%",
            "condition_str": wmo_condition(d["code"]),
        })
    return {
        "location": city_name,
        "time_str": time_str,
        "date_str": date_str,
        "days":     days,
    }


def build_display_state(raw, city_name=None, utc_offset_h=None, pressure_history=None):
    """Convert a raw model dict into a display-state dict consumed by the view.

    Args:
        raw:          dict returned by model.fetch_weather()
        city_name:    display name for the location (defaults to config.LOCATION_NAME)
        utc_offset_h: UTC offset in hours for time formatting (defaults to config.UTC_OFFSET_H)

    Returns a dict with every value already formatted for direct rendering:
        temp_str       str   e.g. "72oF"
        humidity       int   e.g. 55
        pressure_str   str   e.g. "29.92"
        wind_speed_str str   e.g. "12.3 mph"
        wind_dir       int   degrees
        weather_code   int   WMO code
        sunrise        str   "HH:MM AM/PM"
        sunset         str   "HH:MM AM/PM"
        time_str       str   "HH:MM:SS AM"
        date_str       str   "MM/DD/YYYY"
        location       str   location name
    """
    if city_name is None:
        city_name = config.LOCATION_NAME
    if utc_offset_h is None:
        utc_offset_h = config.UTC_OFFSET_H
    time_str, date_str = _format_time(utc_offset_h)
    return {
        "temp_str":       _format_temperature(raw["temp"]),
        "humidity":       raw["humidity"],
        "pressure_str":   _format_pressure(raw["pressure"]),
        "pressure_label": _pressure_trend(pressure_history or []),
        "wind_speed_str": _format_wind_speed(raw["wind_speed"]),
        "wind_gust_str":  _format_wind_gust(raw["wind_gust"]),
        "wind_dir":       raw["wind_dir"],
        "weather_code":   raw["code"],
        "condition_str":  wmo_condition(raw["code"]),
        "precip_pct_str": str(raw["precip_pct"]) + "%",
        "today_high_str": str(int(round(raw["today_high"]))) + "F",
        "today_low_str":  str(int(round(raw["today_low"])))  + "F",
        "sunrise":        _format_12h(raw["sunrise"]),
        "sunset":         _format_12h(raw["sunset"]),
        "time_str":       time_str,
        "date_str":       date_str,
        "location":       city_name,
        "rain_24h_str":   "{:.1f}".format(raw["rain_24h"]),
        "snow_24h_str":   "{:.1f}".format(raw["snow_24h"]),
    }
