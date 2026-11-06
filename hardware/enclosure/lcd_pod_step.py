# Copyright (c) 2026 Burnt pineapples
# SPDX-License-Identifier: MIT

"""30-degree LCD pod as real solids for Inventor (STEP).
Axes match the Inventor plate: X = across width (centered), Y = toward the
top edge (back), Z = up. Origin = front-bottom-center edge of the pod
(sits on the plate top). Units: mm in the STEP (Inventor converts).
Outputs: lcd_pod_30.step (Join to plate), lcd_pod_cutter.step (Cut plate)."""
import math
from build123d import *

# ---- LCD (verify with calipers) ----
mod_h, win_w, win_l = 7.0, 72.0, 25.2      # board-front->bezel face, window
hole_x, hole_y = 75.0, 31.0                # mounting-hole spacing
pilot, boss_d = 1.6, 5.0                   # M2 self-tap (same screws as the legs)
# ---- shape ----
ang, Ls, t, wall, W, roof, uc, back_h = 30, 46, 2.5, 2.5, 120, 45, 24, 8
h0 = 3.5   # front lip: lifts the slab so nothing dips below the plate top
c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
B = (Ls*c, h0 + Ls*s)
Dback = B[0] + (B[1]-back_h)/math.tan(math.radians(roof))

def meet(p1, d1, p2, d2):
    det = d1[0]*(-d2[1]) - d1[1]*(-d2[0])
    rx, ry = p2[0]-p1[0], p2[1]-p1[1]
    a = (rx*(-d2[1]) - ry*(-d2[0]))/det
    return (p1[0]+a*d1[0], p1[1]+a*d1[1])

u = (c, s); L0 = (t*s, h0 - t*c)                            # slab back line
rd = (math.cos(math.radians(roof)), -math.sin(math.radians(roof)))
rn = (-math.sin(math.radians(roof)), -math.cos(math.radians(roof)))
R0 = (B[0]+wall*rn[0], B[1]+wall*rn[1])                    # roof inner line
BK = (Dback-wall, 0.0)                                      # back inner line
P1 = meet(L0, u, (wall,0), (0,1)); P2 = meet(L0, u, R0, rd)   # front inner wall at y=wall
P3 = meet(R0, rd, BK, (0,1));     P4 = (Dback-wall, -10); P0 = (wall, -10)

outer = extrude(Plane.YZ * Polygon(*[(0,0), (0,h0), B, (Dback, back_h), (Dback,0)], align=None), amount=W/2, both=True)
inner = extrude(Plane.YZ * Polygon(*[P0,P1,P2,P3,P4], align=None), amount=W/2-wall, both=True)
pod = outer - inner

slab = Plane(origin=(0,0,h0), x_dir=(0,c,s), z_dir=(0,-s,c))   # x up-slope, z outward
def at(uu, vv, ww): return Plane(origin=slab.from_local_coords((uu,vv,ww)), x_dir=slab.x_dir, z_dir=slab.z_dir)
L_boss = mod_h - t + 0.5
above_plate = Pos(0,0,50.5) * Box(2000, 2000, 100)
for su in (-1,1):
    for sv in (-1,1):
        uu, vv = uc+su*hole_y/2, sv*hole_x/2
        pod += at(uu, vv, -mod_h) * Cylinder(boss_d/2, L_boss, align=(Align.CENTER,Align.CENTER,Align.MIN))
        vend = sv*(W/2-wall+0.5)
        rib = at(uu, (vv+vend)/2, -mod_h) * Box(boss_d, abs(vend-vv), L_boss, align=(Align.CENTER,Align.CENTER,Align.MIN))
        pod += rib & above_plate
pod -= at(uc, 0, 1) * Box(win_l, win_w, mod_h+2, align=(Align.CENTER,Align.CENTER,Align.MAX))   # flush window
for su in (-1,1):
    for sv in (-1,1):
        pod -= at(uc+su*hole_y/2, sv*hole_x/2, -mod_h-1) * Cylinder(pilot/2, mod_h, align=(Align.CENTER,Align.CENTER,Align.MIN))

y0, y1, xw = wall + 0.5, Dback-wall-0.5, W/2-wall-0.5
cutter = Pos(0, (y0+y1)/2, -4.75) * Box(2*xw, y1-y0, 10.5)
cutter = cutter - pod                       # never removes pod material, any order

print("pod valid:", pod.is_valid, " cutter valid:", cutter.is_valid)
bb = pod.bounding_box()
print("pod size mm  X %.1f  Y %.1f  Z %.1f   (in: %.3f x %.3f x %.3f)" % (bb.size.X, bb.size.Y, bb.size.Z, bb.size.X/25.4, bb.size.Y/25.4, bb.size.Z/25.4))
print("lowest pod point above base mm: %.2f" % pod.bounding_box().min.Z)
print("Dback mm %.2f in %.3f" % (Dback, Dback/25.4))
export_step(pod, "lcd_pod_30.step"); export_step(cutter, "lcd_pod_cutter.step")
export_stl(pod, "lcd_pod_30.stl"); export_stl(cutter, "lcd_pod_cutter.stl")
print("exported")

# ---- placed copies in the user's Inventor part frame ----
# Inventor part: Y = up (plate top face at +0.125 in), width along Z (plate Z -9.35..0),
# top edge (power/key) at X = -6.20 in, buttons toward X = 0.
# pod X(width) -> -Z, pod Y(toward top edge) -> -X, pod Z(up) -> +Y
IN = 25.4
plate_top_y = 0.125*IN   # final plate thickness
top_edge_x  = -6.200*IN
center_z    = -4.675*IN
back_gap    = 0.150*IN
place = Plane(origin=(top_edge_x + back_gap + Dback, plate_top_y, center_z),
              x_dir=(0,0,-1), z_dir=(0,1,0))
pod_p, cut_p = place*pod, place*cutter
export_step(pod_p, "lcd_pod_30_placed.step"); export_step(cut_p, "lcd_pod_cutter_placed.step")
export_stl(pod_p, "lcd_pod_30_placed.stl");   export_stl(cut_p, "lcd_pod_cutter_placed.stl")
bb = pod_p.bounding_box()
print("placed pod in:  X %.3f..%.3f  Y %.3f..%.3f  Z %.3f..%.3f" % (bb.min.X/IN, bb.max.X/IN, bb.min.Y/IN, bb.max.Y/IN, bb.min.Z/IN, bb.max.Z/IN))
