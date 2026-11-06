# Firework Controller — ESP32 firmware

Two Arduino sketches, one per box:

| Sketch | Flash to | Job |
|---|---|---|
| `firework_controller/` | **Panel box** ESP32 (buttons, key switch, LEDs, 7-seg display) | Reads key + buttons, countdown + fire commands, link monitoring |
| `firework_field/` | **Fuse/igniter box** ESP32 (relay module, 12V battery) | Drives relays, reads igniter continuity, obeys only a paired, armed controller |

Board setting for both: **ESP32 Dev Module**, Serial Monitor **115200**.
MACs are already paired in both sketches (controller EC:E3:34:19:B1:F0 ↔ field 44:1D:64:BD:75:50).

## Controller pin map (all 24 usable GPIOs allocated)
| Thing | GPIO |
|---|---|
| Fire buttons 1–8 | 13, 14, 25, 26, 34*, 35*, 36*, 39* (*external 10k pullup to 3V3) |
| Button LEDs 1–8 | 4, 19, 21, 22, 23, 27, 32, 33 (via 220Ω) |
| Key ARMED / ARMED ALL | 17 / 18 (key common → 3V3) |
| DISARMED / LINK-green / LINK-red | 15 / 2 / 12 (via 220Ω) |
| 74HC595 data / clock / latch | 0 / 5 / 16 → drives 5161AS 7-seg (segments via 220Ω, common cathodes pins 3+8 → GND) |

There is **no TEST button anymore** — link tests run at boot, every 5s, and on every button press. The LINK window is a persistent indicator: solid green = healthy, solid red = down.

## Fire sequence
Valid press (armed + link + continuity + not fired) → **3-2-1 countdown on the 7-seg display** → fire (500ms relay pulse).
Countdown aborts instantly if the key position changes (DISARMED = abort switch), the link drops, or continuity is lost. Denied presses show **E** on the display with the reason on Serial.

## Display legend
`0–8` = channels ready · `3/2/1` = countdown · `E` = press denied · `-` = no link

## Field unit safety
- Ignores all packets not from the paired controller MAC
- Auto-disarms after 1.5s without an ARMED heartbeat; relays forced off at boot
- Physical master safety: no fuse in the 12V holder = firing circuit dead
