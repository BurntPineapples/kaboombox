# Copyright (c) 2026 Burnt pineapples
# SPDX-License-Identifier: MIT
# Regenerate the wiring SVGs from the sketches: python docs/make_wiring.py .
# Generates docs/wiring-controller.svg and docs/wiring-field.svg from the pin maps in the sketches.
import re, sys, os

root = sys.argv[1]
ctrl = open(os.path.join(root, "firmware/firework_controller/firework_controller.ino"), encoding="utf-8").read()
fld = open(os.path.join(root, "firmware/firework_field/firework_field.ino"), encoding="utf-8").read()

def arr(src, name):
    return [int(x) for x in re.search(name + r"\[8\]\s*=\s*\{([^}]*)\}", src).group(1).split(",")]

def const(src, name):
    return int(re.search(r"const int " + name + r"\s*=\s*(\d+)", src).group(1))

BTN, LED = arr(ctrl, "BTN_PIN"), arr(ctrl, "LED_PIN")
KEY_A, KEY_ALL, MODE = const(ctrl, "PIN_KEY_ARMED"), const(ctrl, "PIN_KEY_ALL"), const(ctrl, "PIN_MODE_BTN")
LG, LR, SDA, SCL = (const(ctrl, n) for n in ("PIN_LED_PASS", "PIN_LED_FAIL", "PIN_LCD_SDA", "PIN_LCD_SCL"))
RELAY, SENSE = arr(fld, "RELAY_PIN"), arr(fld, "SENSE_PIN")

INK, MUTED, SIG, PWR, GND, SNS, BOX = "#1d2329", "#5b6670", "#2563eb", "#d42a2a", "#1d2329", "#d97706", "#f3f5f7"

def svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="13">\n'
            f'<title>{title}</title>\n<rect width="{w}" height="{h}" fill="#ffffff"/>\n' + "\n".join(body) + "\n</svg>\n")

def t(x, y, s, size=13, fill=INK, anchor="start", weight="normal"):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{s}</text>'

def box(x, y, w, h, fill=BOX, stroke=INK, r=6):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'

def line(x1, y1, x2, y2, c=SIG, wdt=2, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" stroke-width="{wdt}"{d}/>'

def res(cx, y, label, c=SIG):   # small resistor box centred on a wire
    return box(cx - 22, y - 7, 44, 14, "#ffffff", c, 2) + t(cx, y - 11, label, 11, MUTED, "middle")

def legend(x, y, items):
    out = []
    for i, (c, s) in enumerate(items):
        out += [line(x, y + i * 18, x + 26, y + i * 18, c, 3), t(x + 34, y + i * 18 + 4, s, 12, MUTED)]
    return out

# ---------------- panel box ----------------
W, H, ROW, Y0 = 1040, 900, 46, 130
ex0, ex1 = 430, 610
left = [(f"Fire button {i+1}", f"GPIO {p}", "other leg → GND" + (" · 10k pull-up to 3V3" if p >= 34 else "")) for i, p in enumerate(BTN)]
left += [("MODE button", f"GPIO {MODE}", "other leg → GND"),
         ("Key: ARMED contact", f"GPIO {KEY_A}", "key common → 3V3"),
         ("Key: ARMED ALL contact", f"GPIO {KEY_ALL}", "key common → 3V3")]
right = [(f"Channel LED {i+1}", f"GPIO {p}", "220Ω", "− leg → GND") for i, p in enumerate(LED)]
right += [("LINK LED green", f"GPIO {LG}", "220Ω", "− leg → GND"), ("LINK LED red", f"GPIO {LR}", "220Ω", "− leg → GND"),
          ("LCD SDA", f"GPIO {SDA}", "", "I2C backpack"), ("LCD SCL", f"GPIO {SCL}", "", "I2C backpack")]
n = max(len(left), len(right))
b = [t(W / 2, 40, "Panel box (controller) wiring", 22, INK, "middle", "bold"),
     t(W / 2, 64, "ESP32 38-pin dev board · pins from firmware/firework_controller/firework_controller.ino", 13, MUTED, "middle"),
     box(ex0, Y0 - 30, ex1 - ex0, n * ROW + 20, "#e8eef6"), t((ex0 + ex1) / 2, Y0 + n * ROW / 2 - 6, "ESP32", 22, INK, "middle", "bold"),
     t((ex0 + ex1) / 2, Y0 + n * ROW / 2 + 16, "38-pin dev board", 12, MUTED, "middle")]
for i, (name, pin, note) in enumerate(left):
    y = Y0 + i * ROW
    b += [line(260, y, ex0, y), t(ex0 + 8, y + 4, pin, 12, SIG, weight="bold"),
          box(30, y - 17, 230, 34), t(42, y - 2, name, 13, INK, weight="bold"), t(42, y + 12, note, 11, MUTED)]
for i, (name, pin, r, note) in enumerate(right):
    y = Y0 + i * ROW
    b += [line(ex1, y, 780, y), t(ex1 - 8, y + 4, pin, 12, SIG, "end", "bold"), box(780, y - 17, 230, 34),
          t(792, y - 2, name, 13, INK, weight="bold"), t(792, y + 12, note, 11, MUTED)]
    if r:
        b.append(res(695, y, r))
py = Y0 + n * ROW + 20
b += [box(30, py, 980, 120, "#fff7f7", PWR),
      t(46, py + 26, "Power", 15, INK, weight="bold"),
      t(46, py + 50, "4× AA pack (+) → POWER toggle → ESP32 5V pin and LCD VCC.   4× AA pack (−) → GND.", 13),
      t(46, py + 72, "ESP32 3V3 → key switch common and the four 10k pull-ups (buttons 5-8: GPIO 34, 35, 36, 39 have no internal pull-up).", 13),
      t(46, py + 94, "Every button's other leg, every LED's − leg and LCD GND go to a shared GND rail. NiMH AAs (4.8 V) are kinder to the LCD than fresh alkalines.", 13)]
b += legend(30, H - 26, [(SIG, "signal wire to an ESP32 GPIO")])
b.append(t(W - 30, H - 20, "Default LCD I2C address 0x27 (some backpacks are 0x3F).", 12, MUTED, "end"))
open(os.path.join(root, "docs/wiring-controller.svg"), "w", encoding="utf-8").write(svg(W, H, b, "Panel box wiring"))

# ---------------- field box ----------------
W, H, ROW, Y0 = 1120, 900, 58, 150
ex0, ex1, rx0, rx1 = 40, 210, 330, 520
COMX, NOX, CLIPA, IGN0, IGN1, NEGX = 560, 600, 690, 720, 840, 960
b = [t(W / 2, 40, "Field box wiring", 22, INK, "middle", "bold"),
     t(W / 2, 64, "ESP32 + ELEGOO 8-channel 5 V relay module · pins from firmware/firework_field/firework_field.ino", 13, MUTED, "middle"),
     box(ex0, Y0 - 40, ex1 - ex0, 8 * ROW + 40, "#e8eef6"), t((ex0 + ex1) / 2, Y0 - 16, "ESP32", 18, INK, "middle", "bold"),
     box(rx0, Y0 - 40, rx1 - rx0, 8 * ROW + 40), t((rx0 + rx1) / 2, Y0 - 22, "8-ch relay module", 14, INK, "middle", "bold"),
     t((rx0 + rx1) / 2, Y0 - 8, "inputs are active LOW", 11, MUTED, "middle"),
     t(COMX, Y0 - 50, "COM", 12, PWR, "middle", "bold"), t(NOX + 4, Y0 - 50, "NO", 12, INK, "middle", "bold"),
     t(CLIPA, Y0 - 50, "clip A", 12, INK, "middle"), t((IGN0 + IGN1) / 2, Y0 - 50, "firework / igniter", 12, INK, "middle"),
     t(NEGX, Y0 - 50, "NEG bus (Wago)", 12, INK, "middle", "bold")]
for i in range(8):
    y = Y0 + i * ROW
    b += [line(ex1, y, rx0, y), t(ex1 - 8, y + 4, f"GPIO {RELAY[i]}", 12, SIG, "end", "bold"),
          t(rx0 + 10, y + 4, f"IN{i+1}", 12, INK, weight="bold"), t(rx1 - 10, y + 4, f"relay {i+1}", 12, MUTED, "end"),
          line(rx1, y - 8, COMX, y - 8, PWR, 2), f'<circle cx="{COMX}" cy="{y-8}" r="4" fill="{PWR}"/>',
          line(rx1, y + 6, CLIPA - 5, y + 6, PWR, 2),
          f'<circle cx="{CLIPA}" cy="{y+6}" r="5" fill="#ffffff" stroke="{INK}" stroke-width="1.5"/>',
          line(CLIPA + 5, y + 6, IGN0, y + 6, PWR, 2), box(IGN0, y - 5, IGN1 - IGN0, 22, "#fff4e0", SNS, 4),
          t((IGN0 + IGN1) / 2, y + 10, f"ch {i+1}", 12, INK, "middle"),
          line(IGN1, y + 6, NEGX - 30, y + 6, GND, 2),
          f'<circle cx="{NEGX-30}" cy="{y+6}" r="5" fill="#ffffff" stroke="{INK}" stroke-width="1.5"/>',
          line(NEGX - 25, y + 6, NEGX, y + 6, GND, 2),
          t(NOX + 6, y + 31, f"sense: NO → 10k → GPIO {SENSE[i]}" + (" (+100k pull-up to 3V3)" if i < 4 else ""), 11, SNS)]
yb = Y0 + 7 * ROW
by = yb + 110
b += [line(COMX, Y0 - 8, COMX, by + 28, PWR, 3), line(NEGX, Y0 + 6, NEGX, by + 28, GND, 3),
      box(COMX - 18, yb + 34, 36, 44, "#ffffff", PWR, 4), t(COMX, yb + 54, "10A", 11, PWR, "middle", "bold"),
      t(COMX, yb + 68, "fuse", 11, PWR, "middle"), t(COMX + 26, yb + 60, "pull to make safe", 11, PWR),
      box(640, by, 220, 56, "#fff7f7", PWR), t(750, by + 24, "12 V SLA battery", 14, INK, "middle", "bold"),
      t(652, by + 33, "+", 16, PWR, weight="bold"), t(848, by + 33, "−", 16, INK, "end", "bold"),
      line(COMX, by + 28, 640, by + 28, PWR, 3), line(860, by + 28, NEGX, by + 28, GND, 3)]
gy = Y0 + 8 * ROW + 40
b += [line(ex1, gy, rx0, gy, GND, 2), t(ex1 - 8, gy + 4, "GND", 12, INK, "end", "bold"), t(rx0 + 10, gy + 4, "GND", 12, INK, weight="bold"),
      line(ex1, gy + 24, rx0, gy + 24, PWR, 2), t(ex1 - 8, gy + 28, "5V / VIN", 12, PWR, "end", "bold"), t(rx0 + 10, gy + 28, "VCC", 12, INK, weight="bold"),
      t((ex1 + rx0) / 2, gy + 50, "power header", 11, MUTED, "middle")]
ny = H - 150
b += [box(30, ny, W - 60, 96, "#f8fafc", MUTED),
      t(46, ny + 24, "Notes", 15, INK, weight="bold"),
      t(46, ny + 46, "The 12 V + is fused, then daisy-chained screw to screw across COM1-COM8. Each NO goes to clip A; clip B of every channel returns to the NEG Wago bus.", 13),
      t(46, ny + 66, "The fuse is the master safety: pull it and the firing circuit is dead whatever the software does. The ESP32 is USB-powered; its 5V/VIN feeds the relay module VCC.", 13),
      t(46, ny + 86, "Continuity: an igniter on a channel pulls its sense pin LOW through the 10k series resistor, which also protects the pin from 12 V while the relay fires.", 13)]
b += legend(30, H - 40, [(SIG, "signal"), (PWR, "+12 V / +5 V")])
b += legend(250, H - 40, [(GND, "return / GND"), (SNS, "continuity sense")])
b += [f'<circle cx="490" cy="{H-40}" r="4" fill="{PWR}"/>', t(502, H - 36, "dot = wires joined; wires that cross without a dot are not connected", 12, MUTED)]
open(os.path.join(root, "docs/wiring-field.svg"), "w", encoding="utf-8").write(svg(W, H, b, "Field box wiring"))
print("ok", BTN, LED, RELAY, SENSE)
