# main.py
# Entry point for the MicroPython weather station.
# Wires together model → viewmodel → view and runs the polling loop.

import time
from machine import Pin

import config
import model
import viewmodel
import view

# ── App states ───────────────────────────────────────────────────────
STATE_WEATHER     = 0
STATE_CITY_SELECT = 1

_app_state   = STATE_WEATHER
_active_city = 4          # default: Rockville, MD (index 4 in CITIES)
_cursor      = 4          # highlighted city in select screen

# ── ISR flags ────────────────────────────────────────────────────────
_refresh_flag = False
_rot_delta    = 0         # accumulated rotation ticks
_rot_click    = False     # True when SW button pressed


def _menu_irq(_):
    global _refresh_flag
    _refresh_flag = True


def _rot_up_irq(pin):
    global _rot_delta
    _rot_delta += 1


def _rot_down_irq(pin):
    global _rot_delta
    _rot_delta -= 1


def _rot_press_irq(pin):
    global _rot_click
    _rot_click = True


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
    raw    = None
    # force an immediate fetch on first iteration
    last_ms = time.ticks_add(time.ticks_ms(), -(config.REFRESH_SEC * 1000))

    while True:
        time.sleep(1)

        # ── City select mode ──────────────────────────────────────────
        if _app_state == STATE_CITY_SELECT:
            if _rot_delta != 0:
                _cursor = (_cursor + _rot_delta) % len(config.CITIES)
                _rot_delta = 0
                view.draw_city_select(screen, config.CITIES, _cursor)
                screen.show(mode=0)
            if _rot_click:
                _rot_click = False
                _active_city = _cursor
                _app_state = STATE_WEATHER
                _refresh_flag = True   # trigger immediate fetch for new city
            continue

        # ── Weather display mode ──────────────────────────────────────
        if _rot_click:
            _rot_click = False
            _cursor = _active_city     # start selection at current city
            _app_state = STATE_CITY_SELECT
            view.draw_city_select(screen, config.CITIES, _cursor)
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
