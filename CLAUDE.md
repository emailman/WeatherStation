# CLAUDE.md — WeatherStation project notes

## What this project is

MicroPython firmware for an Elecrow CrowPanel 5.79" e-paper weather station
(ESP32 + 792 × 272 px black/white display). Fetches live data from Open-Meteo
every 10 minutes and renders it in a fixed panel layout.

## Architecture: MVVM

```
config.py      constants only, zero imports
model.py       WiFi + NTP + HTTP fetch, returns plain dicts
viewmodel.py   string formatting, returns a display-state dict
view.py        all draw_* functions, consumes display-state dict
main.py        button ISR + polling loop, wires the layers
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
    "temp":       float,   # Fahrenheit
    "humidity":   int,     # %
    "pressure":   float,   # inHg
    "wind_speed": float,   # mph
    "wind_dir":   int,     # degrees, 0=N clockwise
    "code":       int,     # WMO weather code
    "sunrise":    str,     # "HH:MM"
    "sunset":     str,     # "HH:MM"
}
```

### viewmodel.build_display_state(raw) → display-state dict
```python
{
    "temp_str":       str,   # e.g. "72oF"  ('o' = degree glyph in 7-seg renderer)
    "humidity":       int,
    "pressure_str":   str,   # e.g. "29.92"
    "wind_speed_str": str,   # e.g. "12.3 mph"
    "wind_dir":       int,
    "weather_code":   int,
    "sunrise":        str,
    "sunset":         str,
    "time_str":       str,   # e.g. "08:32:15 AM"
    "date_str":       str,   # e.g. "03/10/2026"
    "location":       str,
}
```

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

## Layout constants (config.py)

```
W=792, H=272
TOP_H=25   — top bar height, hline at y=24
BOT_Y=245  — bottom bar start, hline at y=245
COL1_X=400 — left/centre divider
COL2_X=600 — centre/right divider
```

Panel centres derived from these:
- Left panel icon: `COL1_X // 2` = 200
- Compass: `(COL2_X + W) // 2` = 696, `(TOP_H + BOT_Y) // 2` = 135

## WMO weather codes handled

| Code(s) | Icon |
|---------|------|
| 0 | Clear sky (sun + 8 rays) |
| 1–3 | Cloudy (cloud outline) |
| 45, 48 | Fog (4 horizontal dashes) |
| 51–67, 80–82 | Rain (cloud + droplets) |
| 71–77 | Snow (cloud + asterisk) |
| 95, 96, 99 | Thunderstorm (cloud + lightning zigzag) |
| anything else | Generic cloud |

## Common tasks

**Change timezone:** Edit `UTC_OFFSET_H` in `config.py`.

**Change units:** Edit `_format_temperature()` or `_format_wind_speed()` in
`viewmodel.py`. Also update the unit suffix strings in `view.draw_center_panel()`
for pressure.

**Add a new WMO code:** Add an `elif` branch in `view.draw_weather_icon()`.

**Upload files:** `mpremote cp config.py model.py viewmodel.py view.py main.py :`

**Force refresh:** Press the MENU button (GPIO 2). The IRQ sets `_refresh_flag`
in `main.py` which triggers an immediate fetch + redraw on the next 1-second tick.
