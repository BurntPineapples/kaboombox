# Copyright (c) 2026 Burnt pineapples
# SPDX-License-Identifier: MIT

# Flat 1.5 mm test copy of the controller plate (outline + every hole + LCD opening),
# made by slicing the real plate STL just above its bottom face. Print it flat, check fit in the box.
import struct, shutil, numpy as np
from build123d import *

SRC = r"E:\InventorProjects\Fireworkcontroller\Controller_9.200x6.100.stl"
raw = open(SRC, "rb").read(); n = struct.unpack("<I", raw[80:84])[0]
v = np.frombuffer(raw[84:84 + 50 * n], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))["v"].reshape(-1, 3, 3)

segs = []                                   # section at Y = 0.3 mm (inside the plate)
for t in v.astype(float):
    d = t[:, 1] - 0.3
    p = [t[a] + d[a] / (d[a] - d[b]) * (t[b] - t[a]) for a, b in ((0, 1), (1, 2), (2, 0)) if d[a] * d[b] < 0]
    if len(p) == 2:
        segs.append([tuple(np.round((q[0], -q[2]), 4)) for q in p])     # sketch (X, -Z)
nxt = {}
for a, b in segs:
    nxt.setdefault(a, []).append(b); nxt.setdefault(b, []).append(a)
loops, seen = [], set()
for start in nxt:
    if start in seen: continue
    loop, prev, cur = [start], None, start
    while True:
        seen.add(cur)
        cand = [q for q in nxt[cur] if q != prev]
        if not cand or cand[0] == start: break
        prev, cur = cur, cand[0]; loop.append(cur)
    if len(loop) > 2: loops.append(Polygon(*loop, align=None))
loops.sort(key=lambda f: -f.area)
sk = loops[0]
for h in loops[1:]: sk -= h
test = extrude(sk, 1.5)
print(f"{len(loops) - 1} holes, outline {test.bounding_box().size.X / 25.4:.3f} x {test.bounding_box().size.Y / 25.4:.3f} in")
export_stl(test, "controller_plate_test.stl"); shutil.copy("controller_plate_test.stl", r"E:\InventorProjects\Fireworkcontroller")

# ---- full print: same outline/holes at 0.125", M2 corner holes, LCD pod re-joined on top ----
IN = 25.4
LEGS = [(-5.775, 8.907), (-5.767, 0.478), (-0.530, 0.478), (-0.530, 8.848)]   # corner holes (X, -Z) in, = legs_step.py
full = loops[0]
for h in loops[1:]:
    c = h.center()
    corner = min(abs(c.X / IN - u) + abs(c.Y / IN - w) for u, w in LEGS) < 0.1
    full -= Pos(c.X, c.Y) * Circle(1.2) if corner else h                     # M2 clearance 2.4 mm
full = extrude(Plane(origin=(0, 0, 0), x_dir=(1, 0, 0), z_dir=(0, 1, 0)) * full, 0.125 * IN, dir=(0, 1, 0))   # sketch v -> -Z, up = Y
for u, w in LEGS:   # counterbore: head sits 2 mm down so an M2x6 still bites 4.8 mm into the leg
    full -= Pos(u * IN, 1.2 + 1.5, -w * IN) * Rot(90, 0, 0) * Cylinder(2.1, 3)
full -= import_step("lcd_pod_cutter_placed.step")
full += import_step("lcd_pod_30_placed.step")
assert len(full.solids()) == 1
export_step(full, "controller_full.step"); export_stl(Rot(90, 0, 0) * full, "controller_full.stl")   # print: plate bottom on the bed
for f in ("controller_full.step", "controller_full.stl"): shutil.copy(f, r"E:\InventorProjects\Fireworkcontroller")
bb = full.bounding_box()
print(f"full plate {bb.size.Z / IN:.3f} x {bb.size.X / IN:.3f} in, {bb.size.Y / IN:.3f} tall, {full.volume / 1000:.0f} cm3")
