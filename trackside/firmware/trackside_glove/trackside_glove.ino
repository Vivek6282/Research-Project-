/*
  TRACKSIDE - GLOVE UNIT
  ----------------------
  This board is the one you WEAR. It listens for radio messages from the
  bridge board and then:
     - lights a 5-segment signal strip   (Nominal / Monitoring / Intervene)
     - buzzes the little vibration motor (off / pulsing / continuous)

  Wiring (see the build guide):
     LED strip  5V  -> board pin marked VIN or 5V
     LED strip  GND -> board GND
     LED strip  DIN -> board GPIO 18      (optional 330 ohm resistor in between)
     Motor circuit input (via 1k resistor to transistor) -> board GPIO 26
     Motor +    -> board 3V3
*/

#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <Adafruit_NeoPixel.h>

// ---------- pins and sizes (change only if you wired differently) ----------
#define LED_PIN    18   // data wire of the LED strip
#define NUM_LEDS   10   // your strip has 10 LEDs; we only use the first 5
#define MOTOR_PIN  26   // goes to the transistor through the 1k resistor

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
uint8_t  shownStage = 254;        // remembers what the LEDs currently show
uint32_t lastMacPrint = 0;

// How many of the 5 segments light up for each stage
int litSegments(uint8_t stage) {
  if (stage == NOMINAL)    return 2;
  if (stage == MONITORING) return 4;
  if (stage == INTERVENE)  return 5;
  return 0;
}

void drawStage(uint8_t stage) {
  strip.clear();
  if (stage == WAITING) {
    strip.setPixelColor(0, Adafruit_NeoPixel::Color(0, 0, 40));   // dim blue = waiting
  } else {
    int lit = litSegments(stage);
    for (int i = 0; i < lit; i++) strip.setPixelColor(i, SEG_COLOR[i]);
  }
  strip.show();
}

// Motor: off / short buzz every 0.6 s / on all the time
bool motorShouldBeOn(uint8_t stage, uint32_t nowMs) {
  if (stage == INTERVENE)  return true;
  if (stage == MONITORING) return (nowMs % 600) < 120;
  return false;
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

// Runs once when you power the glove: proves the LEDs and motor work
void selfTest() {
  for (int i = 0; i < 5; i++) {
    strip.clear();
    strip.setPixelColor(i, SEG_COLOR[i]);
    strip.show();
    delay(200);
  }
  drawStage(INTERVENE);
  digitalWrite(MOTOR_PIN, HIGH);
  delay(400);
  digitalWrite(MOTOR_PIN, LOW);
  drawStage(WAITING);
}

void setup() {
  Serial.begin(115200);
  pinMode(MOTOR_PIN, OUTPUT);
  digitalWrite(MOTOR_PIN, LOW);

  strip.begin();
  strip.setBrightness(50);   // 0-255. Lower = gentler on the USB power
  strip.clear();
  strip.show();

  selfTest();

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE);   // both boards use channel 1

  Serial.println();
  Serial.println("=== TRACKSIDE GLOVE ===");
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

  if (stage != shownStage) {
    drawStage(stage);
    shownStage = stage;
    if (stage == WAITING) Serial.println("Stage: WAITING (no radio messages)");
    if (stage == NOMINAL)    Serial.printf("Stage: NOMINAL     (g=%.2f)\n", gLastG);
    if (stage == MONITORING) Serial.printf("Stage: MONITORING  (g=%.2f)\n", gLastG);
    if (stage == INTERVENE)  Serial.printf("Stage: INTERVENE   (g=%.2f)\n", gLastG);
  }

  digitalWrite(MOTOR_PIN, motorShouldBeOn(stage, now) ? HIGH : LOW);

  // While waiting, repeat the MAC address every 3 seconds so you never miss it
  if (stage == WAITING && (now - lastMacPrint) > 3000) {
    lastMacPrint = now;
    Serial.print("GLOVE MAC ADDRESS: ");
    Serial.println(WiFi.macAddress());
  }
  delay(5);
}
