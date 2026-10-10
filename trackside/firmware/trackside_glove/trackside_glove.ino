/*
  TRACKSIDE - GLOVE UNIT  (LED-only version, no vibration motor)
  ---------------------------------------------------------------
  This board is the one you WEAR. It listens for radio messages from the
  bridge board and shows the stage on a 5-segment LED signal strip:

     NOMINAL     2 green segments, steady
     MONITORING  4 segments: 2 green steady + 2 amber FLASHING (slow)
     INTERVENE   all 5 segments FLASHING (2.5 times a second, kept at or below 3)
     WAITING     one dim blue LED (no radio messages arriving)

  Wiring (see the circuit diagram):
     LED strip  +5V -> a 5V source (the board's 5V pin, or a USB breakout)
     LED strip  GND -> board GND   (the grounds MUST be joined)
     LED strip  DIN -> board G18   (a 330 ohm resistor in between is recommended)
  Nothing is connected to G26 any more.
*/

#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <Adafruit_NeoPixel.h>

// ---------- pins and sizes (change only if you wired differently) ----------
#define LED_PIN    18   // data wire of the LED strip (G18 on your board)
#define NUM_LEDS   10   // your strip has 10 LEDs; we only use the first 5

// ---------- the message the bridge sends us (must match the bridge!) ----------
typedef struct {
  uint8_t stage;   // 0 = NOMINAL, 1 = MONITORING, 2 = INTERVENE
  float   g;       // the g-force number
} AlertMessage;

const uint8_t NOMINAL    = 0;
const uint8_t MONITORING = 1;
const uint8_t INTERVENE  = 2;
const uint8_t WAITING    = 255;   // "no radio messages arriving"

Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);

// The 5 segments, left to right: green, green, amber, amber, red
const uint32_t SEG_COLOR[5] = {
  Adafruit_NeoPixel::Color(0, 255, 0),
  Adafruit_NeoPixel::Color(0, 255, 0),
  Adafruit_NeoPixel::Color(255, 110, 0),
  Adafruit_NeoPixel::Color(255, 110, 0),
  Adafruit_NeoPixel::Color(255, 0, 0)
};

volatile uint8_t  gStage      = WAITING;
volatile uint32_t gLastPacket = 0;
volatile float    gLastG      = 0;
uint8_t  shownStage = 254;        // remembers the stage currently shown
uint8_t  shownMask  = 0xFF;       // remembers which segments are currently lit
uint32_t lastMacPrint = 0;

// Which of the 5 segments are lit RIGHT NOW? One bit per segment (bit 0 = left).
// This also makes the flashing: the answer changes with the time.
uint8_t segmentMask(uint8_t stage, uint32_t nowMs) {
  if (stage == NOMINAL) return 0b00011;                       // 2 green, steady
  if (stage == MONITORING) {
    bool amberOn = (nowMs % 500) < 250;                       // flash 2 times a second
    return amberOn ? 0b01111 : 0b00011;                       // greens always, ambers flash
  }
  if (stage == INTERVENE) {
    bool allOn = (nowMs % 400) < 200;                         // flash 2.5 times a second (safe: not above 3)
    return allOn ? 0b11111 : 0b00000;
  }
  return 0;                                                    // WAITING: handled separately
}

void drawMask(uint8_t stage, uint8_t mask) {
  strip.clear();
  if (stage == WAITING) {
    strip.setPixelColor(0, Adafruit_NeoPixel::Color(0, 0, 40));   // dim blue = waiting
  } else {
    for (int i = 0; i < 5; i++) {
      if (mask & (1 << i)) strip.setPixelColor(i, SEG_COLOR[i]);
    }
  }
  strip.show();
}

// Runs by itself every time a radio message arrives
void onReceive(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  if (len != (int)sizeof(AlertMessage)) return;
  AlertMessage m;
  memcpy(&m, data, sizeof(m));
  if (m.stage > INTERVENE) return;
  gLastG      = m.g;
  gStage      = m.stage;
  gLastPacket = millis();
}

// Runs once when you power the glove: proves the LEDs work
void selfTest() {
  for (int i = 0; i < 5; i++) {              // light the segments one by one
    strip.clear();
    strip.setPixelColor(i, SEG_COLOR[i]);
    strip.show();
    delay(200);
  }
  drawMask(INTERVENE, 0b11111);              // then all five together
  delay(400);
  drawMask(WAITING, 0);
}

void setup() {
  Serial.begin(115200);

  strip.begin();
  strip.setBrightness(50);   // 0-255. Lower = gentler on the USB power
  strip.clear();
  strip.show();

  selfTest();

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE);   // both boards use channel 1

  Serial.println();
  Serial.println("=== TRACKSIDE GLOVE (LED only) ===");
  Serial.print("GLOVE MAC ADDRESS: ");
  Serial.println(WiFi.macAddress());

  if (esp_now_init() != ESP_OK) {
    Serial.println("ERROR: radio (ESP-NOW) failed to start. Press the EN button.");
    return;
  }
  esp_now_register_recv_cb(onReceive);
  Serial.println("Radio ready. Waiting for the bridge...");
}

void loop() {
  uint32_t now = millis();

  // No message for 1.5 seconds? Go back to the "waiting" state.
  if (gStage != WAITING && (now - gLastPacket) > 1500) gStage = WAITING;

  uint8_t stage = gStage;
  uint8_t mask  = segmentMask(stage, now);

  // Redraw only when something actually changed (a new stage, or a flash step)
  if (stage != shownStage || mask != shownMask) {
    drawMask(stage, mask);
    if (stage != shownStage) {                       // print only when the stage changes
      if (stage == WAITING)    Serial.println("Stage: WAITING (no radio messages)");
      if (stage == NOMINAL)    Serial.printf("Stage: NOMINAL     (g=%.2f)\n", gLastG);
      if (stage == MONITORING) Serial.printf("Stage: MONITORING  (g=%.2f)\n", gLastG);
      if (stage == INTERVENE)  Serial.printf("Stage: INTERVENE   (g=%.2f)\n", gLastG);
    }
    shownStage = stage;
    shownMask  = mask;
  }

  // While waiting, repeat the MAC address every 3 seconds so you never miss it
  if (stage == WAITING && (now - lastMacPrint) > 3000) {
    lastMacPrint = now;
    Serial.print("GLOVE MAC ADDRESS: ");
    Serial.println(WiFi.macAddress());
  }
  delay(5);
}