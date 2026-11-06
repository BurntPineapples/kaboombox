# Copyright (c) 2026 Burnt pineapples
# SPDX-License-Identifier: MIT

# Parts tray for the controller box: lies on top of the legs' floor ring, 4x M2x6 down into the ring.
# Same frame as legs_step.py (Y up, sketch u = X, v = -Z). Layout below in mm, sketch coords.
#  breadboard : full corral along the top (LCD) edge, its own sticky back holds it down
#  ESP32 board: 4 corner Ls only (terminal wires + USB stay free), velcro dot / foam tape under it
#  battery    : 3-wall cradle open toward the button edge, velcro strap through 2 slots;
#               lift the plate+legs out, undo the strap, slide the pack out sideways
# Print slab-down, no supports.
#
# Run: python tray_step.py   (needs: pip install build123d)
# Writes tray_placed.step and tray_print.stl, and copies them to my Inventor folder
# (delete the shutil.copy line if you don't have it).
# Using a different breadboard, ESP32 board or battery pack? Measure it and change
# BB / ESP / BAT below; the walls are built around those sizes. The box numbers on the
# first line must match legs_step.py. The script stops with "a wall hits a leg/gusset"
# if a part no longer fits between the legs.
import shutil
from build123d import *

IN = 25.4
BOX_DEPTH, DROP, PLATE_T, RING_T, DEPTH = 5.500, 0.0625, 0.125, 3.0, 6.100   # = legs_step.py
B = DEPTH - 6.200
Y_TOP = -(BOX_DEPTH - DROP - PLATE_T) * IN + RING_T      # ring top = tray bottom
T, WALL, CLR, H = 3.0, 1.2, 0.5, 6.0     # tray (M2x6 = tray + ring, flush), wall, fit gap, wall height
# Part footprints in mm (width x length). Measure your own parts.
BB  = (57.15, 165.10)                    # breadboard   u x v (2.25 x 6.5 in)
ESP = (63.07, 87.63)                     # ESP32 board  (2.483 x 3.45)
BAT = (64.52, 70.36)                     # 4xAA pack    (2.54 x 2.77)
SCREWS = [(-3.15, 0.33), (-3.15, 8.97), (-5.92, 4.65), (-0.38, 3.0)]   # ring centreline (in), = legs_step.py

c = 0.52
def P(u, v): return (u * IN, v * IN)
oct_ = Polygon(P(B, .05 + c), P(B, 9.25 - c), P(B - c, 9.25), P(-6.2 + c, 9.25), P(-6.2, 9.25 - c),
               P(-6.2, .05 + c), P(-6.2 + c, .05), P(B - c, .05), align=None)
def R(u0, u1, v0, v1): return Pos((u0 + u1) / 2, (v0 + v1) / 2) * Rectangle(abs(u1 - u0), abs(v1 - v0))
def corral(u0, u1, v0, v1):   # part footprint -> wall ring around it
    return R(u0 - CLR - WALL, u1 + CLR + WALL, v0 - CLR - WALL, v1 + CLR + WALL) - R(u0 - CLR, u1 + CLR, v0 - CLR, v1 + CLR)

# keep-out: leg pads + the part of each gusset that sticks up above the ring (+0.5 mm)
keep = []
for u, v in [(-5.775, 8.907), (-5.767, 0.478), (B - 0.430, 0.478), (B - 0.430, 8.848)]:
    u, v = u * IN, v * IN
    su = 1 if u < -3.1 * IN else -1; sv = 1 if v < 4.65 * IN else -1
    keep += [R(u - 6.85, u + 6.85, v - 6.85, v + 6.85),
             R(u, u + su * 38, v - 2.5, v + 2.5), R(u - 2.5, u + 2.5, v, v + sv * 38)]
keep = sum(keep[1:], keep[0])

# layout
u0 = -5.767 * IN + 2.5 + WALL + CLR                       # breadboard just inside the top-edge gussets (keep-out has the 0.5 gap)
bb = (u0, u0 + BB[0], 4.65 * IN - BB[1] / 2, 4.65 * IN + BB[1] / 2)
u1 = bb[1] + 2 * CLR + WALL                               # ESP + battery column, shares the breadboard wall
esp = (u1, u1 + ESP[0], 19 + WALL + CLR, 19 + WALL + CLR + ESP[1])
s1 = esp[3] + CLR + WALL + 0.5                            # strap slot 1 starts here
bat = (u1, u1 + BAT[0], s1 + 3.5 + WALL + CLR, s1 + 3.5 + WALL + CLR + BAT[1])
s2 = bat[3] + CLR + WALL + 0.5

walls = corral(*bb)
walls += corral(*esp) - R(-999, 999, esp[2] + 8, esp[3] - 8) - R(esp[0] + 8, esp[1] - 8, -999, 999)   # corner Ls
bc = (bat[0] + bat[1]) / 2
walls += corral(*bat) - R(bat[1], 999, -999, 999) - R(bc - 6, bc + 6, -999, 999)   # open side + wire notches
assert (walls & keep).area < 1e-6, "a wall hits a leg/gusset"

def place(sk, y, h): return extrude(Plane(origin=(0, y, 0), x_dir=(1, 0, 0), z_dir=(0, 1, 0)) * sk, h)
slab = offset(oct_, -0.03 * IN, kind=Kind.INTERSECTION) - keep
for s in (s1, s2): slab -= R(bc - 13, bc + 13, s, s + 3)      # 1" velcro strap, runs under the tray
for u, v in SCREWS: slab -= Pos(u * IN, v * IN) * Circle(1.2)  # M2 clearance
tray = place(slab, Y_TOP, T) + place(walls, Y_TOP + T, H)
assert len(tray.solids()) == 1

export_step(tray, "tray_placed.step"); export_stl(Rot(90, 0, 0) * tray, "tray_print.stl")
for f in ("tray_placed.step", "tray_print.stl"): shutil.copy(f, r"E:\InventorProjects\Fireworkcontroller")
bb_ = tray.bounding_box()
print(f"tray: {bb_.size.X:.1f} x {bb_.size.Z:.1f} mm, {tray.volume / 1000:.0f} cm3")
for n, r in (("breadboard", bb), ("esp", esp), ("battery", bat)):
    print(f"{n}: u {r[0] / IN:.2f}..{r[1] / IN:.2f}  v {r[2] / IN:.2f}..{r[3] / IN:.2f} in")
