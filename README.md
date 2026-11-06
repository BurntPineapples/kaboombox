# ESP32 Wireless Firework Controller

A two-box remote firing system for small firework and effects shows. A handheld panel with
8 fire buttons and an arming key talks over ESP-NOW to a field box with an 8-channel
relay board and a 12 V battery. The field box checks each igniter for continuity and
reports back, so you can see on the panel which channels are ready before you arm.

> [!CAUTION]
> **This fires pyrotechnics. It can hurt or kill people.** It's a hobby project, not a
> certified product, and it comes with no warranty of any kind. Read
> [DISCLAIMER.md](DISCLAIMER.md) before you build or use anything here. You are
> responsible for following the laws where you live. Never bypass the fuse, the arming
> key or the heartbeat auto-disarm.

## How it works

```
  PANEL BOX (handheld)                          FIELD BOX (on the ground)
 ┌──────────────────────┐    ESP-NOW 2.4 GHz    ┌───────────────────────────┐
 │ ESP32                │ ── heartbeat/fire ──► │ ESP32                     │
 │ 8 fire buttons + LEDs│ ◄── status/contin. ── │ 8-ch relay board          │
 │ arming key, MODE btn │                       │ continuity sense per ch.  │
 │ 16x2 LCD, link LEDs  │                       │ 12 V SLA ─ fuse ─ relays  │
 │ 4x AA                │                       │          └─► igniters     │
 └──────────────────────┘                       └───────────────────────────┘
```

- The panel sends a heartbeat every 300 ms with the key position. The field box only
  fires while it's hearing a fresh ARMED heartbeat. If the heartbeat is more than 1.5 s
  old it cuts any pulse in progress and refuses new fire commands.
- The field box sends status 4 times a second: continuity for each channel, which relays
  are closed, and its uptime. The panel uses that to light the channel LEDs and to work
  out link quality.
- The two boards are paired by MAC address and only listen to each other.

### Key switch

| Position | What happens |
|---|---|
| Middle: **DISARMED** | Every relay open. MODE opens the settings menu. |
| Left: **ARMED** | Each button fires its own channel (SINGLE), or any button runs your saved sequence (PROGRAM). |
| Right: **ARMED ALL** | Any button starts a 3-2-1 countdown, then fires every ready channel. Turning the key aborts it. |

After power-up the key has to be seen in DISARMED once before it will arm, so the box
can't come up armed if you switch it on with the key in the wrong spot.

### Channel types

Each channel can be set in the menu (saved in flash):

- **FIRE**: pulses the relay for the channel's pulse length (0.1 to 10 s). For igniters.
- **ON/OFF**: press on, press off. For lights or inflatables.
- **HOLD**: relay on only while you hold the button. For fog or similar.

### Menu (key in DISARMED, press MODE)

btn1 = next, btn2 = back, btn3 = minus, btn4 = plus/start, MODE = back, hold MODE = exit.

1 Link status · 2 Ping test · 3 System check · 4 Continuity · 5 Channel setup ·
6 Link-lost hold · 7 Input test · 8 Info · 9 Reset settings

## What's in here

```
firmware/
  firework_controller/   panel box sketch
  firework_field/        field box sketch
hardware/
  pcb/                   KiCad 10 boards, generator + router scripts, gerber zips
    archive/             old two-board (tray + lid) controller design, not used anymore
  enclosure/             build123d scripts, STEP/STL files, print/fit test pieces
    inventor/            Autodesk Inventor parts (.ipt/.ipj) and the plate STLs
    archive/             earlier OpenSCAD versions
docs/                    wiring sheets and schematics (open the .html files in a browser)
  archive/               outdated sheets from the 7-segment version, don't build from these
```

## Parts list

Roughly what one complete set needs. Check the wiring sheets in `docs/` for details.

| Qty | Part | Notes |
|---|---|---|
| 2 | ESP32 38-pin dev board (NodeMCU ESP-32S or similar) | Measure the pin-row spacing before ordering PCBs (see below) |
| 1 | ELEGOO 8-channel 5 V relay module | Active-LOW inputs |
| 1 | 16x2 LCD with I2C backpack (PCF8574) | Address 0x27 or 0x3F |
| 8 | Momentary push buttons | Fire buttons |
| 1 | Momentary push button | MODE |
| 1 | 3-position key switch | Middle = off, left/right = on |
| 10 | LEDs | 8 channel + 1 green + 1 red link LED |
| 10 | 220 Ω resistor | LED current limit |
| 4 | 10 kΩ resistor | Pull-ups for buttons 5-8 (GPIO 34-39 have no internal pull-up) |
| 4 | 100 kΩ resistor | Field box sense pull-ups, channels 1-4 |
| 8 | 10 kΩ resistor | Field box sense series resistors |
| 1 | 12 V SLA battery | Firing power |
| 1 | Inline fuse holder + 10 A fuse | **The master safety. No fuse, no firing power.** |
| 1 | 4x AA holder + toggle switch | Panel power (NiMH is easier on the LCD than fresh alkalines) |
| 16 | Alligator clips | 2 per channel |
| - | Screw terminals, female headers, wire, Wago connectors | See the PCB section |
| 2 | PCBs (optional) | Controller 100 x 84 mm, field 100 x 75 mm |

## Flashing the firmware

1. Install the [Arduino IDE](https://www.arduino.cc/en/software).
2. Add the ESP32 boards: **File → Preferences → Additional boards manager URLs**:
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json`
   then **Tools → Board → Boards Manager**, search "esp32" and install **esp32 by
   Espressif Systems**. The sketches handle both the 2.x and 3.x cores.
3. **Sketch → Include Library → Manage Libraries**, install **LiquidCrystal I2C** by
   Frank de Brabander (panel box only).
4. Board: **ESP32 Dev Module**. Open `firmware/firework_controller/firework_controller.ino`,
   upload it to the panel ESP32. Open `firmware/firework_field/firework_field.ino` and
   upload it to the field ESP32.

### Pairing the two boards

The MAC addresses in the sketches are for my boards. Yours will be different.

1. Flash both sketches as they are and open **Serial Monitor at 115200 baud**.
2. Each board prints its own MAC at boot (`MY MAC - paste into ...`).
3. Put the **field** board's MAC into `FIELD_MAC` in `firework_controller.ino`.
4. Put the **controller** board's MAC into `CONTROLLER_MAC` in `firework_field.ino`.
5. Re-flash both. The green link LED should come on.

`44:1D:64:BD:75:50` becomes `{0x44, 0x1D, 0x64, 0xBD, 0x75, 0x50}`.

### Settings you might change

| Setting | File | Default | What it does |
|---|---|---|---|
| `FIELD_MAC` | firework_controller.ino | my board | MAC of your field box |
| `CONTROLLER_MAC` | firework_field.ino | my board | MAC of your panel box |
| `LCD_ADDR` | firework_controller.ino | `0x27` | Try `0x3F` if the screen stays blank (and turn the contrast pot) |
| `USE_LONG_RANGE` | **both** | `0` | `1` turns on ESP32 long-range mode. Must match on both boards |
| `MAX_PULSE_MS` | firework_field.ino | `10000` | Hard cap on any one pulse, whatever the panel asks for |
| `HEARTBEAT_TIMEOUT` | firework_field.ino | `1500` | Field disarms after this many ms without a heartbeat. Don't raise it |

Everything else (channel types, pulse lengths, continuity check, link-lost hold, the
saved sequence) is set from the menu on the panel and stored in flash.

If you change the message format, bump `PROTO_VER` in both sketches. Boards with a
different `PROTO_VER` ignore each other instead of misfiring.

## Pin maps

### Panel box (`firework_controller.ino`)

| Function | GPIO |
|---|---|
| Fire buttons 1-8 (to GND) | 13, 14, 25, 26, 34, 35, 36, 39 (34-39 need an external 10 k pull-up to 3V3) |
| Channel LEDs 1-8 (220 Ω to GND) | 4, 19, 21, 22, 23, 18, 32, 33 |
| Key ARMED / ARMED ALL (key common to 3V3) | 17 / 27 |
| MODE button (to GND) | 15 |
| Link LED green / red | 2 / 12 |
| LCD SDA / SCL (LCD VCC to 5 V) | 16 / 5 |

### Field box (`firework_field.ino`)

| Channel | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| Relay IN (active LOW) | 26 | 27 | 14 | 13 | 25 | 33 | 32 | 16 |
| Continuity sense | 36 | 39 | 34 | 35 | 4 | 17 | 18 | 19 |

Each sense pin connects through a 10 k series resistor to that relay's NO terminal
(where the igniter's hot lead lands). Channels 1-4 need a 100 k pull-up to 3V3; 5-8 use
the ESP32's internal pull-up. An igniter in place pulls the pin LOW.

## PCBs

Both boards are generated by Python scripts that run inside KiCad's own Python, then
auto-routed with [freerouting](https://github.com/freerouting/freerouting).

| Board | Size | Files |
|---|---|---|
| Panel (controller) | 100 x 84 mm | `hardware/pcb/controller/` · `controller-gerbers.zip` |
| Field | 100 x 75 mm | `hardware/pcb/field/` · `field-gerbers.zip` |

**Ordering:** upload the gerber zip at [jlcpcb.com](https://jlcpcb.com) (or any other
fab). The defaults are fine: 2 layers, 1.6 mm, HASL.

**Before you order, measure your ESP32.** The boards assume the two pin rows are
25.4 mm (1.0") apart. Some dev boards are 22.86 mm (0.9"). If yours is different,
change `ESP_ROW_SPACING` at the top of the generator script and rebuild. Print
`field/field-paper-check-1to1.pdf` at 100% scale and set your parts on it to check
the fit.

**Rebuilding** (needs [KiCad 10](https://www.kicad.org/), Java and freerouting):

```
cd hardware/pcb
"C:\Program Files\KiCad\10.0\bin\python.exe" generate_controller.py
"C:\Program Files\KiCad\10.0\bin\python.exe" route_controller.py path\to\freerouting.jar
```

The scripts point to my KiCad install at `E:\KiCad`. Change `FP_ROOT` at the top of each
generator to your KiCad footprint folder. Running a generator **wipes the routing** on
that board, so always run the router after it. Then export gerbers from KiCad
(File → Fabrication Outputs) and zip them.

## Enclosure

The panel is a printed 9.2 x 6.1 in plate with an angled LCD pod, legs and an internal
parts tray, made to drop into a box with a 9-3/8 x 6-1/4 in opening. The field parts are a floor plate and a front window
frame for an ammo can.

Ready-to-print files are in `hardware/enclosure/`:

| File | Part |
|---|---|
| `controller_full.stl` | Panel plate with the LCD pod |
| `legs_print.stl` | Panel legs + floor ring (one piece) |
| `tray_print.stl` | Parts tray that sits on the legs |
| `field_floor.stl` | Field box floor plate (print skirt-up, no supports) |
| `field_prop.stl` | Field box front window frame |
| `*_test.stl` | Thin fit-test versions. Print these first, they take minutes |

The `.step` files are the same parts for CAD. PETG or ASA hold up better outdoors than
PLA, which can soften in a hot car or in direct sun.

To regenerate them you need Python 3 and build123d:

```
pip install build123d
cd hardware/enclosure
python legs_step.py
```

A few scripts copy their output into my Inventor folder (`E:\InventorProjects\...`)
or read the plate STL from there. If you don't have that folder, delete those
`shutil.copy` lines and point `SRC` at `inventor/Controller_9.200x6.100.stl`.

The base plate was modelled in Autodesk Inventor. The `.ipt` files are in
`hardware/enclosure/inventor/` if you have Inventor; everyone else can use the STEP/STL files.

## Docs

Open these in a browser:

- [`docs/CONTROLLER_WIRING.html`](docs/CONTROLLER_WIRING.html): panel box wiring, step by step
- [`docs/FIELD_WIRING_GUIDE.html`](docs/FIELD_WIRING_GUIDE.html): field box power and clip wiring
- [`docs/SCHEMATIC_field.html`](docs/SCHEMATIC_field.html): field box schematic
- [`hardware/enclosure/INVENTOR_BUILD.html`](hardware/enclosure/INVENTOR_BUILD.html): faceplate build sheet

Anything in `docs/archive/` is from the old 7-segment version and has wrong pins.

## Before every use

- Test with **no pyrotechnics connected**. Put an LED or test lamp across each channel's
  clips and fire every channel.
- Run **System check** from the menu. It should say PASS.
- Turn the key to DISARMED and **pull the fuse** before you walk up to the field box.
  Connect igniters last, fuse in last, and walk away before you arm.
- If something doesn't fire, disarm, pull the fuse, and wait before you approach.

## License

- Firmware and scripts: [MIT](LICENSE)
- Hardware designs (PCB, enclosure, Inventor files) and docs:
  [CERN-OHL-P v2](LICENSE-HARDWARE)

Both come with no warranty. See [DISCLAIMER.md](DISCLAIMER.md) as well. By using
anything in this repo you accept that you do so entirely at your own risk.
