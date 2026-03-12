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
|                              |                  |         N                 |
|         [sun icon]           |   Humidity       |       W (+) E             |
|           Clear              |   ## 55%         |         S                 |
|                              |                  |    Wind Speed             |
|         72°F                 |   Pressure       |      12.3 mph             |
|                              |   v 29.92 inHg   |                           |
|                              |                  |    Wind Gust              |
|                              |                  |      18.5 mph             |
+------------------------------+------------------+---------------------------+
|  * 07:08                                                          18:52 *   |
+-----------------------------------------------------------------------------+
```

- **Left panel** — WMO weather icon, condition text (e.g. "Clear"), and large 7-segment temperature (°F)
- **Centre panel** — humidity (%) and barometric pressure (inHg)
- **Right panel** — compass rose showing wind direction, wind speed (mph), and wind gust (mph)
- **Top bar** — location, local time, date, battery stub
- **Bottom bar** — sunrise and sunset times

### City selection screen

Press the rotary encoder button to switch between the weather display and the
city selection screen. Rotate to move the cursor; press to confirm.

```
+-----------------------------------------------------------------------------+
|                            SELECT CITY                                      |
+-----------------------------------------------------------------------------+
|            > Rockville, MD                            Clear  47F            |
|              Missoula, MT                            Cloudy  38F            |
|        San Francisco, CA                              Clear  62F            |
|            San Diego, CA                              Clear  68F            |
|              New York, NY                            Cloudy  41F            |
+-----------------------------------------------------------------------------+
```

Each row shows the city name, current weather condition, and temperature (°F).
The highlighted row (cursor) is shown in inverse video.
Data refreshes on the same 10-minute schedule as the weather display.

### 6-day forecast screen

Press the bottom button (GPIO 1) from either the weather display or the city
selection screen to view the 6-day forecast for the active/highlighted city.
Press the bottom button again to return to the weather display for that city.

```
+--------+--------+--------+--------+--------+--------+
|  Mon   |  Tue   |  Wed   |  Thu   |  Fri   |  Sat   |
| 03/10  | 03/11  | 03/12  | 03/13  | 03/14  | 03/15  |
|        |        |        |        |        |        |
| Clear  |  Rain  | Cloudy | Clear  |  Snow  | Cloudy |
|        |        |        |        |        |        |
| Hi:72F | Hi:65F | Hi:60F | Hi:70F | Hi:55F | Hi:58F |
| Lo:55F | Lo:50F | Lo:48F | Lo:52F | Lo:40F | Lo:44F |
|Precip  |Precip  |Precip  |Precip  |Precip  |Precip  |
| Chance | Chance | Chance | Chance | Chance | Chance |
|  30%   |  80%   |  40%   |  10%   |  60%   |  20%   |
+--------+--------+--------+--------+--------+--------+
```

Each column shows: day name, mm/dd date, condition text, high/low temps (°F), "Precip Chance" label, and precipitation probability (%).
The top bar shows the city name, current time, and date (same as other screens).

## Hardware

| Item | Detail |
|---|---|
| Display | Elecrow CrowPanel 5.79" e-paper, 792 × 272 px |
| MCU | ESP32 (or compatible MicroPython board) |
| MENU button | GPIO 2 (active-low, pull-up); triggers an immediate refresh |
| Bottom button | GPIO 1 (active-low, pull-up); opens/closes the 6-day forecast screen |
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
    ("Rockville, MD",    39.08,  -77.16,  -4),
    ("Missoula, MT",     46.87, -113.99,  -6),
    ("San Francisco, CA",37.77, -122.42,  -7),
    ("San Diego, CA",    32.72, -117.16,  -7),
    ("New York, NY",     40.71,  -74.01,  -4),
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
| Wind gust units | `_format_wind_gust()` in `viewmodel.py` (currently mph) |
| Condition text | `wmo_condition()` in `viewmodel.py` — short strings shown on city-select screen and left panel |

## Data source

Open-Meteo free API — no account or key needed.
Endpoint: `http://api.open-meteo.com/v1/forecast`

Fields used: `temperature_2m` (°C), `relative_humidity_2m`, `surface_pressure`,
`wind_speed_10m` (km/h), `wind_gusts_10m` (km/h), `wind_direction_10m`, `weather_code`,
`daily/sunrise`, `daily/sunset`.

## License

MIT
