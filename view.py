# view.py
# All display rendering for the e-paper weather station.
# Receives a display-state dict from the ViewModel; does zero data formatting.
#
# Files required on device: CrowPanel.py, writer.py, freesans20.py

import math

import CrowPanel as eink
import config

BLACK = eink.COLOR_BLACK  # 0
WHITE = eink.COLOR_WHITE  # 1


# ── Convenience alias ───────────────────────────────────────────────

def init_screen():
    """Create and return the e-paper screen object."""
    return eink.Screen_579()


# ═══════════════════════════════════════════════════════════════════
# 7-segment large digit renderer
# ═══════════════════════════════════════════════════════════════════
#
#  Segment index  0=a(top) 1=b(top-right) 2=c(bot-right)
#                 3=d(bot) 4=e(bot-left)  5=f(top-left)  6=g(middle)

_SEG = [
    0b0111111,  # 0  a b c d e f
    0b0000110,  # 1  b c
    0b1011011,  # 2  a b d e g
    0b1001111,  # 3  a b c d g
    0b1100110,  # 4  b c f g
    0b1101101,  # 5  a c d f g
    0b1111101,  # 6  a c d e f g
    0b0000111,  # 7  a b c
    0b1111111,  # 8  all
    0b1101111,  # 9  a b c d f g
]


def _draw_digit(screen, digit, x, y, h, color):
    """Draw one 7-segment digit; return pixel advance width."""
    w = h * 6 // 10
    s = max(2, h // 10)
    mid = h // 2
    bits = _SEG[digit]
    if bits & 0x01:
        screen.fill_rect(x + s, y, w - 2 * s, s, color)  # a top
    if bits & 0x02:
        screen.fill_rect(x + w - s, y + s, s, mid - s, color)  # b top-right
    if bits & 0x04:
        screen.fill_rect(x + w - s, y + mid, s, mid - s, color)  # c bot-right
    if bits & 0x08:
        screen.fill_rect(x + s, y + h - s, w - 2 * s, s, color)  # d bottom
    if bits & 0x10:
        screen.fill_rect(x, y + mid, s, mid - s, color)  # e bot-left
    if bits & 0x20:
        screen.fill_rect(x, y + s, s, mid - s, color)  # f top-left
    if bits & 0x40:
        screen.fill_rect(x + s, y + mid - s // 2, w - 2 * s, s, color)  # g middle
    return w + s  # advance = digit width + inter-digit gap


def draw_large_number(screen, text, x, y, h, color):
    """Render a string using 7-segment glyphs at height h.

    Handles: 0-9  '-'  'o' (degree °)  'C'  'F'  ' '  '.'
    Returns total pixel width consumed.
    """
    w = h * 6 // 10
    s = max(2, h // 10)
    cx = x
    for ch in text:
        if ch.isdigit():
            cx += _draw_digit(screen, int(ch), cx, y, h, color)
        elif ch == '-':
            mid = h // 2
            screen.fill_rect(cx + s, y + mid - s // 2, w - 2 * s, s, color)
            cx += w + s
        elif ch == '.':
            screen.fill_rect(cx, y + h - s * 2, s * 2, s * 2, color)
            cx += s * 3
        elif ch == 'o':  # degree symbol
            r = max(3, h // 8)
            screen.ellipse(cx + r, y + r + 2, r, r, color)
            cx += r * 2 + s + 1
        elif ch == 'C':
            screen.fill_rect(cx + s, y, w - 2 * s, s, color)  # top
            screen.fill_rect(cx + s, y + h - s, w - 2 * s, s, color)  # bottom
            screen.fill_rect(cx, y + s, s, h - 2 * s, color)  # left
            cx += w + s
        elif ch == 'F':
            screen.fill_rect(cx + s, y, w - 2 * s, s, color)  # top
            screen.fill_rect(cx + s, y + h // 2 - s, w - 2 * s, s, color)  # middle
            screen.fill_rect(cx, y + s, s, h - 2 * s, color)  # left
            cx += w + s
        elif ch == ' ':
            cx += w // 2
    return cx - x


# ═══════════════════════════════════════════════════════════════════
# Weather icons
# ═══════════════════════════════════════════════════════════════════

def _cloud(screen, cx, cy, r):
    rx, ry = r * 2 // 5, r * 2 // 7
    screen.ellipse(cx, cy, rx, ry, BLACK)
    screen.ellipse(cx - rx, cy + ry // 2, rx // 2 + 2, ry // 2 + 2, BLACK)
    screen.ellipse(cx + rx, cy + ry // 2, rx // 2 + 2, ry // 2 + 2, BLACK)


def _asterisk(screen, cx, cy, r):
    for i in range(6):
        a = i * math.pi / 3
        screen.line(cx, cy,
                    cx + int(r * math.cos(a)),
                    cy + int(r * math.sin(a)), BLACK)


def draw_weather_icon(screen, code, cx, cy, size):
    """Draw a WMO-code weather icon centred at (cx, cy)."""
    r = size
    if code == 0:
        # Clear sky – filled sun + 8 rays
        screen.ellipse(cx, cy, r // 3, r // 3, BLACK, True)
        for i in range(8):
            a = i * math.pi / 4
            x0 = cx + int((r // 3 + 4) * math.cos(a))
            y0 = cy + int((r // 3 + 4) * math.sin(a))
            x1 = cx + int((r // 2 + 6) * math.cos(a))
            y1 = cy + int((r // 2 + 6) * math.sin(a))
            screen.line(x0, y0, x1, y1, BLACK)

    elif 1 <= code <= 3:
        _cloud(screen, cx, cy, r)

    elif code in (45, 48):
        # Fog – 4 horizontal dashes
        for i in range(4):
            yy = cy - r // 2 + i * (r // 3)
            screen.hline(cx - r // 2, yy, r, BLACK)

    elif (51 <= code <= 67) or (80 <= code <= 82):
        # Rain – cloud + vertical droplets
        _cloud(screen, cx, cy - r // 4, r)
        for i in range(4):
            xx = cx - r // 3 + i * (r // 5 + 1)
            screen.vline(xx, cy + r // 5, r // 3, BLACK)

    elif 71 <= code <= 77:
        # Snow – cloud + snowflake asterisk
        _cloud(screen, cx, cy - r // 4, r)
        _asterisk(screen, cx, cy + r // 3, r // 4)

    elif code in (95, 96, 99):
        # Thunderstorm – cloud + zigzag lightning
        _cloud(screen, cx, cy - r // 4, r)
        lx, ly = cx, cy + r // 6
        screen.line(lx, ly, lx - r // 6, ly + r // 4, BLACK)
        screen.line(lx - r // 6, ly + r // 4, lx, ly + r // 4, BLACK)
        screen.line(lx, ly + r // 4, lx - r // 6, ly + r // 2, BLACK)

    else:
        _cloud(screen, cx, cy, r)


# ═══════════════════════════════════════════════════════════════════
# Compass rose
# ═══════════════════════════════════════════════════════════════════

def draw_compass(screen, cx, cy, radius, wind_deg):
    r = radius
    screen.ellipse(cx, cy, r, r, BLACK)

    # Cardinal labels (8-px built-in font: each char ~8×8)
    screen.text("N", cx - 3, cy - r - 10, BLACK)
    screen.text("S", cx - 3, cy + r + 2, BLACK)
    screen.text("E", cx + r + 2, cy - 4, BLACK)
    screen.text("W", cx - r - 10, cy - 4, BLACK)

    # Arrow points toward direction wind is travelling (opposite of reported origin)
    a = (wind_deg + 90) * math.pi / 180
    cos_a = math.cos(a)
    sin_a = math.sin(a)

    tip_x = cx + int(r * 0.75 * cos_a)
    tip_y = cy + int(r * 0.75 * sin_a)
    tail_x = cx - int(r * 0.40 * cos_a)
    tail_y = cy - int(r * 0.40 * sin_a)

    perp = a + math.pi / 2
    wing = r // 6
    p1x = tail_x + int(wing * math.cos(perp))
    p1y = tail_y + int(wing * math.sin(perp))
    p2x = tail_x - int(wing * math.cos(perp))
    p2y = tail_y - int(wing * math.sin(perp))

    screen.line(tip_x, tip_y, p1x, p1y, BLACK)
    screen.line(tip_x, tip_y, p2x, p2y, BLACK)
    screen.line(p1x, p1y, p2x, p2y, BLACK)

    # Centre dot
    screen.ellipse(cx, cy, 3, 3, BLACK, True)


# ═══════════════════════════════════════════════════════════════════
# Top and bottom bars
# ═══════════════════════════════════════════════════════════════════

def draw_top_bar(screen, state):
    y = 7
    time_str = state["time_str"]
    date_str = state["date_str"]
    location = state["location"]

    screen.text(location, config.W // 6 - len(location) * 4, y, BLACK)
    screen.text(time_str, config.W // 2 - len(time_str) * 4, y, BLACK)
    screen.text(date_str, config.W * 5 // 6 - len(date_str) * 4, y, BLACK)
    screen.hline(0, config.TOP_H - 1, config.W, BLACK)


def _tiny_sun(screen, cx, cy, filled=True):
    screen.ellipse(cx, cy, 4, 4, BLACK, filled)
    for i in range(4):
        a = i * math.pi / 2
        x0 = cx + int(5 * math.cos(a))
        y0 = cy + int(5 * math.sin(a))
        x1 = cx + int(8 * math.cos(a))
        y1 = cy + int(8 * math.sin(a))
        screen.line(x0, y0, x1, y1, BLACK)


def draw_bottom_bar(screen, state):
    screen.hline(0, config.BOT_Y, config.W, BLACK)
    y = config.BOT_Y + 6
    _tiny_sun(screen, 12, y + 4, filled=False)
    screen.text(state["sunrise"], 26, y, BLACK)
    screen.text(state["sunset"], config.W - 70, y, BLACK)
    _tiny_sun(screen, config.W - 14, y + 4)


# ═══════════════════════════════════════════════════════════════════
# Left panel  (weather icon + temperature)
# ═══════════════════════════════════════════════════════════════════

def draw_left_panel(screen, state):
    icon_cx = config.COL1_X // 2  # 198

    # Top block (icon, cond, temp, hi/lo) packed near the top bar; precip
    # anchored independently to leave clear visual space above it.
    icon_cy        = config.TOP_H + 5 + 38    # 68  (5px gap from top bar)
    cond_y         = icon_cy + 38 - 2         # 104  (closer to icon)
    temp_y         = cond_y + 8 + 18         # 130  (50px tall, bottom=180)
    hi_lo_y        = temp_y + 50 + 5          # 185  (bottom=193)
    precip_label_y = 207                       # fixed; ~14px gap from hi/lo
    precip_val_y   = precip_label_y + 8 + 5   # 220

    draw_weather_icon(screen, state["weather_code"], icon_cx, icon_cy, 38)

    cond = state["condition_str"]
    screen.text(cond, icon_cx - len(cond) * 4, cond_y, BLACK)

    seg_h = 50
    temp_str = state["temp_str"]
    digit_w = seg_h * 6 // 10 + max(2, seg_h // 10)
    n_digits = len([c for c in temp_str if c.isdigit()])
    approx_w = n_digits * digit_w + (seg_h // 4) + digit_w
    tx = max(4, icon_cx - approx_w // 2)
    draw_large_number(screen, temp_str, tx, temp_y, seg_h, BLACK)

    hi_lo_str = "Hi:" + state["today_high_str"] + "  Lo:" + state["today_low_str"]
    screen.text(hi_lo_str, icon_cx - len(hi_lo_str) * 4, hi_lo_y, BLACK)

    label = "Chance of precip"
    screen.text(label, icon_cx - len(label) * 4, precip_label_y, BLACK)
    precip_str = state["precip_pct_str"]
    screen.text(precip_str, icon_cx - len(precip_str) * 4, precip_val_y, BLACK)


# ═══════════════════════════════════════════════════════════════════
# Center panel  (humidity + pressure)
# ═══════════════════════════════════════════════════════════════════

def draw_center_panel(screen, state):
    panel_cx = (config.COL1_X + config.COL2_X) // 2 - 15  # 480
    seg_h = 32
    mid_y = (config.TOP_H + config.BOT_Y) // 2  # 135

    # Each half (110 px) centres its block (label 8 + gap 5 + value 32 = 45 px)
    # leaving 32 px margins top and bottom within each half.

    # ── Humidity (upper half) ──
    hy_y = config.TOP_H + 32   # label top: 57
    hum_y = hy_y + 13          # value top: 70  (8px label + 5px gap)
    hy_label = "Humidity"
    screen.text(hy_label, panel_cx - len(hy_label) * 4, hy_y, BLACK)
    hum_str = str(state["humidity"])
    hum_w = draw_large_number(screen, hum_str, panel_cx - 18, hum_y, seg_h, BLACK)
    screen.text("%", panel_cx - 18 + hum_w + 2, hum_y + seg_h - 8, BLACK)
    screen.ellipse(config.COL1_X + 26, hum_y + 11, 7, 10, BLACK)

    # ── Pressure (lower half) ──
    pr_y = mid_y + 32          # label top: 167
    pres_y = pr_y + 13         # value top: 180  (8px label + 5px gap)
    pr_label = state["pressure_label"]
    screen.text(pr_label, panel_cx - len(pr_label) * 4, pr_y, BLACK)
    pres_str = state["pressure_str"]
    pres_w = draw_large_number(screen, pres_str, panel_cx - 28, pres_y, seg_h, BLACK)
    screen.text("inHg", panel_cx - 28 + pres_w + 3, pres_y + seg_h - 8, BLACK)
    ax, ay = config.COL1_X + 20, pres_y + 11
    for i in range(4):
        hw = 10 - i * 2
        screen.hline(ax - hw + i, ay + i * 5, hw * 2 - i * 2, BLACK)


# ═══════════════════════════════════════════════════════════════════
# Right panel  (compass rose)
# ═══════════════════════════════════════════════════════════════════

def draw_right_panel(screen, state):
    compass_cx = (config.COL2_X + config.W) // 2  # 696
    compass_cy = (config.TOP_H + config.BOT_Y) // 2 - 35  # 100
    compass_r = 52
    draw_compass(screen, compass_cx, compass_cy, compass_r,
                 state["wind_dir"])

    # "Wind Speed" label + value, then blank line, then "Wind Gust" label + value
    base_y = compass_cy + compass_r + 19
    spd_label = "Wind Speed"
    screen.text(spd_label,
                compass_cx - len(spd_label) * 4,
                base_y, BLACK)
    spd_str = state["wind_speed_str"]
    screen.text(spd_str,
                compass_cx - len(spd_str) * 4,
                base_y + 10, BLACK)
    gust_label = "Wind Gust"
    screen.text(gust_label,
                compass_cx - len(gust_label) * 4,
                base_y + 28, BLACK)
    gust_str = state["wind_gust_str"]
    screen.text(gust_str,
                compass_cx - len(gust_str) * 4,
                base_y + 38, BLACK)


# ═══════════════════════════════════════════════════════════════════
# Full display draw
# ═══════════════════════════════════════════════════════════════════

def draw_display(screen, state):
    """Render a complete weather screen from a ViewModel display-state dict."""
    screen.fill(WHITE)

    screen.vline(config.COL1_X, config.TOP_H, config.BOT_Y - config.TOP_H, BLACK)
    screen.vline(config.COL2_X, config.TOP_H, config.BOT_Y - config.TOP_H, BLACK)

    draw_top_bar(screen, state)
    draw_bottom_bar(screen, state)
    draw_left_panel(screen, state)
    draw_center_panel(screen, state)
    draw_right_panel(screen, state)
    print("Display updated.")


# ═══════════════════════════════════════════════════════════════════
# City selection screen
# ═══════════════════════════════════════════════════════════════════

def draw_city_select(screen, cities, cursor, temps=None, conditions=None):
    """Render the city-selection list.

    Args:
        cities:     sequence of (name, lat, lon, utc_offset_h) tuples
        cursor:     index of currently highlighted city
        temps:      optional list of temperature strings (one per city, or None
                    if not yet fetched), displayed right-aligned in each row
        conditions: optional list of condition strings (e.g. "Rain"), displayed
                    just to the left of the temperature
    """
    ROW_H = (config.H - config.TOP_H) // len(cities)  # 49 px for 5 cities

    screen.fill(WHITE)

    # Header bar
    label = "SELECT CITY"
    lx = (config.W - len(label) * 8) // 2
    screen.text(label, lx, 7, BLACK)
    screen.hline(0, config.TOP_H - 1, config.W, BLACK)

    for i, city in enumerate(cities):
        name = city[0]
        row_y = config.TOP_H + i * ROW_H

        if i == cursor:
            screen.fill_rect(0, row_y, config.W, ROW_H, BLACK)
            text_color = WHITE
            prefix = "> "
        else:
            text_color = BLACK
            prefix = "  "

        row_text = prefix + name
        tx = (config.W - len(row_text) * 8) // 2
        ty = row_y + (ROW_H - 8) // 2
        screen.text(row_text, tx, ty, text_color)

        if temps is not None and i < len(temps) and temps[i] is not None:
            temp_str = temps[i]
            temp_x = config.W - len(temp_str) * 8 - 10
            screen.text(temp_str, temp_x, ty, text_color)
            if conditions is not None and i < len(conditions) and conditions[i] is not None:
                cond_str = conditions[i]
                screen.text(cond_str, temp_x - len(cond_str) * 8 - 8, ty, text_color)


def draw_forecast(screen, state):
    """Render the 5-day forecast screen."""
    screen.fill(WHITE)
    draw_top_bar(screen, state)
    screen.hline(0, config.BOT_Y, config.W, BLACK)

    # 5 vertical dividers splitting 792px into 6 equal columns (132px each)
    for x in (132, 264, 396, 528, 660):
        screen.vline(x, config.TOP_H, config.BOT_Y - config.TOP_H, BLACK)

    days = state["days"]
    for i, d in enumerate(days):
        cx = i * 132 + 66  # column centre

        def _text(txt, y):
            tx = cx - len(txt) * 4
            screen.text(txt, tx, y, BLACK)

        _text(d["day"],              35)
        _text(d["date"],             50)
        _text(d["condition_str"],    85)
        _text("Hi:" + d["high_str"], 125)
        _text("Lo:" + d["low_str"],  160)
        _text("Precip Chance",        183)
        _text(d["precip_str"],       198)

    screen.show(mode=0)


def draw_error(screen, msg):
    screen.fill(WHITE)
    screen.text("Weather fetch error:", 10, 90, BLACK)
    screen.text(str(msg)[:50], 10, 105, BLACK)
    screen.show(mode=0)
