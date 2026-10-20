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
#include <Preferences.h>
#include "radio_secrets.h"
#include "trackside_radio_protocol.h"

// =====================================================================
//  CHANGE THIS LINE: paste the GLOVE MAC ADDRESS between the quotes.
//  You get it from the glove's Serial Monitor. Example: "A0:B7:65:12:34:56"
// =====================================================================
const char* GLOVE_MAC = "B0:CB:D8:0A:4F:20";

// Used only when the line has no stage in it (plain number).
const float FALLBACK_THRESHOLD = 1.15;

const int ONBOARD_LED = 2;      // the little blue light on the board

Preferences radioPrefs;
uint32_t packetCounter = 0;
uint32_t counterCeiling = 0;

uint8_t  gloveAddr[6];
char     lineBuf[48];
uint8_t  lineLen  = 0;
uint32_t sentCount = 0;

// Parses a colon-separated MAC string into 6 raw bytes.
// Input: text (MAC string), out (destination 6-byte buffer). Output: true on success, false on format error.
bool parseMac(const char* text, uint8_t* out) {
  unsigned int m[6];
  int n = sscanf(text, "%x:%x:%x:%x:%x:%x", &m[0], &m[1], &m[2], &m[3], &m[4], &m[5]);
  if (n != 6) return false;
  for (int i = 0; i < 6; i++) out[i] = (uint8_t)m[i];
  return true;
}

// Handles one complete serial line from USB using shared protocol parsing (G5, G6).
// Discards lines with malformed numbers, out-of-range g, or unrecognized stage words.
void handleLine(char* line) {
  float   g     = 0.0f;
  uint8_t stage = TRACKSIDE_STAGE_NOMINAL;

  if (!trackside_parse_serial_line(line, FALLBACK_THRESHOLD, &g, &stage)) {
    Serial.println("Ignored invalid line. Expected number or number,STAGE (0.0..10.0, NOMINAL/MONITORING/INTERVENE).");
    return;
  }

  // Advance replay counter; when ceiling reached, write next ceiling to NVS (G4)
  packetCounter++;
  if (packetCounter >= counterCeiling) {
    radioPrefs.begin("radio", false);
    counterCeiling += 1000;
    radioPrefs.putUInt("ceiling", counterCeiling);
    radioPrefs.end();
    Serial.printf("Advanced NVS replay ceiling to %lu\n", (unsigned long)counterCeiling);
  }

  RadioPacket packet;
  packet.version = 1;
  packet.stage   = stage;
  packet.g       = g;
  packet.counter = packetCounter;
  esp_err_t result = esp_now_send(gloveAddr, (uint8_t*)&packet, sizeof(packet));

  sentCount++;
  digitalWrite(ONBOARD_LED, sentCount % 2);   // blink the blue light on every send
  Serial.printf("g=%.2f  stage=%u  send=%s  (#%lu, seq=%lu)\n",
                g, stage, (result == ESP_OK) ? "ok" : "FAILED",
                (unsigned long)sentCount, (unsigned long)packetCounter);
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

  // Set Primary Master Key (PMK) used by ESP-NOW to encrypt Local Master Keys
  if (esp_now_set_pmk(TRACKSIDE_PMK) != ESP_OK) {
    Serial.println("ERROR: could not set Primary Master Key (PMK).");
    return;
  }

  // Configure glove as an encrypted ESP-NOW peer using shared LMK
  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, gloveAddr, 6);
  peer.channel = 1;
  peer.encrypt = true;
  memcpy(peer.lmk, TRACKSIDE_LMK, 16);
  if (esp_now_add_peer(&peer) != ESP_OK) {
    Serial.println("ERROR: could not add the glove as an encrypted radio partner.");
    return;
  }

  // Initialize persistent replay counter ceiling in NVS (G4)
  radioPrefs.begin("radio", false);
  uint32_t storedCeiling = radioPrefs.getUInt("ceiling", 0);
  packetCounter = storedCeiling;
  counterCeiling = storedCeiling + 1000;
  radioPrefs.putUInt("ceiling", counterCeiling);
  radioPrefs.end();
  Serial.printf("Replay guard: counter starts at %lu, next ceiling %lu\n",
                (unsigned long)packetCounter, (unsigned long)counterCeiling);

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
