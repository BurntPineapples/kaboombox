# Copyright (c) 2026 Burnt pineapples
# SPDX-License-Identifier: MIT

# Shrink the plate without moving any button/LED/key/power/pod feature.
#  width (Inventor Z): slide each END (corner chamfers, corner holes, end face) inward.
#  depth (Inventor X): slide the BUTTON edge (X=0 face, its 2 chamfers, its 2 corner holes) toward -X.
#   python shrink_plate.py [new_width_in] [new_depth_in]      (default 9.200 6.100)
#
# Needs numpy. Works straight on the STL triangles, so it only suits small changes:
# the asserts below stop it before an end runs into the power switch or MODE button hole.
# Writes Controller_<width>x<depth>.stl next to SRC. If you don't have my Inventor
# folder, point SRC at inventor/Controller.stl in this repo.
import sys, struct, numpy as np

SRC = r"E:\InventorProjects\Fireworkcontroller\Controller.stl"
OLD_W, OLD_D = 9.300, 6.200
NEW_W = float(sys.argv[1]) if len(sys.argv) > 1 else 9.200
NEW_D = float(sys.argv[2]) if len(sys.argv) > 2 else 6.100
d = (OLD_W - NEW_W) / 2 * 25.4            # mm each end moves in
e = (OLD_D - NEW_D) * 25.4                # mm the button edge moves in
assert 0 <= d < 0.15 * 25.4, "more than 0.15in per end hits the power-switch hole"
assert 0 <= e < 0.25 * 25.4, "more than 0.25in crowds the mode button (hole edge at X=-0.405)"

raw = open(SRC, "rb").read()
n = struct.unpack("<I", raw[80:84])[0]
dt = np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")])
tri = np.frombuffer(raw[84:84 + 50 * n], dtype=dt).copy()
v = tri["v"].reshape(-1, 3, 3)
x, z = v[..., 0] / 25.4, v[..., 2] / 25.4

before = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
# Z=0 end: everything past the corner chamfers (nearest other feature is the power hole at -0.678)
v[..., 2] -= np.where(z > -0.53, d, 0)
# far end: corner regions + end face, but NOT the key hole whose edge reaches Z=-8.786 at X=-4.74
far = (z < -8.775) & ~((x > -5.5) & (x < -1.0))
v[..., 2] += np.where(far, d, 0)
# button edge: face + chamfers + corner holes, but NOT the mode button (Z -4.67, edge at X=-0.405)
v[..., 0] -= np.where((x > -0.53) & ~((z < -4.2) & (z > -5.15)), e, 0)
after = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
assert (np.einsum("ij,ij->i", before, after) > 0).all(), "a triangle flipped"

tri["v"] = v.reshape(-1, 9)
out = SRC.replace(".stl", f"_{NEW_W:.3f}x{NEW_D:.3f}.stl")
open(out, "wb").write(raw[:84] + tri.tobytes())
x, z = v[..., 0] / 25.4, v[..., 2] / 25.4
print(f"{out}\n  width {z.max() - z.min():.3f} in (Z {z.max():.3f} .. {z.min():.3f})"
      f"  depth {x.max() - x.min():.3f} in (X {x.max():.3f} .. {x.min():.3f})")
