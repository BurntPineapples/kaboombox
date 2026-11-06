# Copyright (c) 2026 Burnt pineapples
# SPDX-License-Identifier: MIT

# Field unit parts for the ammo can. Frame: Z up, Z=0 = rim top (prop) / floor (plate),
# X along the can length (0 = can centre, front/latch wall inside face at -CAN_L/2), Y centered.
#  field_floor  : insulating floor plate, parts self-tap into it (M2 -> 1.6 mm pilot, same screws as the controller).
#                 Perimeter skirt underneath clears the pressed rib in the can floor.
#                 Print skirt-up (top face on the bed), no supports.
#  field_prop   : window frame on the FRONT rim only. Bottom groove clamps the rim, top groove takes the
#                 lid's front lip, whose bottom edge rests on the ledge GAP_FRONT up. Lid + can lock it.
#                 Wires (and later a brush strip) go through the open window.
#                 STEP is placed in the can; STL prints standing on its end (use a brim), no supports.
#
# Run: python field_step.py   (needs: pip install build123d)
# Writes field_floor / field_prop .step + .stl and two quick fit-test STLs into this folder.
# To fit a different can, measure it and change the can numbers just below; everything
# else is worked out from them. The shutil.copy lines also drop copies into my Inventor
# folder; delete them if you don't have that folder.
import shutil
from build123d import *

IN = 25.4
# Can dimensions, in inches. Measure your can and change these first.
CAN_L        = 10.875         # inside length at the rim (measured ~11, minus 1/8 for safety)
CAN_W_MIN    = 5.5            # inside width at the rim
R_CORN       = 0.375          # can inside corner radius (guess, big = safe); the prop stops where the corner curve starts
RIM_T        = 0.080          # rim (can wall) thickness, caliper
LID_T        = 0.050          # lid lip sheet thickness, caliper
LID_GAP      = 0.04           # lid lip inside face -> rim outside face, lid closed (guess)
FLOOR_L, FLOOR_W = 10.625, 5.25  # floor plate size (inside floor minus clearance)
GAP_FRONT    = 1.0            # rim top -> bottom edge of the lid's front lip (max 1" or the sides open)
# Window frame (prop) sizes, in mm. CLR is the fit gap: raise it if the frame is too tight on the rim.
CLR, WALL, DEPTH = 0.5, 2.5, 10.0      # fit gap, groove wall thickness, body depth into the can
SLEEVE_D, LEG_D, LIP_H = 12.0, 8.0, 6.0  # rim groove: inside sleeve / outside leg depth; lid lip groove depth
TILT = 1.0                             # extra lid groove width: the propped lid tilts ~8 deg over LIP_H
POST, TOP, BOT = 10.0, 6.0, 2.0        # window side posts, rail above / below the window

def rrect(l, w, r): return RectangleRounded(l, w, r)

# Floor plate
PLATE_T, SKIRT_H, SKIRT_W = 5.0, 6.0, 3.0   # mm: plate thickness, skirt height (clears the floor rib), skirt wall
fl = extrude(rrect(FLOOR_L * IN, FLOOR_W * IN, 0.375 * IN), PLATE_T)
ring = rrect(FLOOR_L * IN, FLOOR_W * IN, 0.375 * IN) - rrect(FLOOR_L * IN - 2 * SKIRT_W, FLOOR_W * IN - 2 * SKIRT_W, 0.375 * IN - SKIRT_W)
fl += extrude(ring, -SKIRT_H)
for sx in (-1, 1):   # finger holes to lift it out
    fl -= Pos(sx * (FLOOR_L / 2 - 0.75) * IN, 0, 0) * Cylinder(11, 50)
fl = Pos(0, 0, SKIRT_H) * fl          # skirt bottom on the can floor

# Front window frame ("prop")
HW = (CAN_W_MIN / 2 - R_CORN) * IN               # half width: straight part of the rim / lid lip only
def blk(xa, xb, za, zb): return Pos((xa + xb) / 2, 0, (za + zb) / 2) * Box(xb - xa, 2 * HW, zb - za)
x0 = -CAN_L / 2 * IN                             # front wall inside face (outside is -X)
r_out = x0 - RIM_T * IN                          # rim outside face
l_in = r_out - LID_GAP * IN                      # lid lip inside face
g_in, g_out = l_in + CLR + TILT, l_in - LID_T * IN - CLR   # lid lip groove
xo, G = g_out - WALL, GAP_FRONT * IN
prop = blk(xo, x0 + DEPTH, 0, G)                                            # body, lid lip edge sits on top
prop += blk(xo, g_out, G, G + LIP_H) + blk(g_in, g_in + WALL, G, G + LIP_H)  # lid lip groove walls
prop += blk(x0 + CLR, x0 + CLR + WALL, -SLEEVE_D, 0)                        # rim groove: sleeve inside the wall
prop += blk(r_out - CLR - WALL, r_out - CLR, -LEG_D, 0)                     #             leg outside the wall
win_w, win_h = 2 * (HW - POST), G - TOP - BOT
prop -= Pos(x0, 0, BOT) * Box(100, win_w, win_h, align=(Align.CENTER, Align.CENTER, Align.MIN))
print(f"rim groove {r_out - CLR:.2f}..{x0 + CLR:.2f}, lid groove {g_out:.2f}..{g_in:.2f} (x, mm)")

stand = Rot(90, 0, 0)                            # print standing on its end
assert len(fl.solids()) == 1 and len(prop.solids()) == 1
for name, part, stl in (("field_floor", fl, fl), ("field_prop", prop, stand * prop)):
    export_step(part, name + ".step"); export_stl(stl, name + ".stl")
    for ext in (".step", ".stl"):
        shutil.copy(name + ext, r"E:\InventorProjects\Fireworkcontroller")
    bb = part.bounding_box()
    print(f"{name}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, {part.volume / 1000:.0f} cm3")
print(f"prop window {win_w:.0f} x {win_h:.1f} mm ({win_w / IN:.2f} x {win_h / IN:.2f} in)")

# prop test: 15 mm end slice (post + both grooves) -> checks the rim and lid lip fit fast
pt = prop & Pos(0, HW - 7.5, 0) * Box(1000, 15, 1000)
export_stl(stand * pt, "field_prop_test.stl"); shutil.copy("field_prop_test.stl", r"E:\InventorProjects\Fireworkcontroller")
print(f"prop test: {pt.volume / 1000:.1f} cm3")

# floor test: 2 mm outline ring of the floor plate -> checks length/width/corners in the can
ft = extrude(rrect(FLOOR_L * IN, FLOOR_W * IN, 0.375 * IN) - rrect(FLOOR_L * IN - 12, FLOOR_W * IN - 12, 0.375 * IN - 6), 2)
export_stl(ft, "field_floor_test.stl"); shutil.copy("field_floor_test.stl", r"E:\InventorProjects\Fireworkcontroller")
print(f"floor test: {ft.volume / 1000:.0f} cm3")
