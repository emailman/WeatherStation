# CLAUDE.md — WeatherStation project notes

## What this project is

MicroPython firmware for an Elecrow CrowPanel 5.79" e-paper weather station
(ESP32 + 792 × 272 px black/white display). Fetches live data from Open-Meteo
every 10 minutes and renders it in a fixed panel layout.

## Architecture: MVVM

```
config.py      constants only, zero imports
model.py       WiFi + NTP + HTTP fetch, returns plain dicts
viewmodel.py   string formatting, returns a display-state dict; also city-select helpers
view.py        all draw_* functions, consumes display-state dict
main.py        button/encoder ISRs + polling loop, wires the layers
```

**Layer boundaries to preserve:**
- `view.py` must never call `format()` or do unit conversion — only render
- `viewmodel.py` must never import `CrowPanel` or touch the screen object
- `model.py` must never import `view` or `viewmodel`
- `config.py` must have zero imports

## Key interfaces

### model.fetch_weather() → raw dict
```python
{
    "temp":       float,   # Fahrenheit (converted from °C)
    "humidity":   int,     # %
    "pressure":   float,   # inHg
    "wind_speed": float,   # mph (converted from km/h — Open-Meteo default)
    "wind_gust":  float,   # mph (converted from km/h)
    "wind_dir":   int,     # degrees, 0=N clockwise
    "code":       int,     # WMO weather code
    "sunrise":    str,     # "HH:MM"
    "sunset":     str,     # "HH:MM"
    "precip_pct": int,     # today's precipitation probability max (%)
}
```

### viewmodel.build_display_state(raw) → display-state dict
```python
{
    "temp_str":       str,   # e.g. "72oF"  ('o' = degree glyph in 7-seg renderer)
    "humidity":       int,
    "pressure_str":   str,   # e.g. "29.92"
    "wind_speed_str": str,   # e.g. "12.3 mph"
    "wind_gust_str":  str,   # e.g. "18.5 mph"
    "wind_dir":       int,
    "weather_code":   int,
    "condition_str":  str,   # e.g. "Clear", "Rain" — from wmo_condition(); used in left panel
    "precip_pct_str": str,   # e.g. "30%" — today's precipitation probability max
    "sunrise":        str,
    "sunset":         str,
    "time_str":       str,   # e.g. "08:32:15 AM"
    "date_str":       str,   # e.g. "03/10/2026"
    "location":       str,
}
```

### viewmodel helpers for city-select screen
- `viewmodel.format_city_temp(temp_f)` → plain string e.g. `"72F"` (no degree glyph; for `screen.text()`)
- `viewmodel.wmo_condition(code)` → short condition string e.g. `"Rain"`, `"Clear"`, `"Thunder"`

### view.draw_city_select(screen, cities, cursor, temps=None, conditions=None)
- `temps` — list of temp strings from `format_city_temp`, one per city (or `None` if not yet fetched)
- `conditions` — list of condition strings from `wmo_condition`, one per city (or `None`)
- Both are shown right-aligned in each row: `[condition]  [temp]`

### model.fetch_forecast(lat, lon) → list of 6 dicts
```python
[
    {
        "day":        str,   # e.g. "Mon"
        "date":       str,   # e.g. "03/12"
        "high":       float, # °F
        "low":        float, # °F
        "precip_pct": int,   # %
        "code":       int,   # WMO weather code
    },
    ...  # 6 entries total
]
```

### viewmodel.build_forecast_state(forecast_raw, city_name, utc_offset_h) → display-state dict
```python
{
    "location": str,
    "time_str": str,
    "date_str": str,
    "days": [
        {"day", "date", "high_str", "low_str", "precip_str", "condition_str"},
        ...  # 6 entries
    ]
}
```
`location`/`time_str`/`date_str` keys allow `draw_top_bar()` to be reused unchanged.

### view.draw_forecast(screen, state)
6-column layout (132 px per column). Dividers at x=132, 264, 396, 528, 660.
Each column shows: day name, mm/dd date, condition, Hi:NNF, Lo:NNF, precip%.

## App states (main.py)

```
STATE_WEATHER     = 0   — weather display; rotary click → city select; bottom button → forecast
STATE_CITY_SELECT = 1   — city list; rotary click → confirm; rotate → move cursor; bottom button → forecast
STATE_FORECAST    = 2   — 6-day forecast; bottom button → weather display (for forecast city)
```

Navigation:
- STATE_WEATHER → bottom button → STATE_FORECAST (forecast for active city)
- STATE_CITY_SELECT → bottom button → STATE_FORECAST (forecast for cursor city)
- STATE_FORECAST → bottom button → STATE_WEATHER (sets active city = forecast city)
- STATE_WEATHER ↔ STATE_CITY_SELECT via rotary click

City temps and conditions are cached in `_city_temps` / `_city_conditions` lists and
refreshed on the same `REFRESH_SEC` timer as the weather display. `_refresh_flag = True`
at startup triggers an immediate first fetch for both modes.

## MicroPython constraints

- No `dataclasses`, no `typing`, no f-strings with `=` specifier
- Plain dicts are preferred over user classes for data transfer (faster attribute
  access, lower RAM overhead on ESP32)
- Avoid `@property` decorators in the ViewModel — stateless functions are fine
- Do not split `view.py` into sub-modules; extra module imports cost RAM
- `time.mktime(time.localtime())` is the MicroPython idiom to get epoch seconds
  from the RTC; there is no `datetime` module

## Display hardware notes

- Display: 792 × 272 px, black/white only (no greyscale)
- Driver: `CrowPanel.py` must be present on the device (not in this repo)
  - `eink.Screen_579()` — creates screen object
  - `eink.COLOR_BLACK = 0`, `eink.COLOR_WHITE = 1`
  - `screen.show(mode=0)` — flushes buffer to display (slow; avoid calling more than once per refresh)
- `writer.py` and `freesans20.py` are required on device but not used directly
  by this code (they may be used by CrowPanel.py internally)

## 7-segment renderer

`view.draw_large_number(screen, text, x, y, h, color)` renders custom glyphs.
Supported characters: `0-9`, `-`, `.`, `o` (degree symbol), `C`, `F`, ` `.
The character `'o'` renders a small circle as a degree symbol — this is intentional.
Do NOT use `'o'` in strings passed to `screen.text()` — use plain text helpers instead.

## Layout constants (config.py)

```
W=792, H=272
TOP_H=25   — top bar height, hline at y=24
BOT_Y=245  — bottom bar start, hline at y=245
COL1_X=396 — left/centre divider (50% of W)
COL2_X=594 — centre/right divider (75% of W)
```

Panel centres derived from these:
- Left panel icon: `COL1_X // 2` = 198
- Compass: `(COL2_X + W) // 2` = 693, `(TOP_H + BOT_Y) // 2 - 35` = 100

## WMO weather codes handled

| Code(s) | Icon | Condition text |
|---------|------|----------------|
| 0 | Clear sky (sun + 8 rays) | "Clear" |
| 1–3 | Cloudy (cloud outline) | "Cloudy" |
| 45, 48 | Fog (4 horizontal dashes) | "Fog" |
| 51–67, 80–82 | Rain (cloud + droplets) | "Rain" |
| 71–77 | Snow (cloud + asterisk) | "Snow" |
| 95, 96, 99 | Thunderstorm (cloud + lightning zigzag) | "Thunder" |
| anything else | Generic cloud | "Cloudy" |

## Common tasks

**Change timezone:** Edit `UTC_OFFSET_H` in `config.py`.

**Change units:** Edit `_format_temperature()`, `_format_wind_speed()`, or
`_format_wind_gust()` in `viewmodel.py`. Also update the unit suffix strings in
`view.draw_center_panel()` for pressure.

**Add a new WMO code:** Add an `elif` branch in `view.draw_weather_icon()` and
a matching branch in `viewmodel.wmo_condition()`. The condition string is shown
both in the left panel and on the city-select screen.

**Add a city:** Append a `(name, lat, lon, utc_offset_h)` tuple to `CITIES` in `config.py`.

**Upload files:** `mpremote cp config.py model.py viewmodel.py view.py main.py :`

**Force refresh:** Press the MENU button (GPIO 2). The IRQ sets `_refresh_flag`
in `main.py` which triggers an immediate fetch + redraw on the next 1-second tick.
