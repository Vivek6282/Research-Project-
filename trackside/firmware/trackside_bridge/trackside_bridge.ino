/*
  TRACKSIDE - BRIDGE UNIT
  -----------------------
  This board stays plugged into your LAPTOP with the USB cable.
  The Python simulator sends it lines of text over USB, for example:
        1.25                  (just the g-force)
        1.25,MONITORING       (g-force plus the stage - exact match with the screen)
  The bridge turns each line into a radio message and sends it to the glove.

  You can also test it by hand: open the Serial Monitor (115200 baud,
  "Newline" selected), type a number like 1.3 and press Enter.
*/

#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <ctype.h>

// =====================================================================
//  CHANGE THIS LINE: paste the GLOVE MAC ADDRESS between the quotes.
//  You get it from the glove's Serial Monitor. Example: "A0:B7:65:12:34:56"
// =====================================================================
const char* GLOVE_MAC = "B0:CB:D8:0A:4F:20";

// Used only when the line has no stage in it (plain number).
const float FALLBACK_THRESHOLD = 1.15;

const int ONBOARD_LED = 2;      // the little blue light on the board

// Must be identical to the glove's message layout
typedef struct {
  uint8_t stage;   // 0 = NOMINAL, 1 = MONITORING, 2 = INTERVENE
  float   g;
} AlertMessage;

uint8_t  gloveAddr[6];
char     lineBuf[48];
uint8_t  lineLen  = 0;
uint32_t sentCount = 0;

// Turn "AA:BB:CC:DD:EE:FF" into 6 numbers. Returns false if the text is wrong.
bool parseMac(const char* text, uint8_t* out) {
  unsigned int m[6];
  int n = sscanf(text, "%x:%x:%x:%x:%x:%x", &m[0], &m[1], &m[2], &m[3], &m[4], &m[5]);
  if (n != 6) return false;
  for (int i = 0; i < 6; i++) out[i] = (uint8_t)m[i];
  return true;
}

// Decide the stage from a plain g number
uint8_t classify(float g) {
  if (g >= FALLBACK_THRESHOLD)        return 2;   // INTERVENE
  if (g >= FALLBACK_THRESHOLD * 0.82f) return 1;   // MONITORING
  return 0;                                        // NOMINAL
}

// Read the stage word: I... = 2, M... = 1, anything else = 0
uint8_t stageFromText(const char* t) {
  while (*t == ' ') t++;
  char c = (char)toupper((unsigned char)*t);
  if (c == 'I') return 2;
  if (c == 'M') return 1;
  return 0;
}

// Handle one complete line that arrived over USB
void handleLine(char* line) {
  while (*line == ' ') line++;
  if (*line == '\0') return;
  // A real line must start with a digit, a dot or a minus sign
  if (!(isdigit((unsigned char)*line) || *line == '.' || *line == '-')) {
    Serial.println("Ignored. Type a number like 1.3 and press Enter.");
    return;
  }

  uint8_t stage;
  float   g;
  char* comma = strchr(line, ',');
  if (comma) {
    *comma = '\0';
    g     = (float)atof(line);
    stage = stageFromText(comma + 1);
  } else {
    g     = (float)atof(line);
    stage = classify(g);
  }

  AlertMessage msg;
  msg.stage = stage;
  msg.g     = g;
  esp_err_t result = esp_now_send(gloveAddr, (uint8_t*)&msg, sizeof(msg));

  sentCount++;
  digitalWrite(ONBOARD_LED, sentCount % 2);   // blink the blue light on every send
  Serial.printf("g=%.2f  stage=%u  send=%s  (#%lu)\n",
                g, stage, (result == ESP_OK) ? "ok" : "FAILED", (unsigned long)sentCount);
}

void setup() {
  Serial.begin(115200);
  pinMode(ONBOARD_LED, OUTPUT);
  digitalWrite(ONBOARD_LED, LOW);
  delay(300);

  Serial.println();
  Serial.println("=== TRACKSIDE BRIDGE ===");

  if (!parseMac(GLOVE_MAC, gloveAddr)) {
    Serial.println("ERROR: GLOVE_MAC is not a valid address. Fix the line near the top of the sketch.");
    return;
  }

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE);   // both boards use channel 1

  Serial.print("This bridge's own MAC: ");
  Serial.println(WiFi.macAddress());
  Serial.print("Sending to glove MAC:  ");
  Serial.println(GLOVE_MAC);

  if (esp_now_init() != ESP_OK) {
    Serial.println("ERROR: radio (ESP-NOW) failed to start. Press the EN button.");
    return;
  }

  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, gloveAddr, 6);
  peer.channel = 0;
  peer.encrypt = false;
  if (esp_now_add_peer(&peer) != ESP_OK) {
    Serial.println("ERROR: could not add the glove as a radio partner.");
    return;
  }

  Serial.println("Bridge ready. Waiting for numbers from the laptop...");
}

void loop() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') {
      lineBuf[lineLen] = '\0';
      handleLine(lineBuf);
      lineLen = 0;
    } else if (c != '\r' && lineLen < sizeof(lineBuf) - 1) {
      lineBuf[lineLen++] = c;
    }
  }
}
