# Copyright (c) 2026 Burnt pineapples
# SPDX-License-Identifier: MIT

# Legs for the 9.200 x 6.100" plate, one printed part, placed in the Inventor frame
# (Y up, plate bottom at Y=0, X -0.1..-6.2 = button edge..top edge, Z -0.05..-9.25).
# Floor ring + 4 corner legs + 45° gussets. Legs go straight up to the plate
# underside; an M2 screw through each plate corner hole bites into the leg top.
# Leg/part positions come from Controller_9.200.stl (bottom-face loops); button-side ones follow the
# button edge, which shrink_plate.py moved in by 6.200-DEPTH.
#
# Run: python legs_step.py   (needs: pip install build123d)
# Writes legs_placed.step, legs_print.stl and legs_test.stl into this folder, and copies
# them to my Inventor folder (delete the shutil.copy lines if you don't have it).
# For a different box, measure its inside depth and change BOX_DEPTH. The leg positions
# match the plate's corner holes; if you move a hole, change `legs` here AND LEGS in
# plate_test.py. The script stops with "a leg hits a part" if a leg would land on a
# button, the key switch or the power switch.
import shutil
from build123d import *

IN = 25.4
BOX_DEPTH = 5.500   # floor -> rim top (in), measured twice
DROP      = 0.0625  # plate top sits this far under the rim so the LCD pod clears when closing
PLATE_T   = 0.125   # final plate thickness (in)
RING_T    = 3.0     # mm, floor ring thickness
DEPTH     = 6.100   # plate depth (in), = shrink_plate.py NEW_D
B         = DEPTH - 6.200   # button edge X (0 -> -0.1)
Y_FLOOR   = -(BOX_DEPTH - DROP - PLATE_T) * IN

def P(u, v): return (u * IN, v * IN)          # sketch coords: u = X, v = -Z  (inches)
def rect(u0, u1, v0, v1):
    return Pos((u0 + u1) / 2 * IN, (v0 + v1) / 2 * IN) * Rectangle(abs(u1 - u0) * IN, abs(v1 - v0) * IN)
def circ(u, v, r): return Pos(u * IN, v * IN) * Circle(r * IN)
def place(sk, y, h): return extrude(Plane(origin=(0, y, 0), x_dir=(1, 0, 0), z_dir=(0, 1, 0)) * sk, h)

c = 0.52
oct_ = Polygon(P(B, .05 + c), P(B, 9.25 - c), P(B - c, 9.25), P(-6.2 + c, 9.25), P(-6.2, 9.25 - c),
               P(-6.2, .05 + c), P(-6.2 + c, .05), P(B - c, .05), align=None)
def inset(d): return offset(oct_, -d * IN, kind=Kind.INTERSECTION)

legs = [(-5.775, 8.907), (-5.767, 0.478), (B - 0.430, 0.478), (B - 0.430, 8.848)]   # = plate corner holes
keep = [circ(-0.723, 4.672, .418), circ(-4.739, 0.996, 0.62), circ(-4.742, 8.343, 0.65),  # mode, power, key
        circ(-5.327, 8.343, .20), circ(-4.189, 8.343, .20)]                              # key screws
keep += [circ(-1.565, 0.996 + 1.05 * k, .418) for k in (0, 7)]                         # end fire buttons
keep = sum(keep[1:], keep[0])

legs_out = inset(0.03)
base = place(legs_out - inset(0.53), Y_FLOOR, RING_T)                                    # floor ring
for u, v in legs:
    pad = legs_out & rect(u - .25, u + .25, v - .25, v + .25)
    assert (pad & keep).area < 1e-6, "a leg hits a part"
    base += place(pad, Y_FLOOR, -Y_FLOOR)                                                # leg to plate
    su = 1 if u < -3.1 else -1          # toward the middle in X
    sz = -1 if v < 4.65 else 1          # toward the middle in global Z (= -v)
    for xd, zd in [((su, 0, 0), (0, 0, su)), ((0, 0, sz), (-sz, 0, 0))]:
        pl = Plane(origin=(u * IN, Y_FLOOR, -v * IN), x_dir=xd, z_dir=zd)
        base += extrude(pl * Polygon((0, 0), (40, 0), (0, 40), align=None), 2, both=True)  # 45° gusset
    base -= Pos(u * IN, 0, -v * IN) * Rot(90, 0, 0) * Cylinder(0.8, 2 * 14)               # M2 pilot 1.6 mm, 14 deep

for u, v in [(-3.15, 0.33), (-3.15, 8.97), (-5.92, 4.65), (-0.38, 3.0)]:   # tray screws, = tray_step.py
    base -= Pos(u * IN, Y_FLOOR, -v * IN) * Rot(90, 0, 0) * Cylinder(0.8, 20)     # M2 pilot through the ring

assert len(base.solids()) == 1
export_step(base, "legs_placed.step")
export_stl(Rot(90, 0, 0) * base, "legs_print.stl")
for f in ("legs_placed.step", "legs_print.stl"):
    shutil.copy(f, r"E:\InventorProjects\Fireworkcontroller")
bb = base.bounding_box()
print(f"legs: {bb.size.X:.1f} x {bb.size.Z:.1f} mm, {bb.size.Y:.2f} tall ({bb.size.Y/IN:.3f} in), "
      f"{base.volume/1000:.0f} cm3")

# test slice: floor ring + bottom 15 mm of the legs/gussets -> checks the footprint in the box floor
test = base & Pos(0, Y_FLOOR, 0) * Box(1000, 30, 1000, align=(Align.CENTER, Align.MIN, Align.CENTER))
test = test & Pos(0, Y_FLOOR, 0) * Box(1000, 15, 1000, align=(Align.CENTER, Align.MIN, Align.CENTER))
export_stl(Rot(90, 0, 0) * test, "legs_test.stl"); shutil.copy("legs_test.stl", r"E:\InventorProjects\Fireworkcontroller")
print(f"legs test: {test.volume / 1000:.0f} cm3")
