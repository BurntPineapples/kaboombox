// KaBoomBox signing key, example file.
//
// 1. Copy this file to secrets.h in the same folder.
// 2. Make your own random key. In a terminal (needs Python 3):
//      python -c "import secrets; print(', '.join('0x%02X' % b for b in secrets.token_bytes(32)))"
//    Paste the 32 numbers between the { } below and set KABOOM_KEY_IS_PLACEHOLDER to 0.
// 3. Put the exact same secrets.h in BOTH sketch folders:
//      firmware/firework_controller/secrets.h
//      firmware/firework_field/secrets.h
//
// Keep secrets.h private. It's in .gitignore so it never gets uploaded. Anyone
// with your key could make a fake panel that your field box would obey.
// If the boxes have different keys they simply won't link (LCD: FW/SECRET DIFFER).

#define KABOOM_KEY_IS_PLACEHOLDER 1   // set to 0 once you've put your own key in

static const uint8_t KABOOM_KEY[32] = {
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};
