# Copyright (c) 2026 Burnt pineapples
# SPDX-License-Identifier: MIT

"""Auto-routes the controller board with freerouting.
Exports a DSN, runs freerouting on it, then pulls the routes (SES) back
into controller/controller.kicad_pcb and saves it.

Needs Java and the freerouting .jar (github.com/freerouting/freerouting):
  "E:\\KiCad\\bin\\python.exe" route_controller.py <freerouting.jar>

To route a different board, change `name` below (the folder and file name
must match, like field/field.kicad_pcb). "-mp 20" caps freerouting at 20
routing passes; raise it if boards come back with unrouted nets.
Check the result with KiCad's DRC before ordering.
"""
import os, subprocess, sys
import pcbnew

ROOT = os.path.dirname(os.path.abspath(__file__))
JAR = sys.argv[1]
name = "controller"
pcb = os.path.join(ROOT, name, name + ".kicad_pcb")
dsn = os.path.join(ROOT, name, name + ".dsn")
ses = os.path.join(ROOT, name, name + ".ses")

board = pcbnew.LoadBoard(pcb)
if not pcbnew.ExportSpecctraDSN(board, dsn):
    raise RuntimeError("DSN export failed")
print("DSN exported")

r = subprocess.run(["java", "-jar", JAR, "-de", dsn, "-do", ses, "-mp", "20"],
                   capture_output=True, text=True, timeout=1200)
print("freerouting rc:", r.returncode)
if not os.path.exists(ses):
    print(r.stdout[-3000:]); print(r.stderr[-3000:])
    raise RuntimeError("no SES produced")

if not pcbnew.ImportSpecctraSES(board, ses):
    raise RuntimeError("SES import failed")
pcbnew.SaveBoard(pcb, board)
print("routed and saved")
