/*
 * ============================================================
 *  FIREWORK / SHOW CONTROLLER  —  flash this to the CONTROL PANEL box
 *  (ESP32 with buttons, key switch, LEDs, 16x2 I2C LCD, mode button)
 * ============================================================
 *  Board: "ESP32 Dev Module"
 *  LIBRARY NEEDED: "LiquidCrystal I2C" by Frank de Brabander
 *
 *  v2: flash the FIELD box with its v2 sketch too. v1 and v2 boxes
 *  ignore each other (no link, nothing fires) - they never misfire.
 *
 *  16x2 I2C LCD: GND, VCC->5V, SDA->GPIO16, SCL->GPIO5.
 *  Blank screen: turn the contrast pot, or change LCD_ADDR to 0x3F.
 *
 *  KEY SWITCH: middle=DISARMED  left=ARMED (P17)  right=ARMED ALL (P27)
 *    After power-up the key must be seen in DISARMED before it will arm.
 *    Key to DISARMED turns EVERY relay off.
 *
 *  CHANNEL TYPES (per channel, set in the menu, saved in flash):
 *    FIRE   - relay pulses for the channel's pulse length (fireworks, confetti)
 *    ON/OFF - press = on, press again = off (inflatables, lights)
 *    HOLD   - relay on only while the button is held (fog, effects)
 *
 *  ARMED (left):
 *    SINGLE  = each button runs its own channel.
 *    MODE short = SINGLE / PROGRAM.
 *    MODE hold  = build PROGRAM: press buttons in order, MODE, then
 *                 btn1-4 = 0.5 / 1.0 / 1.5 / 2.0 s between steps.
 *    PROGRAM = any button runs the saved sequence (saved in flash).
 *  ARMED ALL (right): any button = 3-2-1 then every ready FIRE channel.
 *
 *  MENU (key DISARMED, press MODE):
 *    btn1 = next   btn2 = previous   btn3 = -   btn4 = + / start
 *    MODE = back   MODE hold = exit   turning the key also exits
 *    1 Link status   2 Ping test    3 System check
 *    4 Continuity    5 Channel setup (type, pulse length, need continuity)
 *    6 Link-lost hold (how long ON/OFF channels stay on if radio drops)
 *    7 Input test    8 Info         9 Reset settings
 *
 *  CHANNEL LEDs: FIRE = ready (link + continuity if required).
 *    ON/OFF + HOLD = relay on (fast blink = asked on, field not confirmed).
 *  LINK LEDs: green = OK, red = down, red blinking with green = weak signal.
 */

#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <Wire.h>
#include <Preferences.h>
#include <LiquidCrystal_I2C.h>

#define FW_VERSION     "2.0"
#define USE_LONG_RANGE 0   // 1 = ESP32 long-range radio (more range, lower speed). Set the SAME in the field sketch.

// ====== FIELD UNIT'S MAC ADDRESS ======
uint8_t FIELD_MAC[6] = {0x44, 0x1D, 0x64, 0xBD, 0x75, 0x50};

// ---------- pin map ----------
const int BTN_PIN[8] = {13, 14, 25, 26, 34, 35, 36, 39}; // fire buttons -> GND (34-39: external 10k pullup)
const int LED_PIN[8] = {4, 19, 21, 22, 23, 18, 32, 33};  // channel LEDs via 220R -> GND, HIGH = lit
const int PIN_KEY_ARMED = 17;
const int PIN_KEY_ALL    = 27;
const int PIN_MODE_BTN   = 15;
const int PIN_LED_PASS   = 2;   // LINK green
const int PIN_LED_FAIL   = 12;  // LINK red
const int PIN_LCD_SDA    = 16;  // I2C SDA
const int PIN_LCD_SCL    = 5;   // I2C SCL

#define LCD_ADDR 0x27
LiquidCrystal_I2C lcd(LCD_ADDR, 16, 2);

// ---------- protocol (must match field sketch) ----------
#define PROTO_VER    0xA2   // first byte of every packet; not 1-5 so a v1 box can't mistake it for a message type
#define NO_HEARTBEAT 0xFF   // STATUS.mode when the field isn't hearing us
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

#define HEARTBEAT_MS   300
#define LINK_TIMEOUT   1500
#define PING_MS        1000   // constant ping, for round-trip time
#define PING_TIMEOUT   600
#define STATUS_PER_2S  8      // field sends STATUS every 250 ms
#define WEAK_LINK_PCT  60
#define DEBOUNCE_MS    30
#define FIRE_FLASH_MS  900
#define COUNTDOWN_MS   3000
#define ERR_SHOW_MS    1500
#define HOLD_MS        800
#define GUESS_CD_MS    3000
#define LCD_REFRESH_MS 150
#define CHECK_MS       1500

const uint32_t DELAY_OPTS[4] = {500, 1000, 1500, 2000};
const uint16_t LINK_HOLD_OPTS[6] = {0, 10, 30, 60, 300, HOLD_FOREVER};
const char*    LINK_HOLD_NAME[6] = {"off at once", "10 sec", "30 sec", "1 min", "5 min", "til link back"};

enum ChType   : uint8_t { CT_FIRE = 0, CT_TOGGLE = 1, CT_HOLD = 2 };
const char* TYPE_NAME[3] = {"FIRE", "ON/OFF", "HOLD"};
enum SubMode  : uint8_t { SUB_SINGLE = 0, SUB_PROGRAM = 1 };
enum ProgState: uint8_t { PS_IDLE = 0, PS_BUILDING = 1, PS_DELAY = 2 };

// ---------- settings (saved in flash, survive power-off) ----------
#define CFG_MAGIC 0x5A
struct Settings {
  uint8_t magic;
  uint8_t type[8];
  uint8_t pulseDs[8];   // pulse length in tenths of a second, 1-100
  uint8_t needCont[8];  // 1 = refuse to fire without continuity
  uint8_t linkHold;     // index into LINK_HOLD_OPTS
  uint8_t seq[8];       // saved PROGRAM sequence
  uint8_t seqLen;
  uint8_t delayIdx;     // index into DELAY_OPTS
} cfg;
Preferences prefs;

// ---------- state ----------
uint8_t  mode = MODE_DISARMED;     // what the field is told: the key, forced DISARMED by menu / interlock
uint8_t  keyMode = MODE_DISARMED;  // what the key physically says
bool     keyFault = false;
bool     keyCycled = false;        // key must be seen in DISARMED before it may arm
uint8_t  subMode = SUB_SINGLE;
uint8_t  progState = PS_IDLE;
uint8_t  toggleOn = 0;             // ON/OFF channels switched on
uint8_t  holdOn = 0;               // HOLD channels whose button is down

volatile uint8_t  continuityMask = 0;
volatile uint8_t  relayMask = 0;   // relays the field says are closed
volatile uint8_t  fieldMode = NO_HEARTBEAT;
volatile uint32_t lastStatusMs = 0;
volatile uint32_t fieldUptimeS = 0;
volatile uint32_t badVerMs = 0;
volatile uint16_t statusCount = 0;
volatile int8_t   rssi = 0;        // 0 = unknown (arduino-esp32 v2 doesn't report it)
volatile bool     fieldRebooted = false;
volatile bool     pongFlag = false;
volatile uint32_t pongAtMs = 0;

uint8_t  quality = 0;              // % of field STATUS packets received, last 2 s
uint32_t qualityMs = 0;
bool     pingPending = false, lastPingOk = false;
uint32_t pingSentMs = 0, lastPingMs = 0, lastRtt = 0, pingsLost = 0;
bool     lcdFound = false;

bool     btnRaw[8]    = {false};
bool     btnStable[8] = {false};
uint32_t btnRawMs[8]  = {0};

bool     modeRaw = false, modeStable = false;
uint32_t modeRawMs = 0, modeDownMs = 0;
bool     modeHoldDone = false;

uint32_t lastHeartbeat = 0;
uint32_t flashUntil[8] = {0};
uint32_t mismatchSince = 0;
int      missingCh = -1;           // ON/OFF or HOLD channel the field won't confirm

bool     cdActive = false;
uint8_t  cdMask = 0;
uint8_t  cdStartMode = MODE_DISARMED;
uint32_t cdStartMs = 0;
int      cdShown = -1;
uint32_t noticeUntil = 0;
const char* noticeTitle = "";
const char* noticeText = "";

bool     guessActive = false;
uint32_t guessStart = 0;

bool     seqRunning = false;
uint8_t  seqIndex = 0;
uint32_t seqNextMs = 0;
int      seqCurCh = -1;

// ---------- menu ----------
enum Page : uint8_t { PG_LINK, PG_PING, PG_CHECK, PG_CONT, PG_CHAN, PG_LINKHOLD, PG_INPUT, PG_INFO, PG_RESET, PG_COUNT };
const char* PAGE_NAME[PG_COUNT] = {"Link status", "Ping test", "System check", "Continuity", "Channel setup",
                                   "Link-lost hold", "Input test", "Info", "Reset settings"};
bool     menuOpen = false, inChan = false, inInput = false, resetArmed = false;
uint8_t  page = 0, chSel = 0, chItem = 0;
int      inputLast = -1;
uint8_t  checkState = 0;           // 0 idle, 1 running, 2 done
uint32_t checkStartMs = 0;
char     checkResult[17] = "";

// ---------- settings ----------
void defaults() {
  memset(&cfg, 0, sizeof(cfg));
  cfg.magic = CFG_MAGIC;
  for (int c = 0; c < 8; c++) { cfg.type[c] = CT_FIRE; cfg.pulseDs[c] = 15; cfg.needCont[c] = 1; }
  cfg.delayIdx = 1;
}

void saveCfg() { prefs.putBytes("cfg", &cfg, sizeof(cfg)); }

void loadCfg() {
  prefs.begin("show", false);
  bool ok = prefs.getBytes("cfg", &cfg, sizeof(cfg)) == sizeof(cfg) && cfg.magic == CFG_MAGIC &&
            cfg.linkHold < 6 && cfg.delayIdx < 4 && cfg.seqLen <= 8;
  for (int c = 0; c < 8 && ok; c++)
    ok = cfg.type[c] < 3 && cfg.pulseDs[c] >= 1 && cfg.pulseDs[c] <= 100 && cfg.seq[c] < 8;
  if (!ok) { defaults(); Serial.println("SETTINGS: none saved, using defaults"); }
}

// ---------- helpers ----------
bool isLinkHealthy() {
  return lastStatusMs != 0 && (millis() - lastStatusMs) < LINK_TIMEOUT && fieldMode != NO_HEARTBEAT;
}

bool verMismatch() { return badVerMs != 0 && millis() - badVerMs < 3000; }

bool chReady(int c) { return !cfg.needCont[c] || bitRead(continuityMask, c); }

uint8_t fireAllMask() {   // FIRE channels ARMED ALL would launch
  uint8_t m = 0;
  for (int c = 0; c < 8; c++) if (cfg.type[c] == CT_FIRE && chReady(c)) bitSet(m, c);
  return m;
}

void sendMsg(uint8_t type, uint8_t mask) {
  Msg m = {};
  m.ver = PROTO_VER;
  m.type = type;
  m.mode = mode;
  m.mask = mask;
  if (type == MSG_HEARTBEAT) { m.mask = toggleOn; m.mask2 = holdOn; m.holdS = LINK_HOLD_OPTS[cfg.linkHold]; }
  if (type == MSG_FIRE) for (int c = 0; c < 8; c++) m.pulseMs[c] = cfg.pulseDs[c] * 100;
  esp_now_send(FIELD_MAC, (uint8_t *)&m, sizeof(m));
}

void sendHeartbeat() { lastHeartbeat = millis(); sendMsg(MSG_HEARTBEAT, 0); }

void sendPing() {
  pingPending = true;
  pingSentMs = lastPingMs = millis();
  pongFlag = false;
  sendMsg(MSG_PING, 0);
}

void pingNow() { if (!pingPending) sendPing(); }

void handleRecv(const uint8_t *mac, const uint8_t *data, int len, int8_t sig) {
  if (memcmp(mac, FIELD_MAC, 6) != 0) return;
  if (len != (int)sizeof(Msg) || data[0] != PROTO_VER) { badVerMs = millis(); return; }
  Msg m;
  memcpy(&m, data, sizeof(m));
  if (m.type == MSG_PONG) {
    pongAtMs = millis();
    pongFlag = true;
  } else if (m.type == MSG_STATUS) {
    continuityMask = m.mask;
    relayMask = m.mask3;
    fieldMode = m.mode;
    if (m.uptimeS + 2 < fieldUptimeS) fieldRebooted = true;
    fieldUptimeS = m.uptimeS;
    rssi = sig;
    statusCount++;
    lastStatusMs = millis();
  }
}

#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
void onRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  handleRecv(info->src_addr, data, len, info->rx_ctrl ? info->rx_ctrl->rssi : 0);
}
#else
void onRecv(const uint8_t *mac, const uint8_t *data, int len) {
  handleRecv(mac, data, len, 0);
}
#endif

void notice(const char *title, const char *text) {
  noticeTitle = title;
  noticeText = text;
  noticeUntil = millis() + ERR_SHOW_MS;
}

void deny(const char *reason) {
  Serial.printf("DENIED: %s\n", reason);
  notice("** DENIED **", reason);
}

// what one channel does when its button is pressed (or its sequence step comes up)
void trigger(int c) {
  if (cfg.type[c] == CT_TOGGLE && bitRead(toggleOn, c)) {
    bitClear(toggleOn, c);
    sendHeartbeat();
    Serial.printf("ch %d OFF\n", c + 1);
    return;
  }
  if (!chReady(c)) { deny("ch not ready"); return; }
  if (cfg.type[c] == CT_TOGGLE) {
    bitSet(toggleOn, c);
    sendHeartbeat();
    Serial.printf("ch %d ON\n", c + 1);
  } else if (cfg.type[c] == CT_HOLD && !seqRunning) {   // in a sequence HOLD acts like FIRE
    bitSet(holdOn, c);
    sendHeartbeat();
    Serial.printf("ch %d HOLD on\n", c + 1);
  } else {
    sendMsg(MSG_FIRE, 1 << c);
    flashUntil[c] = millis() + FIRE_FLASH_MS;
    guessActive = true;
    guessStart = millis();
    Serial.printf("FIRE ch %d (%.1fs pulse)\n", c + 1, cfg.pulseDs[c] / 10.0);
  }
}

void startSequence() {
  seqRunning = true;
  seqIndex = 0;
  seqNextMs = millis();
  seqCurCh = -1;
  Serial.printf("SEQUENCE start: %d channels, %.1fs delay\n", cfg.seqLen, DELAY_OPTS[cfg.delayIdx] / 1000.0);
}

void startCountdown(uint8_t mask) {
  cdActive = true;
  cdMask = mask;
  cdStartMode = mode;
  cdStartMs = millis();
  cdShown = -1;
  Serial.printf("ARMED ALL countdown for mask 0x%02X - key to DISARMED aborts\n", mask);
}

// ---------- menu ----------
void closeMenu() {
  menuOpen = inChan = inInput = resetArmed = false;
  checkState = 0;
}

void runCheck() {
  bool btnHeld = false;
  for (int c = 0; c < 8; c++) btnHeld |= btnStable[c];
  struct { const char *name; bool ok; } t[] = {
    {"LCD",        lcdFound},
    {"link",       isLinkHealthy()},
    {"ping",       lastPingOk},
    {"signal",     quality >= WEAK_LINK_PCT},
    {"fw version", !verMismatch()},
    {"key wiring", !keyFault},
    {"buttons",    !btnHeld},          // a stuck button
    {"relays",     relayMask == 0},    // we're disarmed, field must have every relay open
  };
  const int n = sizeof(t) / sizeof(t[0]);
  int pass = 0;
  const char *fail = nullptr;
  Serial.println("=== SYSTEM CHECK ===");
  for (auto &x : t) {
    Serial.printf("  %-11s %s\n", x.name, x.ok ? "OK" : "FAIL");
    if (x.ok) pass++; else if (!fail) fail = x.name;
  }
  Serial.printf("  ping %lums, signal %d%%, rssi %d, continuity 0x%02X\n",
                (unsigned long)lastRtt, quality, rssi, continuityMask);
  if (fail) snprintf(checkResult, sizeof(checkResult), "FAIL %s", fail);
  else      snprintf(checkResult, sizeof(checkResult), "PASS %d/%d", pass, n);
  checkState = 2;
}

void menuPress(int i) {
  if (inInput) { inputLast = i; return; }
  if (i > 3) return;                       // only btn1-4 navigate
  bool next = (i == 0), prev = (i == 1), plus = (i == 3);
  if (inChan) {
    if (next || prev) { chItem = (chItem + (prev ? 3 : 1)) % 4; return; }
    int d = cfg.pulseDs[chSel];
    switch (chItem) {
      case 0: chSel = (chSel + (plus ? 1 : 7)) % 8; return;
      case 1: cfg.type[chSel] = (cfg.type[chSel] + (plus ? 1 : 2)) % 3;
              cfg.needCont[chSel] = (cfg.type[chSel] == CT_FIRE);   // igniters need it, props don't
              break;
      case 2: d += plus ? (d < 10 ? 1 : 5) : (d <= 10 ? -1 : -5);  // 0.1s steps under 1s, 0.5s above
              cfg.pulseDs[chSel] = constrain(d, 1, 100);
              break;
      case 3: cfg.needCont[chSel] ^= 1; break;
    }
    saveCfg();
    return;
  }
  if (next || prev) { page = (page + (prev ? PG_COUNT - 1 : 1)) % PG_COUNT; resetArmed = false; return; }
  switch (page) {
    case PG_LINK:
    case PG_PING:     pingNow(); break;
    case PG_CHECK:    checkState = 1; checkStartMs = millis(); pingNow(); break;
    case PG_CHAN:     if (plus) { inChan = true; chItem = 0; } break;
    case PG_LINKHOLD: cfg.linkHold = (cfg.linkHold + (plus ? 1 : 5)) % 6; saveCfg(); break;
    case PG_INPUT:    if (plus) { inInput = true; keyCycled = false; inputLast = -1; } break;
    case PG_RESET:
      if (!plus) resetArmed = false;
      else if (!resetArmed) resetArmed = true;
      else { defaults(); saveCfg(); resetArmed = false; Serial.println("SETTINGS reset to defaults"); }
      break;
  }
}

// ---------- buttons ----------
void onPress(int i) {
  if (menuOpen) { menuPress(i); return; }

  if (progState == PS_BUILDING) {
    if (mode != MODE_ARMED) return;
    for (int k = 0; k < cfg.seqLen; k++)
      if (cfg.seq[k] == i) { Serial.printf("channel %d already queued\n", i + 1); return; }
    if (cfg.seqLen < 8) {
      cfg.seq[cfg.seqLen++] = i;
      Serial.printf("PROGRAM: added channel %d as step %d\n", i + 1, cfg.seqLen);
    }
    return;
  }

  if (progState == PS_DELAY) {
    if (i < 4) {
      cfg.delayIdx = i;
      progState = PS_IDLE;
      subMode = SUB_PROGRAM;
      saveCfg();
      Serial.printf("PROGRAM saved: %d channels, %.1fs delay\n", cfg.seqLen, DELAY_OPTS[i] / 1000.0);
    }
    return;
  }

  if (cdActive || seqRunning) { Serial.println("busy - press ignored"); return; }

  if (mode == MODE_ARMED) {
    bool turningOff = cfg.type[i] == CT_TOGGLE && bitRead(toggleOn, i);
    if (subMode == SUB_SINGLE) {
      if (!isLinkHealthy() && !turningOff) deny("no link");
      else                                 trigger(i);
    } else {
      if (!isLinkHealthy())     deny("no link");
      else if (cfg.seqLen == 0) deny("empty - hold MODE");
      else                      startSequence();
    }
  } else if (mode == MODE_ARMED_ALL) {
    uint8_t ready = fireAllMask();
    if (!isLinkHealthy()) deny("no link");
    else if (ready == 0)  deny("nothing ready");
    else                  startCountdown(ready);
  } else {
    notice("DISARMED", "press MODE=menu");
  }
}

void onRelease(int i) {
  if (bitRead(holdOn, i)) {
    bitClear(holdOn, i);
    sendHeartbeat();
    Serial.printf("ch %d HOLD off\n", i + 1);
  }
}

void onModeShort() {
  if (menuOpen) {
    if (inChan) inChan = false;
    else if (!inInput) closeMenu();        // input test exits on MODE hold only
    return;
  }
  if (progState == PS_BUILDING) {
    progState = PS_DELAY;
    Serial.printf("PROGRAM: %d queued. Pick delay btn1-4\n", cfg.seqLen);
  } else if (progState == PS_DELAY) {
    progState = PS_IDLE; subMode = SUB_PROGRAM;
    saveCfg();
    Serial.println("PROGRAM: kept current delay");
  } else if (mode == MODE_ARMED) {
    subMode = (subMode == SUB_SINGLE) ? SUB_PROGRAM : SUB_SINGLE;
    Serial.printf("SUB-MODE: %s\n", subMode == SUB_SINGLE ? "SINGLE" : "PROGRAM");
  } else if (keyMode == MODE_DISARMED && !keyFault) {
    menuOpen = true;
    page = PG_LINK;
  }
}

void onModeHold() {
  if (menuOpen) { closeMenu(); return; }
  if (progState == PS_IDLE && mode == MODE_ARMED) {
    progState = PS_BUILDING;
    subMode = SUB_PROGRAM;
    cfg.seqLen = 0;
    Serial.println("PROGRAM MODE: press fire buttons in order, then MODE to set delay");
  } else if (progState != PS_IDLE) {
    progState = PS_IDLE;
    Serial.println("PROGRAM cancelled");
  }
}

// ---------- LCD ----------
void lcdLine(uint8_t row, const char* s) {
  char b[17]; uint8_t i = 0;
  for (; i < 16 && s[i]; i++) b[i] = s[i];
  for (; i < 16; i++) b[i] = ' ';
  b[16] = 0;
  lcd.setCursor(0, row); lcd.print(b);
}

void show(const char *a, const char *b) { lcdLine(0, a); lcdLine(1, b); }

void seqStr(char* buf, int maxlen) {
  int p = 0;
  for (int k = 0; k < cfg.seqLen && p < maxlen - 2; k++)
    p += snprintf(buf + p, maxlen - p, "%d", cfg.seq[k] + 1);
  buf[p] = 0;
}

void menuScreen() {
  char a[24], b[24];
  int c = chSel;
  if (inInput) {
    const char *k = keyFault ? "FLT" : keyMode == MODE_ARMED_ALL ? "ALL" : keyMode == MODE_ARMED ? "ARM" : "OFF";
    snprintf(a, sizeof(a), "B:%c M:%s K:%s", inputLast < 0 ? '-' : '1' + inputLast, modeStable ? "dn" : "up", k);
    show(a, "hold MODE=exit");
    return;
  }
  if (inChan) {
    switch (chItem) {
      case 0: snprintf(a, sizeof(a), "Setup: channel");
              snprintf(b, sizeof(b), "> %d  %s %.1fs", c + 1, TYPE_NAME[cfg.type[c]], cfg.pulseDs[c] / 10.0); break;
      case 1: snprintf(a, sizeof(a), "Ch%d type", c + 1);
              snprintf(b, sizeof(b), "> %s", TYPE_NAME[cfg.type[c]]); break;
      case 2: snprintf(a, sizeof(a), "Ch%d pulse length", c + 1);
              snprintf(b, sizeof(b), "> %.1f sec", cfg.pulseDs[c] / 10.0); break;
      default: snprintf(a, sizeof(a), "Ch%d need contin.", c + 1);
              snprintf(b, sizeof(b), "> %s", cfg.needCont[c] ? "YES" : "NO"); break;
    }
    show(a, b);
    return;
  }
  snprintf(a, sizeof(a), "%d.%s", page + 1, PAGE_NAME[page]);
  switch (page) {
    case PG_LINK:
      if (!isLinkHealthy()) strcpy(b, "DOWN");
      else if (rssi)        snprintf(b, sizeof(b), "OK Q%d%% %ddB", quality, rssi);
      else                  snprintf(b, sizeof(b), "OK  signal %d%%", quality);
      break;
    case PG_PING:
      if (lastPingOk) snprintf(b, sizeof(b), "%lums  lost %lu", (unsigned long)lastRtt, (unsigned long)pingsLost);
      else            snprintf(b, sizeof(b), "no reply lost%lu", (unsigned long)pingsLost);
      break;
    case PG_CHECK: strcpy(b, checkState == 1 ? "checking..." : checkState == 2 ? checkResult : "+ = run"); break;
    case PG_CONT:
      snprintf(a, sizeof(a), "%d.Cont  12345678", page + 1);
      strcpy(b, "        ");
      for (int k = 0; k < 8; k++) b[8 + k] = bitRead(continuityMask, k) ? 'C' : '.';
      b[16] = 0;
      break;
    case PG_CHAN:     strcpy(b, "+ = open"); break;
    case PG_LINKHOLD: snprintf(b, sizeof(b), "> %s", LINK_HOLD_NAME[cfg.linkHold]); break;
    case PG_INPUT:    strcpy(b, "+ = start"); break;
    case PG_INFO:     snprintf(b, sizeof(b), "v%s fld %luh%02lum", FW_VERSION,
                               (unsigned long)(fieldUptimeS / 3600), (unsigned long)(fieldUptimeS / 60 % 60)); break;
    case PG_RESET:    strcpy(b, resetArmed ? "+ again = RESET" : "+ = reset all"); break;
    default:          b[0] = 0;
  }
  show(a, b);
}

void updateLCD() {
  static uint32_t last = 0;
  uint32_t now = millis();
  if (now - last < LCD_REFRESH_MS) return;
  last = now;
  if (menuOpen) { menuScreen(); return; }

  int ready = __builtin_popcount(fireAllMask());
  int on = __builtin_popcount(toggleOn | holdOn);
  char a[24], b[24], sq[12];

  if (keyFault)                      show("KEY FAULT", "both pins high");
  else if (!keyCycled)               show("TURN KEY TO", "DISARMED first");
  else if (progState == PS_BUILDING) { seqStr(sq, sizeof(sq)); snprintf(b, sizeof(b), "Seq:%s_", sq); show("PROGRAM: order", b); }
  else if (progState == PS_DELAY)    show("PROGRAM: delay", "b1-4: .5 1 1.5 2");
  else if (seqRunning && seqCurCh >= 0) {
    snprintf(a, sizeof(a), "SEQ  ch %d", seqCurCh + 1);
    snprintf(b, sizeof(b), "step %d of %d", seqIndex, cfg.seqLen);
    show(a, b);
  }
  else if (cdActive) { snprintf(b, sizeof(b), "countdown %d", cdShown >= 0 ? cdShown : 3); show("** FIRE ALL **", b); }
  else if (guessActive && (now - guessStart) < GUESS_CD_MS) {
    snprintf(b, sizeof(b), "fuse ~%d", 3 - (int)((now - guessStart) / 1000));
    show("FIRING...", b);
  }
  else if (now < noticeUntil)        show(noticeTitle, noticeText);
  else if (verMismatch())            show("FW MISMATCH", "flash both boxes");
  else if (!isLinkHealthy())         show("LINK DOWN", toggleOn && cfg.linkHold ? "field holds ON" : "check field box");
  else if (missingCh >= 0)           { snprintf(a, sizeof(a), "CH %d NOT ON", missingCh + 1); show(a, "field no confirm"); }
  else if (mode == MODE_DISARMED)    { snprintf(b, sizeof(b), "Rdy:%d  MODE=menu", ready); show("DISARMED", b); }
  else {
    snprintf(b, sizeof(b), "Rdy:%d On:%d Q%d%%", ready, on, quality);
    if (mode == MODE_ARMED_ALL) { show("ARMED ALL", b); return; }
    snprintf(a, sizeof(a), "ARMED  %s", subMode == SUB_SINGLE ? "SINGLE" : "PROGRAM");
    if (subMode == SUB_PROGRAM && cfg.seqLen > 0) {
      seqStr(sq, sizeof(sq));
      snprintf(b, sizeof(b), "Sq:%s d:%.1fs", sq, DELAY_OPTS[cfg.delayIdx] / 1000.0);
    }
    show(a, b);
  }
}

void setup() {
  Serial.begin(115200);
  loadCfg();

  for (int i = 0; i < 8; i++) { pinMode(LED_PIN[i], OUTPUT); digitalWrite(LED_PIN[i], LOW); }
  pinMode(PIN_LED_PASS, OUTPUT);
  pinMode(PIN_LED_FAIL, OUTPUT);

  for (int i = 0; i < 4; i++) pinMode(BTN_PIN[i], INPUT_PULLUP);
  for (int i = 4; i < 8; i++) pinMode(BTN_PIN[i], INPUT);
  pinMode(PIN_KEY_ARMED, INPUT_PULLDOWN);
  pinMode(PIN_KEY_ALL, INPUT_PULLDOWN);
  pinMode(PIN_MODE_BTN, INPUT_PULLUP);

  // LCD on custom I2C pins (setPins makes the no-arg Wire.begin use them)
  Wire.setPins(PIN_LCD_SDA, PIN_LCD_SCL);
  Wire.begin();
  Wire.beginTransmission(LCD_ADDR);
  lcdFound = Wire.endTransmission() == 0;
  lcd.init();
  lcd.backlight();
  show("Show Ctrl v" FW_VERSION, "starting...");

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
#if USE_LONG_RANGE
  esp_wifi_set_protocol(WIFI_IF_STA, WIFI_PROTOCOL_LR);
#endif
  Serial.println();
  Serial.println("=== SHOW CONTROLLER v" FW_VERSION " (panel box) ===");
  Serial.print("MY MAC - paste into CONTROLLER_MAC in the field sketch: ");
  Serial.println(WiFi.macAddress());
  if (!lcdFound) Serial.println("WARNING: no LCD at the I2C address - try 0x3F");
  for (int c = 0; c < 8; c++)
    Serial.printf("  ch %d: %-6s pulse %.1fs  continuity %s\n", c + 1, TYPE_NAME[cfg.type[c]],
                  cfg.pulseDs[c] / 10.0, cfg.needCont[c] ? "required" : "ignored");
  Serial.printf("  link-lost hold: %s\n", LINK_HOLD_NAME[cfg.linkHold]);

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init FAILED - halting");
    show("ESP-NOW FAIL", "halted");
    while (true) delay(1000);
  }
  esp_now_register_recv_cb(onRecv);

  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, FIELD_MAC, 6);
  peer.channel = 0;
  peer.encrypt = false;
  esp_now_add_peer(&peer);

  // boot self-test: flash the LEDs
  for (int i = 0; i < 8; i++) digitalWrite(LED_PIN[i], HIGH);
  digitalWrite(PIN_LED_PASS, HIGH);
  digitalWrite(PIN_LED_FAIL, HIGH);
  delay(500);
  for (int i = 0; i < 8; i++) digitalWrite(LED_PIN[i], LOW);
  digitalWrite(PIN_LED_PASS, LOW);
  digitalWrite(PIN_LED_FAIL, LOW);

  sendPing();
}

void loop() {
  uint32_t now = millis();

  // ---- key ----
  bool kArmed = digitalRead(PIN_KEY_ARMED);
  bool kAll   = digitalRead(PIN_KEY_ALL);
  keyFault = kArmed && kAll;   // both contacts closed = wiring short: stay disarmed
  keyMode = keyFault ? MODE_DISARMED : kAll ? MODE_ARMED_ALL : kArmed ? MODE_ARMED : MODE_DISARMED;
  if (keyMode == MODE_DISARMED && !keyFault && !inInput) keyCycled = true;
  if (menuOpen && !inInput && keyMode != MODE_DISARMED) closeMenu();   // turning the key leaves the menu

  uint8_t newMode = (menuOpen || !keyCycled) ? MODE_DISARMED : keyMode;
  if (newMode != mode) {
    mode = newMode;
    if (mode == MODE_DISARMED) toggleOn = holdOn = 0;
    Serial.printf("MODE: %s\n", mode == MODE_DISARMED ? "DISARMED"
                              : mode == MODE_ARMED    ? "ARMED" : "ARMED ALL");
    sendHeartbeat();           // tell the field now, don't wait
  }
  if (mode != MODE_ARMED && progState != PS_IDLE) {
    progState = PS_IDLE;
    Serial.println("PROGRAM cancelled (left ARMED)");
  }

  // ---- radio: heartbeat, constant ping, link quality ----
  if (now - lastHeartbeat >= HEARTBEAT_MS) sendHeartbeat();
  if (pingPending) {
    if (pongFlag) {
      pingPending = false; lastPingOk = true;
      lastRtt = pongAtMs - pingSentMs;
    } else if (now - pingSentMs > PING_TIMEOUT) {
      pingPending = false; lastPingOk = false; pingsLost++;
    }
  }
  if (!pingPending && now - lastPingMs >= PING_MS) sendPing();
  if (now - qualityMs >= 2000) {
    qualityMs = now;
    quality = min(100, statusCount * 100 / STATUS_PER_2S);
    statusCount = 0;
  }

  bool linkHealthy = isLinkHealthy();
  static bool linkWasUp = false;
  if (linkHealthy != linkWasUp) {
    linkWasUp = linkHealthy;
    Serial.println(linkHealthy ? "LINK: UP" : "LINK: DOWN");
  }
  if (fieldRebooted) {
    fieldRebooted = false;
    Serial.println("WARNING: field box rebooted (power glitch?)");
    notice("FIELD REBOOTED", "power glitch?");
  }

  // ---- system check: does the field confirm the ON/OFF + HOLD relays? ----
  uint8_t missing = (toggleOn | holdOn) & ~relayMask;
  if (!linkHealthy || !missing) mismatchSince = 0;
  else if (!mismatchSince) mismatchSince = now;
  missingCh = (mismatchSince && now - mismatchSince > 1000) ? __builtin_ctz(missing) : -1;

  if (checkState == 1 && now - checkStartMs >= CHECK_MS && !pingPending) runCheck();

  // ---- buttons ----
  for (int i = 0; i < 8; i++) {
    bool raw = (digitalRead(BTN_PIN[i]) == LOW);
    if (raw != btnRaw[i]) { btnRaw[i] = raw; btnRawMs[i] = now; }
    if (raw != btnStable[i] && (now - btnRawMs[i]) >= DEBOUNCE_MS) {
      btnStable[i] = raw;
      if (raw) onPress(i); else onRelease(i);
    }
  }

  bool mraw = (digitalRead(PIN_MODE_BTN) == LOW);
  if (mraw != modeRaw) { modeRaw = mraw; modeRawMs = now; }
  if (mraw != modeStable && (now - modeRawMs) >= DEBOUNCE_MS) {
    modeStable = mraw;
    if (mraw) { modeDownMs = now; modeHoldDone = false; }
    else if (!modeHoldDone) onModeShort();
  }
  if (modeStable && !modeHoldDone && (now - modeDownMs) >= HOLD_MS) {
    modeHoldDone = true;
    onModeHold();
  }

  // ---- ARMED ALL countdown ----
  if (cdActive) {
    uint8_t stillReady = cdMask & fireAllMask();
    if (mode != cdStartMode)       { cdActive = false; Serial.println("COUNTDOWN ABORTED: key changed"); }
    else if (!linkHealthy)         { cdActive = false; Serial.println("COUNTDOWN ABORTED: link lost"); }
    else if (stillReady == 0)      { cdActive = false; Serial.println("COUNTDOWN ABORTED: nothing ready"); }
    else {
      uint32_t el = now - cdStartMs;
      if (el >= COUNTDOWN_MS) {
        cdActive = false;
        Serial.printf("FIRE ALL: mask 0x%02X\n", stillReady);
        sendMsg(MSG_FIRE, stillReady);
        for (int c = 0; c < 8; c++) if (bitRead(stillReady, c)) flashUntil[c] = now + FIRE_FLASH_MS;
      } else {
        int s = 3 - (int)(el / 1000);
        if (s != cdShown) { cdShown = s; Serial.printf("  ... %d\n", s); }
      }
    }
  }

  // ---- PROGRAM sequence ----
  if (seqRunning) {
    if (mode != MODE_ARMED || !linkHealthy) {
      seqRunning = false; Serial.println("SEQUENCE ABORTED");
    } else if (now >= seqNextMs) {
      if (seqIndex >= cfg.seqLen) {
        seqRunning = false; seqCurCh = -1; Serial.println("SEQUENCE complete");
      } else {
        int ch = cfg.seq[seqIndex];
        seqCurCh = ch;
        Serial.printf("SEQ step %d: channel %d\n", seqIndex + 1, ch + 1);
        trigger(ch);
        seqIndex++;
        seqNextMs = now + DELAY_OPTS[cfg.delayIdx];
      }
    }
  }

  // ---- LEDs ----
  for (int i = 0; i < 8; i++) {
    bool on;
    if (inInput)                    on = btnStable[i];
    else if (now < flashUntil[i])   on = ((now / 120) % 2) == 0;
    else if (cfg.type[i] != CT_FIRE) on = bitRead(toggleOn | holdOn, i) && ((linkHealthy && bitRead(relayMask, i)) || (now / 100) % 2);
    else                            on = linkHealthy && chReady(i);
    digitalWrite(LED_PIN[i], on);
  }
  digitalWrite(PIN_LED_PASS, linkHealthy);
  digitalWrite(PIN_LED_FAIL, !linkHealthy || (quality < WEAK_LINK_PCT && (now / 500) % 2));

  updateLCD();

  delay(5);
}
