"""
Single-board CONTROLLER PCB generator (LCD version, no lid/tray split).
Run with KiCad's bundled Python:
  "E:\\KiCad\\bin\\python.exe" generate_controller.py

One board: controller/controller.kicad_pcb
  - ESP32 38-pin devkit socket
  - screw terminals for: 8 fire buttons, 8 channel LEDs, key switch, mode
    button, link LEDs, 16x2 I2C LCD, 5V power
  - 4x 10k button pull-ups (BTN5-8 are input-only pins)
  - 10x 220R (8 channel LEDs + 2 link LEDs)
Panel-mount every control in the box lid and run the wires DOWN to this board.

!!! MEASURE BEFORE ORDERING !!!
ESP_ROW_SPACING = center-to-center of the ESP32's two pin rows.
25.4mm (1.0") for most 38-pin devkits; some are 22.86mm (0.9"). Measure yours.
Board fits a 238 x 159 mm (9-3/8 x 6-1/4 in) box interior with margin.
"""

import os
import pcbnew

FP_ROOT = r"E:\KiCad\share\kicad\footprints"
OUT_ROOT = os.path.dirname(os.path.abspath(__file__))

ESP_ROW_SPACING = 25.4  # mm  <-- MEASURE YOUR ESP32! (25.4 or 22.86)
ORIGIN_X = 100.0
ORIGIN_Y = 100.0


def mm(v):
    return pcbnew.FromMM(v)


def V(x, y):
    return pcbnew.VECTOR2I(mm(ORIGIN_X + x), mm(ORIGIN_Y + y))


class BoardBuilder:
    def __init__(self, path):
        self.board = pcbnew.CreateEmptyBoard()
        self.path = path
        self.nets = {}

    def net(self, name):
        if name not in self.nets:
            n = pcbnew.NETINFO_ITEM(self.board, name)
            self.board.Add(n)
            self.nets[name] = n
        return self.nets[name]

    def place(self, lib, fpname, ref, value, x, y, rot=0, padnets=None):
        fp = pcbnew.FootprintLoad(os.path.join(FP_ROOT, lib), fpname)
        if fp is None:
            raise RuntimeError("footprint not found: %s / %s" % (lib, fpname))
        fp.SetReference(ref)
        fp.SetValue(value)
        fp.SetPosition(V(x, y))
        if rot:
            fp.SetOrientationDegrees(rot)
        self.board.Add(fp)
        if padnets:
            for padnum, netname in padnets.items():
                if netname is None:
                    continue
                pad = fp.FindPadByNumber(str(padnum))
                if pad is None:
                    raise RuntimeError("%s: no pad %s" % (ref, padnum))
                pad.SetNet(self.net(netname))
        return fp

    def edge_rect(self, w, h):
        r = pcbnew.PCB_SHAPE(self.board)
        r.SetShape(pcbnew.SHAPE_T_RECT)
        r.SetStart(V(0, 0))
        r.SetEnd(V(w, h))
        r.SetLayer(pcbnew.Edge_Cuts)
        r.SetWidth(mm(0.1))
        self.board.Add(r)

    def text(self, s, x, y, size=1.2):
        t = pcbnew.PCB_TEXT(self.board)
        t.SetText(s)
        t.SetPosition(V(x, y))
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
        t.SetTextThickness(mm(0.2))
        self.board.Add(t)

    def label_pads(self, fp, mapping, dx=0.0, dy=0.0, size=0.9):
        for pad in fp.Pads():
            num = pad.GetNumber()
            if num not in mapping:
                continue
            t = pcbnew.PCB_TEXT(self.board)
            t.SetText(mapping[num])
            pos = pad.GetPosition()
            t.SetPosition(pcbnew.VECTOR2I(int(pos.x + mm(dx)), int(pos.y + mm(dy))))
            t.SetLayer(pcbnew.F_SilkS)
            t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
            t.SetTextThickness(mm(0.15))
            self.board.Add(t)

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        pcbnew.SaveBoard(self.path, self.board)
        print("saved", self.path)


SOCKET = ("Connector_PinSocket_2.54mm.pretty", "PinSocket_1x19_P2.54mm_Vertical")
RES = ("Resistor_THT.pretty", "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal")
TB02 = ("TerminalBlock.pretty", "TerminalBlock_MaiXu_MX126-5.0-02P_1x02_P5.00mm")
TB03 = ("TerminalBlock.pretty", "TerminalBlock_MaiXu_MX126-5.0-03P_1x03_P5.00mm")
TB04 = ("TerminalBlock.pretty", "TerminalBlock_MaiXu_MX126-5.0-04P_1x04_P5.00mm")
TB09 = ("TerminalBlock.pretty", "TerminalBlock_MaiXu_MX126-5.0-09P_1x09_P5.00mm")


def build():
    b = BoardBuilder(os.path.join(OUT_ROOT, "controller", "controller.kicad_pcb"))
    b.edge_rect(100, 84)  # <=100x100 -> JLCPCB cheap tier
    for ref, (x, y) in {"H1": (4, 4), "H2": (96, 4),
                        "H3": (4, 80), "H4": (96, 80)}.items():
        h = b.place("MountingHole.pretty", "MountingHole_3.2mm_M3", ref, "M3", x, y)
        h.Reference().SetVisible(False)  # keep tiny hole labels off the board edge

    # ---- ESP32 socket (38-pin devkit, USB toward BOTTOM edge, pin1 top) ----
    left = {1: "3V3", 2: None, 3: "BTN7", 4: "BTN8", 5: "BTN5", 6: "BTN6",
            7: "LED7", 8: "LED8", 9: "BTN3", 10: "BTN4", 11: "KEY_ALL",
            12: "BTN2", 13: "LED_FAIL", 14: "GND", 15: "BTN1",
            16: None, 17: None, 18: None, 19: "5V"}
    right = {1: "GND", 2: "LED5", 3: "LED4", 4: None, 5: None, 6: "LED3",
             7: "GND", 8: "LED2", 9: "LED6", 10: "LCD_SCL", 11: "KEY_ARM",
             12: "LCD_SDA", 13: "LED1", 14: None, 15: "LED_PASS",
             16: "MODE_BTN", 17: None, 18: None, 19: None}
    j2 = b.place(*SOCKET, "J2", "ESP32 left", 22, 18, 0, left)
    j3 = b.place(*SOCKET, "J3", "ESP32 right", 22 + ESP_ROW_SPACING, 18, 0, right)
    # GPIO number next to each socket pin (matches a 38-pin devkit, USB down)
    esp_left_lbl = {"1": "3V3", "2": "EN", "3": "36", "4": "39", "5": "34",
                    "6": "35", "7": "32", "8": "33", "9": "25", "10": "26",
                    "11": "27", "12": "14", "13": "12", "14": "GND", "15": "13",
                    "16": "9", "17": "10", "18": "11", "19": "5V"}
    esp_right_lbl = {"1": "GND", "2": "23", "3": "22", "4": "TX", "5": "RX",
                     "6": "21", "7": "GND", "8": "19", "9": "18", "10": "5",
                     "11": "17", "12": "16", "13": "4", "14": "0", "15": "2",
                     "16": "15", "17": "8", "18": "7", "19": "6"}
    b.label_pads(j2, esp_left_lbl, dx=-3.4, size=0.7)
    b.label_pads(j3, esp_right_lbl, dx=3.4, size=0.7)

    # ---- connectors (each pad silk-labeled with its function) ----
    btn = {i: "BTN%d" % i for i in range(1, 9)}; btn[9] = "GND"
    btn_fp = b.place(*TB09, "J_BTN", "fire buttons 1-8 +GND", 12, 8, 0, btn)
    b.label_pads(btn_fp, {str(i): "B%d" % i for i in range(1, 9)} | {"9": "GND"},
                 dy=3.2, size=0.85)

    led = {i: "LED%d_A" % i for i in range(1, 9)}; led[9] = "GND"
    led_fp = b.place(*TB09, "J_LED", "channel LEDs 1-8 +GND", 12, 76, 0, led)
    b.label_pads(led_fp, {str(i): "L%d" % i for i in range(1, 9)} | {"9": "GND"},
                 dy=3.2, size=0.85)

    # right-edge stack of the small connectors (TB origin = left pad)
    lcd_fp = b.place(*TB04, "J_LCD", "16x2 I2C LCD", 74, 8, 0,
                     {1: "GND", 2: "5V", 3: "LCD_SDA", 4: "LCD_SCL"})
    b.label_pads(lcd_fp, {"1": "GND", "2": "VCC", "3": "SDA", "4": "SCL"},
                 dy=3.2, size=0.85)

    pwr_fp = b.place(*TB02, "J_PWR", "5V power in", 76, 22, 0, {1: "5V", 2: "GND"})
    b.label_pads(pwr_fp, {"1": "5V", "2": "GND"}, dy=3.2, size=0.85)

    key_fp = b.place(*TB03, "J_KEY", "key switch", 74, 36, 0,
                     {1: "3V3", 2: "KEY_ARM", 3: "KEY_ALL"})
    b.label_pads(key_fp, {"1": "3V3", "2": "ARM", "3": "ALL"}, dy=3.2, size=0.85)

    lnk_fp = b.place(*TB03, "J_LNK", "link LEDs G/R +GND", 74, 50, 0,
                     {1: "GND", 2: "LNKG_A", 3: "LNKR_A"})
    b.label_pads(lnk_fp, {"1": "GND", "2": "GRN", "3": "RED"}, dy=3.2, size=0.85)

    mode_fp = b.place(*TB02, "J_MODE", "mode button", 76, 64, 0,
                      {1: "MODE_BTN", 2: "GND"})
    b.label_pads(mode_fp, {"1": "MODE", "2": "GND"}, dy=3.2, size=0.85)

    # ---- resistors: horizontal (rot 0), tidy column; origin=left pad, +10mm ----
    for i, sig in enumerate(["BTN5", "BTN6", "BTN7", "BTN8"]):
        b.place(*RES, "R_P%d" % (i + 1), "10k", 54, 16 + i * 4, 0,
                {1: sig, 2: "3V3"})
    b.place(*RES, "R_LG", "220", 54, 33, 0, {1: "LED_PASS", 2: "LNKG_A"})
    b.place(*RES, "R_LR", "220", 54, 37, 0, {1: "LED_FAIL", 2: "LNKR_A"})
    for i in range(8):
        n = i + 1
        b.place(*RES, "R_C%d" % n, "220", 54, 42 + i * 4, 0,
                {1: "LED%d" % n, 2: "LED%d_A" % n})

    # ---- silk: title top-middle (gap between J_BTN and J_LCD) ----
    b.text("FIREWORK", 63, 7, 1.0)
    b.text("CONTROLLER", 63, 12, 1.0)
    b.text("ESP32  (USB v down)", 35, 68, 0.9)
    b.save()


build()
print("done")
