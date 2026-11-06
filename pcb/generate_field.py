"""
FIELD (fuse/igniter box) PCB generator — labeled, single board.
Run with KiCad's bundled Python:
  "E:\\KiCad\\bin\\python.exe" generate_field.py

field/field.kicad_pcb:
  - ESP32 38-pin devkit socket (GPIO # on every pad)
  - 4x 100k sense pull-ups (ch1-4 input-only pins)
  - 8x 10k series resistors (sense pin -> relay NO tap)
  - J_RLY 1x10 header to the ELEGOO relay input row (GND IN1..IN8 VCC)
  - J_SNS 8-pos screw terminal: sense taps out to each relay NO screw
Pin map matches firework_field.ino:
  RELAY IN1..8 = 26,27,14,13,25,33,32,16 ; SENSE1..8 = 36,39,34,35,4,17,18,19

!!! ESP_ROW_SPACING: 25.4mm (1.0") default; measure yours (25.4 or 22.86). !!!
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
TB08 = ("TerminalBlock.pretty", "TerminalBlock_MaiXu_MX126-5.0-08P_1x08_P5.00mm")
HDR10 = ("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x10_P2.54mm_Vertical")

# GPIO number next to each ESP32 socket pin (38-pin devkit, USB down)
ESP_L_LBL = {"1": "3V3", "2": "EN", "3": "36", "4": "39", "5": "34", "6": "35",
             "7": "32", "8": "33", "9": "25", "10": "26", "11": "27", "12": "14",
             "13": "12", "14": "GND", "15": "13", "16": "9", "17": "10",
             "18": "11", "19": "5V"}
ESP_R_LBL = {"1": "GND", "2": "23", "3": "22", "4": "TX", "5": "RX", "6": "21",
             "7": "GND", "8": "19", "9": "18", "10": "5", "11": "17", "12": "16",
             "13": "4", "14": "0", "15": "2", "16": "15", "17": "8", "18": "7",
             "19": "6"}


def build_field():
    b = BoardBuilder(os.path.join(OUT_ROOT, "field", "field.kicad_pcb"))
    b.edge_rect(100, 75)
    for ref, (x, y) in {"H1": (5, 5), "H2": (95, 5),
                        "H3": (5, 70), "H4": (95, 70)}.items():
        b.place("MountingHole.pretty", "MountingHole_3.2mm_M3", ref, "M3", x, y)

    # ESP32 socket. Physical pin -> field net (USB toward bottom edge).
    left = {1: "3V3", 2: None, 3: "SENSE1", 4: "SENSE2", 5: "SENSE3",
            6: "SENSE4", 7: "IN7", 8: "IN6", 9: "IN5", 10: "IN1",
            11: "IN2", 12: "IN3", 13: None, 14: "GND", 15: "IN4",
            16: None, 17: None, 18: None, 19: "5V"}
    right = {1: "GND", 2: None, 3: None, 4: None, 5: None, 6: None,
             7: "GND", 8: "SENSE8", 9: "SENSE7", 10: None, 11: "SENSE6",
             12: "IN8", 13: "SENSE5", 14: None, 15: None, 16: None,
             17: None, 18: None, 19: None}
    j2 = b.place(*SOCKET, "J2", "ESP32 left", 14, 14, 0, left)
    j3 = b.place(*SOCKET, "J3", "ESP32 right", 14 + ESP_ROW_SPACING, 14, 0, right)
    b.label_pads(j2, ESP_L_LBL, dx=-3.4, size=0.7)
    b.label_pads(j3, ESP_R_LBL, dx=3.4, size=0.7)

    # 100k pull-ups for sense channels 1-4 (input-only pins)
    for i in range(4):
        b.place(*RES, "R_P%d" % (i + 1), "100k", 50, 14 + i * 13, 90,
                {1: "SENSE%d" % (i + 1), 2: "3V3"})

    # 10k series resistors: sense pin -> that channel's NO tap
    for i in range(8):
        n = i + 1
        col = i // 4
        row = i % 4
        b.place(*RES, "R_S%d" % n, "10k", 60 + col * 9, 14 + row * 13, 90,
                {1: "SENSE%d" % n, 2: "NO%d" % n})

    # 10-pin header to relay input row: GND IN1..IN8 VCC(5V)
    relay = {1: "GND", 2: "IN1", 3: "IN2", 4: "IN3", 5: "IN4", 6: "IN5",
             7: "IN6", 8: "IN7", 9: "IN8", 10: "5V"}
    rly_fp = b.place(*HDR10, "J_RLY", "to relay module", 26, 69, 90, relay)
    b.label_pads(rly_fp, {"1": "GND", "2": "IN1", "3": "IN2", "4": "IN3",
                          "5": "IN4", "6": "IN5", "7": "IN6", "8": "IN7",
                          "9": "IN8", "10": "VCC"}, dy=-2.4, size=0.85)

    # screw terminal: 8 sense taps out to relay NO screws
    sense = {i + 1: "NO%d" % (i + 1) for i in range(8)}
    sns_fp = b.place(*TB08, "J_SNS", "sense taps to relay NO", 85, 40, 90, sense)
    b.label_pads(sns_fp, {str(i + 1): "CH%d" % (i + 1) for i in range(8)},
                 dx=-4.6, size=1.0)

    # minimal silk in clear space; pad labels (IN1-8, CH1-8, GPIO#) carry detail
    b.text("FIELD ESP32  (USB v down)", 45, 64, 1.0)
    b.save()


build_field()
print("done")
