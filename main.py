# main.py
# Entry point for the MicroPython weather station.
# Wires together model → viewmodel → view and runs the polling loop.

import time
from machine import Pin

import config
import model
import viewmodel
import view

# MENU button (GPIO 2) sets this flag to force an early refresh
_refresh_flag = False


def _menu_irq(_):
    global _refresh_flag
    _refresh_flag = True


def main():
    global _refresh_flag

    menu_btn = Pin(2, Pin.IN, Pin.PULL_UP)
    menu_btn.irq(trigger=Pin.IRQ_FALLING, handler=_menu_irq)

    print("Connecting to WiFi...")
    model.connect_wifi()
    model.sync_ntp()

    screen = view.init_screen()
    raw = None
    # force an immediate fetch on first iteration
    last_ms = time.ticks_add(time.ticks_ms(), -(config.REFRESH_SEC * 1000))

    while True:
        elapsed = time.ticks_diff(time.ticks_ms(), last_ms) // 1000
        if elapsed >= config.REFRESH_SEC or _refresh_flag:
            _refresh_flag = False
            print("Fetching weather...")
            try:
                raw = model.fetch_weather(config.LATITUDE, config.LONGITUDE)
                last_ms = time.ticks_ms()
                print("Data:", raw)
            except Exception as e:
                print("Fetch error:", e)
                if raw is None:
                    view.draw_error(screen, e)

            if raw is not None:
                try:
                    state = viewmodel.build_display_state(raw)
                    view.draw_display(screen, state)
                except Exception as e:
                    print("Draw error:", e)
                    view.draw_error(screen, "Draw: " + str(e))

        time.sleep(1)


main()
