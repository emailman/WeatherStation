# WeatherStation

A MicroPython weather station that displays live conditions on an
[Elecrow CrowPanel 5.79" e-paper display](https://www.elecrow.com/crowpanel-5-79-epaper-hmi-display.html)
(792 × 272 px, black/white).

Weather data is fetched from [Open-Meteo](https://open-meteo.com/) every 10 minutes —
no API key required.

## Display layout

### Weather display

```
+-----------------------------------------------------------------------------+
|  Rockville, MD          08:32:15 AM  03/10/2026               Bat:90%      |
+------------------------------+------------------+---------------------------+
|                              |                  |                           |
|         [sun icon]           |   Humidity       |         N                 |
|                              |   ## 55%         |       W (+) E             |
|         72°F                 |                  |         S                 |
|                              |   Pressure       |      12.3 mph             |
|                              |   v 29.92 inHg   |                           |
+------------------------------+------------------+---------------------------+
|  * 07:08                                                          18:52 *   |
+-----------------------------------------------------------------------------+
```

- **Left panel** — WMO weather icon + large 7-segment temperature (°F)
- **Centre panel** — humidity (%) and barometric pressure (inHg)
- **Right panel** — compass rose showing wind direction + speed (mph)
- **Top bar** — location, local time, date, battery stub
- **Bottom bar** — sunrise and sunset times

### City selection screen

Press the rotary encoder button to switch between the weather display and the
city selection screen. Rotate to move the cursor; press to confirm.

```
+-----------------------------------------------------------------------------+
|                            SELECT CITY                                      |
+-----------------------------------------------------------------------------+
|              New York, NY                            Cloudy  41F            |
|            > Chicago, IL                               Rain  34F            |
|          Los Angeles, CA                              Clear  68F            |
|              Houston, TX                             Cloudy  58F            |
|             Rockville, MD                             Clear  47F            |
+-----------------------------------------------------------------------------+
```

Each row shows the city name, current weather condition, and temperature (°F).
The highlighted row (cursor) is shown in inverse video.
Data refreshes on the same 10-minute schedule as the weather display.

## Hardware

| Item | Detail |
|------|--------|
| Display | Elecrow CrowPanel 5.79" e-paper, 792 × 272 px |
| MCU | ESP32 (or compatible MicroPython board) |
| Button | MENU button on GPIO 2 (active-low, pull-up); triggers an immediate refresh |
| Rotary encoder | Up/Down/Click on GPIOs defined in `config.py`; navigates city selection |

## File overview

| File | Layer | Purpose |
|------|-------|---------|
| `config.py` | Config | WiFi credentials, GPS coordinates, refresh interval, UTC offset, display geometry, city list |
| `model.py` | Model | WiFi connection, NTP sync, Open-Meteo HTTP fetch + unit conversion |
| `viewmodel.py` | ViewModel | Transforms raw model data into display-ready strings; WMO condition text |
| `view.py` | View | All drawing: 7-segment digits, weather icons, compass, panel layout, city-select screen |
| `main.py` | App | Button/encoder ISRs, 10-minute polling loop, wires the other layers together |

### Required files already on the device

- `CrowPanel.py` — Elecrow driver (`Screen_579`, `COLOR_BLACK`, `COLOR_WHITE`)
- `writer.py` — font rendering helper
- `freesans20.py` — bitmap font

## Setup

### 1. Configure

Edit `config.py`:

```python
WIFI_SSID     = "your_network"
WIFI_PASSWORD = "your_password"
LATITUDE      = 39.08        # decimal degrees
LONGITUDE     = -77.16
LOCATION_NAME = "Rockville, MD"
REFRESH_SEC   = 600          # seconds between fetches (min ~60)
UTC_OFFSET_H  = -4           # UTC-5 = EST, UTC-4 = EDT, UTC-7 = MST, etc.
```

Add or edit cities in the `CITIES` list:

```python
CITIES = [
    ("New York, NY",    40.71,  -74.01,  -4),
    ("Chicago, IL",     41.88,  -87.63,  -5),
    # ...
]
```

### 2. Upload files

Using **mpremote**:

```bash
mpremote cp config.py model.py viewmodel.py view.py main.py :
```

Using **Thonny**: open each file and use *File → Save copy… → MicroPython device*.

### 3. Run

`main.py` calls `main()` at module level, so it runs automatically on boot.
To start manually from the REPL:

```python
import main
```

To make it run on every power-on, rename or copy `main.py` to `boot.py`, or add
`import main` to the existing `boot.py`.

## Customisation

| What | Where |
|------|-------|
| Timezone | `UTC_OFFSET_H` in `config.py` |
| Refresh rate | `REFRESH_SEC` in `config.py` |
| City list | `CITIES` in `config.py` |
| Display geometry | Layout constants at the bottom of `config.py` |
| Temperature units | `_format_temperature()` in `viewmodel.py` (currently °F) |
| Wind speed units | `_format_wind_speed()` in `viewmodel.py` (currently mph) |
| Pressure units | `_format_pressure()` and the unit suffix in `view.draw_center_panel()` |
| Weather icons | `draw_weather_icon()` in `view.py` — add new WMO codes as needed |
| Condition text | `wmo_condition()` in `viewmodel.py` — short strings shown on city-select screen |

## Data source

Open-Meteo free API — no account or key needed.
Endpoint: `http://api.open-meteo.com/v1/forecast`

Fields used: `temperature_2m` (°C), `relative_humidity_2m`, `surface_pressure`,
`wind_speed_10m` (km/h), `wind_direction_10m`, `weather_code`, `daily/sunrise`, `daily/sunset`.

## License

MIT
