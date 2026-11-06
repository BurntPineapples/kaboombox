// Copyright (c) 2026 Burnt pineapples
// SPDX-License-Identifier: MIT
// Provided as-is with no warranty. Read DISCLAIMER.md before building or using this.

/*
 * ============================================================
 *  FIREWORK / SHOW FIELD UNIT  —  flash this to the RELAY box
 *  (the ESP32 wired to the 8-channel relay module)
 * ============================================================
 *  Board setting in Arduino IDE: "ESP32 Dev Module"
 *
 *  v2: flash the CONTROLLER with its v2 sketch too. v1 and v2 boxes
 *  ignore each other (no link, nothing fires) - they never misfire.
 *
 *  FIRST-TIME PAIRING:
 *   1. Flash both sketches. Open Serial Monitor at 115200 baud.
 *   2. Each board prints its own MAC address at boot.
 *   3. Paste the CONTROLLER's MAC into CONTROLLER_MAC below, re-flash.
 *   4. Paste THIS board's MAC into FIELD_MAC in the controller sketch.
 *
 *  WHAT THE CONTROLLER SENDS:
 *   - FIRE: pulse a relay for that channel's pulse length (set in the
 *     controller menu, capped here at MAX_PULSE_MS).
 *   - HEARTBEAT (every 300 ms): key mode + which ON/OFF and HOLD
 *     channels should be on right now. Relays follow it.
 *
 *  SAFETY DESIGN:
 *   - Packets from any other MAC, or other firmware version, are ignored.
 *   - Firing requires a fresh heartbeat (<1.5s) saying ARMED / ARMED ALL.
 *   - Key to DISARMED -> every relay opens.
 *   - Link lost -> pulses cut at once, HOLD channels off at once, fire
 *     requests refused. ON/OFF channels stay on for the controller's
 *     "Link-lost hold" setting (default: off at once), then open.
 *     When the link returns, relays follow the controller again.
 *   - Relay outputs are driven OFF as the very first thing in setup().
 *   - The real safety is physical: no fuse in the 12V holder = the
 *     firing circuit is dead no matter what this code does.
 *
 *  CONTINUITY SENSE (per channel):
 *   pullup --+-- sense pin
 *            +-- [10k series] -- relay NO terminal (igniter + line)
 *   Channels 1-4 (pins 36/39/34/35): external 100k pullup to 3V3 required.
 *   Channels 5-8 (pins 4/17/18/19): internal pullup, no resistor needed.
 *   Igniter present pulls the pin LOW. The 10k series resistor protects
 *   the pin from the 12V that appears on the line while the relay fires.
 */

#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>

#define USE_LONG_RANGE 0   // 1 = ESP32 long-range radio (more range, lower speed). Set the SAME in the controller sketch.

// ====== PASTE THE CONTROLLER'S MAC ADDRESS HERE ======
uint8_t CONTROLLER_MAC[6] = {0xEC, 0xE3, 0x34, 0x19, 0xB1, 0xF0};

// ---------- pin map (matches the wiring diagram) ----------
const int RELAY_PIN[8] = {26, 27, 14, 13, 25, 33, 32, 16}; // ELEGOO IN1-IN8, active LOW
const int SENSE_PIN[8] = {36, 39, 34, 35, 4, 17, 18, 19};  // LOW = igniter connected

// ---------- protocol (must match controller sketch) ----------
#define PROTO_VER    0xA2   // first byte of every packet; not 1-5 so a v1 box can't mistake it for a message type
#define NO_HEARTBEAT 0xFF   // STATUS.mode when we aren't hearing the controller
#define HOLD_FOREVER 0xFFFF
enum Mode : uint8_t { MODE_DISARMED = 0, MODE_ARMED = 1, MODE_ARMED_ALL = 2 };
#define MSG_HEARTBEAT 1
#define MSG_FIRE      2
#define MSG_PING      3
#define MSG_PONG      4
#define MSG_STATUS    5

typedef struct __attribute__((packed)) {
  uint8_t  ver;
  uint8_t  type;
  uint8_t  mode;       // controller: key mode | field STATUS: mode it hears, NO_HEARTBEAT if none
  uint8_t  mask;       // FIRE: channels to pulse | HEARTBEAT: ON/OFF channels on | STATUS: continuity
  uint8_t  mask2;      // HEARTBEAT: HOLD channels on | STATUS: fired channels
  uint8_t  mask3;      // STATUS: relays closed right now
  uint16_t holdS;      // HEARTBEAT: link-lost hold for ON/OFF channels (HOLD_FOREVER = until link back)
  uint32_t uptimeS;    // STATUS: field uptime
  uint16_t pulseMs[8]; // FIRE: pulse length per channel
} Msg;

#define MAX_PULSE_MS      10000 // hard cap on any one pulse, whatever the controller asks
#define MIN_PULSE_MS      50
#define HEARTBEAT_TIMEOUT 1500
#define STATUS_MS         250   // controller measures link quality from these

// ---------- state ----------
volatile uint8_t  ctrlMode = MODE_DISARMED;
volatile uint32_t lastHeartbeatMs = 0;
volatile uint8_t  fireRequestMask = 0;
volatile uint16_t fireReqMs[8];
volatile uint8_t  toggleMask = 0;    // ON/OFF channels the controller wants on
volatile uint8_t  holdMask = 0;      // HOLD channels the controller wants on
volatile uint16_t linkHoldS = 0;
volatile bool     pongRequested = false;

uint8_t  firedMask = 0;
uint8_t  lastContinuity = 0xFF; // impossible value forces first print
uint8_t  lastRelays = 0;
uint32_t pulseStart[8] = {0};
uint16_t pulseLen[8] = {0};     // 0 = no pulse running
uint32_t lastStatusSent = 0;
bool     linkWasUp = false;

void reply(uint8_t type, uint8_t mode, uint8_t cont, uint8_t relays) {
  Msg m = {};
  m.ver = PROTO_VER;
  m.type = type;
  m.mode = mode;
  m.mask = cont;
  m.mask2 = firedMask;
  m.mask3 = relays;
  m.uptimeS = millis() / 1000;
  esp_now_send(CONTROLLER_MAC, (uint8_t *)&m, sizeof(m));
}

void handleRecv(const uint8_t *mac, const uint8_t *data, int len) {
  if (memcmp(mac, CONTROLLER_MAC, 6) != 0) return;            // strangers ignored
  if (len != (int)sizeof(Msg) || data[0] != PROTO_VER) return; // other firmware ignored
  Msg m;
  memcpy(&m, data, sizeof(m));

  // every controller message doubles as a heartbeat
  ctrlMode = m.mode;
  lastHeartbeatMs = millis();

  if (m.type == MSG_HEARTBEAT) {
    toggleMask = m.mask;
    holdMask = m.mask2;
    linkHoldS = m.holdS;
  } else if (m.type == MSG_PING) {
    pongRequested = true;             // answered from loop()
  } else if (m.type == MSG_FIRE) {
    for (int i = 0; i < 8; i++) if (bitRead(m.mask, i)) fireReqMs[i] = m.pulseMs[i];
    fireRequestMask |= m.mask;        // executed from loop()
  }
}

#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
void onRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  handleRecv(info->src_addr, data, len);
}
#else
void onRecv(const uint8_t *mac, const uint8_t *data, int len) {
  handleRecv(mac, data, len);
}
#endif

uint8_t readContinuity() {
  uint8_t mask = 0;
  for (int i = 0; i < 8; i++) {
    if (digitalRead(SENSE_PIN[i]) == LOW) bitSet(mask, i);
  }
  return mask;
}

void setup() {
  // relays OFF before anything else can happen
  for (int i = 0; i < 8; i++) {
    pinMode(RELAY_PIN[i], OUTPUT);
    digitalWrite(RELAY_PIN[i], HIGH);
  }
  // sense channels 1-4 (pins 36/39/34/35): input-only pins, external 100k pullup required
  for (int i = 0; i < 4; i++) pinMode(SENSE_PIN[i], INPUT);
  // sense channels 5-8 (pins 4/17/18/19): use the chip's internal pullup, no resistor needed
  for (int i = 4; i < 8; i++) pinMode(SENSE_PIN[i], INPUT_PULLUP);

  Serial.begin(115200);

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
#if USE_LONG_RANGE
  esp_wifi_set_protocol(WIFI_IF_STA, WIFI_PROTOCOL_LR);
#endif
  Serial.println();
  Serial.println("=== FIELD UNIT v2 (relay box) ===");
  Serial.print("MY MAC - paste into FIELD_MAC in the controller sketch: ");
  Serial.println(WiFi.macAddress());

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init FAILED - halting");
    while (true) delay(1000);
  }
  esp_now_register_recv_cb(onRecv);

  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, CONTROLLER_MAC, 6);
  peer.channel = 0;
  peer.encrypt = false;
  esp_now_add_peer(&peer);

  Serial.println("Ready. Relays inhibited until ARMED heartbeat arrives.");
}

void loop() {
  uint32_t now = millis();

  bool fresh = lastHeartbeatMs != 0 && (now - lastHeartbeatMs) < HEARTBEAT_TIMEOUT;
  bool keyOn = ctrlMode == MODE_ARMED || ctrlMode == MODE_ARMED_ALL;
  bool armed = fresh && keyOn;

  if (fresh != linkWasUp) {
    linkWasUp = fresh;
    if (fresh)                          Serial.println("LINK: controller heard");
    else if (linkHoldS == HOLD_FOREVER) Serial.println("LINK LOST - pulses cut, fire refused, ON/OFF held until link returns");
    else Serial.printf("LINK LOST - pulses cut, fire refused, ON/OFF held %us\n", (unsigned)linkHoldS);
  }

  // execute fire requests (only while armed with a fresh heartbeat)
  if (fireRequestMask) {
    uint8_t req = fireRequestMask;
    fireRequestMask = 0;
    if (armed) {
      for (int i = 0; i < 8; i++) {
        if (bitRead(req, i)) {
          pulseStart[i] = now;
          pulseLen[i] = constrain((int)fireReqMs[i], MIN_PULSE_MS, MAX_PULSE_MS);
          Serial.printf(">>> FIRING channel %d for %u ms\n", i + 1, pulseLen[i]);
        }
      }
    } else {
      Serial.println("Fire request REFUSED (disarmed or stale heartbeat)");
    }
  }

  // end pulses that have run their time
  for (int i = 0; i < 8; i++) {
    if (pulseLen[i] && now - pulseStart[i] >= pulseLen[i]) {
      pulseLen[i] = 0;
      bitSet(firedMask, i);
      Serial.printf("Channel %d pulse complete\n", i + 1);
    }
  }

  // hard safety: any disarm/link-loss kills pulses in progress
  if (!armed) {
    for (int i = 0; i < 8; i++) {
      if (pulseLen[i]) {
        Serial.printf("SAFETY: aborting pulse on channel %d\n", i + 1);
        pulseLen[i] = 0;
      }
    }
  }

  // ON/OFF + HOLD channels follow the heartbeat. On link loss, ON/OFF ones
  // ride through for the controller's hold setting; HOLD ones drop at once.
  uint8_t relays = 0;
  if (armed) relays = toggleMask | holdMask;
  else if (!fresh && keyOn && lastHeartbeatMs != 0 &&
           (linkHoldS == HOLD_FOREVER || now - lastHeartbeatMs < HEARTBEAT_TIMEOUT + linkHoldS * 1000UL))
    relays = toggleMask;
  for (int i = 0; i < 8; i++) {
    if (pulseLen[i]) bitSet(relays, i);
    digitalWrite(RELAY_PIN[i], bitRead(relays, i) ? LOW : HIGH); // active LOW
  }
  if (relays != lastRelays) {
    lastRelays = relays;
    Serial.print("Relays [ch 8..1]: ");
    for (int i = 7; i >= 0; i--) Serial.print(bitRead(relays, i));
    Serial.println();
  }

  // key turned to DISARMED clears the fired list: any channel still
  // showing continuity becomes launchable again after re-arming
  if (fresh && ctrlMode == MODE_DISARMED && firedMask != 0) {
    firedMask = 0;
    Serial.println("DISARMED: fired list cleared - channels with continuity are ready again");
  }

  uint8_t heard = fresh ? ctrlMode : NO_HEARTBEAT;

  // answer link-test pings
  if (pongRequested) {
    pongRequested = false;
    reply(MSG_PONG, heard, lastContinuity, relays);
  }

  // status broadcast: continuity + fired + relays
  if (now - lastStatusSent >= STATUS_MS) {
    lastStatusSent = now;
    uint8_t cont = readContinuity();
    if (cont != lastContinuity) {
      lastContinuity = cont;
      Serial.print("Continuity [ch 8..1]: ");
      for (int i = 7; i >= 0; i--) Serial.print(bitRead(cont, i));
      Serial.println();
    }
    reply(MSG_STATUS, heard, cont, relays);
  }

  delay(5);
}
