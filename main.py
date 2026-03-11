# main.py
# Entry point for the MicroPython weather station.
# Wires together model → viewmodel → view and runs the polling loop.

import time
from machine import Pin

_ROT_DEBOUNCE_MS = 500   # ignore encoder edges within this window

import config
import model
import viewmodel
import view

# ── App states ───────────────────────────────────────────────────────
STATE_WEATHER     = 0
STATE_CITY_SELECT = 1

_app_state   = STATE_CITY_SELECT
_active_city = 0          # default: Rockville, MD (index 0 in CITIES)
_cursor      = 0          # highlighted city in select screen

# ── ISR flags ────────────────────────────────────────────────────────
_refresh_flag  = True      # True at startup so city temps fetch immediately
_rot_delta     = 0         # accumulated rotation ticks
_rot_click     = False     # True when SW button pressed
_last_rot_ms   = 0         # debounce timestamp for rotation
_last_click_ms = 0         # debounce timestamp for SW button


def _menu_irq(_):
    global _refresh_flag
    _refresh_flag = True


def _rot_up_irq(pin):
    global _rot_delta, _last_rot_ms
    now = time.ticks_ms()
    if time.ticks_diff(now, _last_rot_ms) >= _ROT_DEBOUNCE_MS:
        _rot_delta -= 1
        _last_rot_ms = now


def _rot_down_irq(pin):
    global _rot_delta, _last_rot_ms
    now = time.ticks_ms()
    if time.ticks_diff(now, _last_rot_ms) >= _ROT_DEBOUNCE_MS:
        _rot_delta += 1
        _last_rot_ms = now


def _rot_press_irq(pin):
    global _rot_click, _last_click_ms
    now = time.ticks_ms()
    if time.ticks_diff(now, _last_click_ms) >= _ROT_DEBOUNCE_MS:
        _rot_click = True
        _last_click_ms = now


def main():
    global _app_state, _active_city, _cursor
    global _refresh_flag, _rot_delta, _rot_click

    menu_btn = Pin(2, Pin.IN, Pin.PULL_UP)
    menu_btn.irq(trigger=Pin.IRQ_FALLING, handler=_menu_irq)

    rot_up.irq(trigger=Pin.IRQ_FALLING,    handler=_rot_up_irq)
    rot_down.irq(trigger=Pin.IRQ_FALLING,  handler=_rot_down_irq)
    rot_sw.irq(trigger=Pin.IRQ_FALLING,    handler=_rot_press_irq)

    print("Connecting to WiFi...")
    model.connect_wifi()
    model.sync_ntp()

    screen = view.init_screen()
    raw               = None
    _city_temps      = [None] * len(config.CITIES)
    _city_conditions = [None] * len(config.CITIES)
    last_ms           = time.ticks_ms()

    view.draw_city_select(screen, config.CITIES, _cursor, _city_temps, _city_conditions)
    screen.show(mode=0)

    while True:
        time.sleep(1)

        # ── City select mode ──────────────────────────────────────────
        if _app_state == STATE_CITY_SELECT:
            changed = False

            if _rot_delta != 0:
                _cursor = (_cursor + _rot_delta) % len(config.CITIES)
                _rot_delta = 0
                changed = True

            if _rot_click:
                _rot_click = False
                _active_city = _cursor
                _app_state = STATE_WEATHER
                _refresh_flag = True   # trigger immediate fetch for new city
                continue

            elapsed = time.ticks_diff(time.ticks_ms(), last_ms) // 1000
            if elapsed >= config.REFRESH_SEC or _refresh_flag:
                _refresh_flag = False
                last_ms = time.ticks_ms()
                for i, (name, lat, lon, utc_h) in enumerate(config.CITIES):
                    print("Fetching temp for", name, "...")
                    try:
                        city_raw = model.fetch_weather(lat, lon, utc_h)
                        _city_temps[i]      = viewmodel.format_city_temp(city_raw["temp"])
                        _city_conditions[i] = viewmodel.wmo_condition(city_raw["code"])
                    except Exception as e:
                        print("Temp fetch error:", name, e)
                changed = True

            if changed:
                view.draw_city_select(screen, config.CITIES, _cursor, _city_temps, _city_conditions)
                screen.show(mode=0)
            continue

        # ── Weather display mode ──────────────────────────────────────
        if _rot_click:
            _rot_click = False
            _cursor = _active_city     # start selection at current city
            _app_state = STATE_CITY_SELECT
            view.draw_city_select(screen, config.CITIES, _cursor, _city_temps, _city_conditions)
            screen.show(mode=0)
            continue

        elapsed = time.ticks_diff(time.ticks_ms(), last_ms) // 1000
        if elapsed >= config.REFRESH_SEC or _refresh_flag:
            _refresh_flag = False
            last_ms = time.ticks_ms()
            name, lat, lon, utc_h = config.CITIES[_active_city]
            print("Fetching weather for", name, "...")
            try:
                raw = model.fetch_weather(lat, lon, utc_h)
                print("Data:", raw)
            except Exception as e:
                print("Fetch error:", e)
                if raw is None:
                    view.draw_error(screen, e)

            if raw is not None:
                try:
                    state = viewmodel.build_display_state(raw, name, utc_h)
                    view.draw_display(screen, state)
                    screen.show(mode=0)
                except Exception as e:
                    print("Draw error:", e)
                    view.draw_error(screen, "Draw: " + str(e))


# Rotary encoder pins (module-level so ISRs can reference them)
rot_up   = Pin(config.ROT_UP,    Pin.IN, Pin.PULL_UP)
rot_down = Pin(config.ROT_DOWN,  Pin.IN, Pin.PULL_UP)
rot_sw   = Pin(config.ROT_CLICK, Pin.IN, Pin.PULL_UP)

main()
